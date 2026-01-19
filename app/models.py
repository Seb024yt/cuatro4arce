from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
from pydantic import BaseModel, EmailStr

# Database Models

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = Field(default=None)
    hashed_password: str
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    payment_status: str = Field(default="pending") # pending, paid
    payment_folio: Optional[str] = Field(default=None)
    max_companies: int = Field(default=1) # Default limit of 1 company
    
    companies: List["Company"] = Relationship(back_populates="user")

class Company(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rut: str = Field(index=True)
    clave_sii: str
    name: Optional[str] = None # Alias for the company
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    user: Optional[User] = Relationship(back_populates="companies")

# Pydantic Schemas for API

class Worker(BaseModel):
    nombre: str
    rut: str
    monto: int

class ProcessRequest(BaseModel):
    # Now we receive company_id instead of raw credentials, 
    # but for compatibility with existing logic, we might need to fetch credentials in backend
    company_id: Optional[int] = None 
    rutEmpresa: Optional[str] = None # Keeping optional for backward compatibility or direct use
    claveSII: Optional[str] = None
    mes: str
    anio: int
    correo: EmailStr
    trabajadores: List[Worker] = []

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    max_companies: int
    payment_status: str
    is_admin: bool
    companies: List["CompanyRead"] = []

class CompanyCreate(BaseModel):
    rut: str
    clave_sii: str
    name: str

class CompanyRead(BaseModel):
    id: int
    rut: str
    name: str

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UpgradeRequest(BaseModel):
    new_limit: int

class OnboardingRequest(BaseModel):
    full_name: str
    company_name: str
    company_rut: str
    company_sii: str

