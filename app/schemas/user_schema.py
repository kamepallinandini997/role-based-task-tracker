from pydantic import BaseModel ,EmailStr
from typing import Optional,Literal
from datetime import date

class RegisterUser(BaseModel):
    name :  str
    email : EmailStr
    phone : str
    password : str
    date_of_birth : date
    date_of_joining : Optional[date] = None
    address : Optional[str] =None
    role: Literal["manager", "developer", "tester"] = "developer"

class RegisterResponse(BaseModel):
    email: EmailStr
    message: str = "Registration successful. Please log in to continue."

class LoginRequest(BaseModel):
    email: EmailStr 
    password: str 

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: dict | None = None
