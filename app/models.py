from pydantic import BaseModel, EmailStr
from typing import List, Optional

class Worker(BaseModel):
    nombre: str
    rut: str
    monto: int

class ProcessRequest(BaseModel):
    rutEmpresa: str
    claveSII: str
    mes: str
    anio: int
    correo: EmailStr
    trabajadores: List[Worker] = []

class LoginRequest(BaseModel):
    username: str
    password: str
