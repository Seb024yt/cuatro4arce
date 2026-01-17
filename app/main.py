import uuid
import time
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict

from .models import LoginRequest, ProcessRequest
# from .sii_connector import run_sii_process # Will implement later

app = FastAPI()

# Mount templates
templates = Jinja2Templates(directory="app/templates")

# Store jobs in memory
jobs: Dict[str, Dict] = {}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # In a real app, check session/cookie here
    return templates.TemplateResponse("login.html", {"request": request}) 
    # Note: I will map index.html to login.html in templates or just use read logic.
    # Since I updated index.html in root, and user might run from root, I should probably
    # serve the file directly or ensure I copied it. 
    # For now, I'll assume I copied index.html to app/templates/login.html in a previous step 
    # (I didn't yet, so I will read it from root or just copy it now).

@app.post("/api/login")
async def login(creds: LoginRequest):
    # Mock login logic
    # User said: "Implementar acceso con usuario y contraseña del portal"
    # I'll use hardcoded for now or a simple check.
    # User said "yo como administrador cada que alguien pague puedas crear los usarios"
    # Since no DB yet, I'll allow "admin"/"admin" or "user"/"password" for testing.
    if creds.username == "admin" and creds.password == "admin":
        return {"message": "Login successful"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/portal", response_class=HTMLResponse)
async def portal(request: Request):
    return templates.TemplateResponse("portal.html", {"request": request})

def process_job(job_id: str, data: ProcessRequest):
    jobs[job_id]["state"] = "processing"
    jobs[job_id]["status"] = "Validando datos..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Ingresando al SII..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Descargando Registro de Compras y Ventas..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Descargando Boletas de Honorarios..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Buscando Remanente F29..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Generando PDF final..."
    time.sleep(2)
    
    jobs[job_id]["status"] = "Enviando correo..."
    time.sleep(1)
    
    jobs[job_id]["state"] = "completed"
    jobs[job_id]["status"] = "Finalizado"

@app.post("/api/process")
async def start_process(data: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "state": "pending",
        "status": "Iniciando...",
        "created_at": time.time()
    }
    
    # In real implementation, call the actual SII logic
    # background_tasks.add_task(run_sii_process, job_id, data)
    background_tasks.add_task(process_job, job_id, data) # Mock for now
    
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
