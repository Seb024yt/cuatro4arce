import uuid
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select

from .models import LoginRequest, ProcessRequest, User, UserCreate, UserRead, Company, CompanyCreate, CompanyRead, Token
from .sii_connector import run_sii_process
from .database import create_db_and_tables, get_session
from .auth import create_access_token, get_password_hash, verify_password, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES

app = FastAPI()

# Mount templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files (for generated excel)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize DB
@app.on_event("startup")
def on_startup():
    create_db_and_tables()

# Store jobs in memory
jobs: Dict[str, Dict] = {}

# --- Views ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
async def register_view(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request, company_id: int, session: Session = Depends(get_session)):
    company = session.get(Company, company_id)
    if not company:
        # Fallback or error, for now just pass None or redirect
        return templates.TemplateResponse("dashboard.html", {"request": request})
        
    return templates.TemplateResponse("portal.html", {"request": request, "company": company})


# --- Auth API ---

@app.post("/auth/register", response_model=UserRead)
async def register(user: UserCreate, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El correo ya está registrado")
    
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@app.post("/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


# --- User/Company API ---

@app.get("/api/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# --- Admin API ---

@app.get("/api/admin/users", response_model=List[UserRead])
async def get_all_users(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    users = session.exec(select(User)).all()
    return users

@app.post("/api/admin/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Requiere permisos de administrador")
    
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    user.payment_status = "paid"
    user.payment_folio = f"MANUAL-{int(time.time())}"
    session.add(user)
    session.commit()
    return {"message": "Usuario activado correctamente"}

# --- Payment API ---

@app.post("/api/pay")
async def simulate_payment(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    # Simulate payment
    folio = f"PAY-{uuid.uuid4().hex[:8].upper()}"
    current_user.payment_status = "paid"
    current_user.payment_folio = folio
    session.add(current_user)
    session.commit()
    return {"status": "paid", "folio": folio}

@app.post("/api/companies", response_model=CompanyRead)
async def create_company(
    company: CompanyCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    if len(current_user.companies) >= current_user.max_companies:
        raise HTTPException(status_code=400, detail="Límite de empresas alcanzado")
    
    db_company = Company.from_orm(company)
    db_company.user_id = current_user.id
    session.add(db_company)
    session.commit()
    session.refresh(db_company)
    return db_company

@app.get("/api/companies/{company_id}", response_model=CompanyRead)
async def read_company(
    company_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    company = session.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if company.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta empresa")
    return company


# --- Process API ---

def update_job_status(job_id: str, message: str, state: str = None):
    if job_id in jobs:
        jobs[job_id]["status"] = message
        if state:
            jobs[job_id]["state"] = state

@app.post("/api/process")
async def start_process(
    data: ProcessRequest, 
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user)
):
    # Fetch credentials if company_id is provided
    if data.company_id:
        company = session.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
        # Verify ownership
        if company.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para usar esta empresa")
            
        data.rutEmpresa = company.rut
        data.claveSII = company.clave_sii
    
    if not data.rutEmpresa or not data.claveSII:
        raise HTTPException(status_code=400, detail="Faltan credenciales (RUT/Clave) o Company ID")

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "state": "pending",
        "status": "Iniciando...",
        "created_at": time.time()
    }
    
    def status_callback(msg, state=None):
        update_job_status(job_id, msg, state)
        
    background_tasks.add_task(run_sii_process, job_id, data, status_callback)
    
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

