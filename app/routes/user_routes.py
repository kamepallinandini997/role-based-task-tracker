from datetime import datetime
from pydantic import EmailStr
from urllib.request import Request
from app.utils.db_utils import login_attempts_collection
from fastapi import APIRouter, HTTPException, status
from app.schemas.user_schema import LoginRequest, LoginResponse, PasswordChangeRequest, PasswordResetRequest, RegisterUser, RegisterResponse
from app.services.user_service import change_password, login_user, register_user, request_password_reset
from fastapi.security import HTTPBearer
from fastapi import Depends

auth_scheme = HTTPBearer()

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
async def request_password_reset_endpoint(payload: PasswordResetRequest):
    result = await request_password_reset(payload.email)
    return result

@router.post("/change-password")
async def change_password_endpoint(payload: PasswordChangeRequest):
    result = await change_password(payload.email, payload.otp, payload.new_password)
    return result

@router.post("/logout")
async def logout(credentials: HTTPBearer = Depends(auth_scheme)):
    token = credentials.credentials

    # Find the active login attempt for this token
    attempt = await login_attempts_collection.find_one({"token": token, "expired": False})
    if not attempt:
        raise HTTPException(status_code=401, detail="Token already expired or invalid")

    # Mark the token as expired and set logout time
    await login_attempts_collection.update_one(
        {"_id": attempt["_id"]},
        {"$set": {"expired": True, "logout_time": datetime.utcnow()}}
    )

    return {"message": "Successfully logged out"}
