# user_route.py
from fastapi import APIRouter, HTTPException, status
from app.schemas.user_schema import RegisterUser, RegisterResponse
from app.services.user_service import register_user

router = APIRouter()

@router.post("/register", response_model=RegisterResponse)
async def register(user: RegisterUser):
    success, message = await register_user(user)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    
    return RegisterResponse(email=user.email)
