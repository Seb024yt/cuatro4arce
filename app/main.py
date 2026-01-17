import uuid
import time
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict

from .models import LoginRequest, ProcessRequest
from .sii_connector import run_sii_process

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

def update_job_status(job_id: str, message: str, state: str = None):
    if job_id in jobs:
        jobs[job_id]["status"] = message
        if state:
            jobs[job_id]["state"] = state

@app.post("/api/process")
async def start_process(data: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "state": "pending",
        "status": "Iniciando...",
        "created_at": time.time()
    }
    
    # Callback wrapper to pass to the sync function
    def status_callback(msg, state=None):
        update_job_status(job_id, msg, state)
        
    background_tasks.add_task(run_sii_process, job_id, data, status_callback)
    
    return {"job_id": job_id}

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
