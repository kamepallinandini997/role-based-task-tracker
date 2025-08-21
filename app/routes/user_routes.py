# user_route.py
from urllib.request import Request
from fastapi import APIRouter, HTTPException, status,EmailStr
from app.schemas.user_schema import LoginRequest, LoginResponse, RegisterUser, RegisterResponse
from app.services.user_service import change_password, login_user, register_user, request_password_reset

router = APIRouter()

@router.post("/register", response_model=RegisterResponse)
async def register(user: RegisterUser):
    success, message = await register_user(user)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return RegisterResponse(email=user.email)

@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    result = await login_user(payload.email, payload.password)
    return LoginResponse(**result)


@router.post("/request-password-reset")
async def request_password_reset_endpoint(email: EmailStr):
    result = await request_password_reset(email)
    return result

@router.post("/change-password")
async def change_password_endpoint(email: EmailStr,otp: str ,new_password: str ):
    result = await change_password(email, otp, new_password)
    return result
