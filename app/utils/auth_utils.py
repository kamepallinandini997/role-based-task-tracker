from datetime import datetime, timedelta
from email.mime.text import MIMEText
import random
import re
import smtplib
import jwt
from fastapi import Header, HTTPException
from passlib.context import CryptContext
from app.config import EMAIL_HOST, EMAIL_PASS, EMAIL_PORT, EMAIL_USER, SECRET_KEY, ALGORITHM
from app.utils.logger import logger
from app.utils.db_utils import users_collection,password_resets_collection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -------------------------
# Password hashing & verification
# -------------------------
def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    try:
        hashed = pwd_context.hash(password)
        logger.info("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.info(f"Password verification: {is_valid}")
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


# -------------------------
# Password strength validation
# -------------------------
def validate_password_strength(password: str) -> (bool, str):
    """Check password strength."""
    try:
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit."
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False, "Password must contain at least one special character."

        logger.info("Password strength validation passed")
        return True, ""
    except Exception as e:
        logger.error(f"Error validating password strength: {e}")
        return False, "Internal error during password validation."


# -------------------------
# JWT token creation & decoding
# -------------------------
ACCESS_TOKEN_EXPIRE_HOURS=24

def create_jwt_token(user_id: str, role: str) -> str:
    """Create a JWT token for a user."""
    try:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {"user_id": user_id, "role": role, "exp": expire}
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        logger.info(f"JWT token created for user_id={user_id}")
        return token
    except Exception as e:
        logger.error(f"Error creating JWT token: {e}")
        return None


def decode_jwt_token(token: str) -> dict:
    """Decode a JWT token and return payload."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.info(f"JWT token decoded successfully for user_id={payload.get('user_id')}")
        return {"success": True, "data": payload}
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return {"success": False, "message": "Token expired"}
    except jwt.InvalidTokenError:
        logger.warning("JWT token invalid")
        return {"success": False, "message": "Invalid token"}


# -------------------------
# Database helper
# -------------------------
async def get_user_by_email(email: str) -> dict | None:
    """
    Fetch a user by email from the database.
    Returns the user document if found, else None.
    """
    try:
        user = await users_collection.find_one({"email": email})
        if user:
            logger.info(f"User found with email: {email}")
        return user
    except Exception as e:
        logger.error(f"Error fetching user by email ({email}): {e}")
        return None

OTP_EXPIRE_MINUTES = 10  # OTP validity

async def generate_otp() -> str:
    otp = str(random.randint(100000, 999999))  # 6-digit OTP
    logger.info(f"OTP generated: {otp}")
    return otp

def otp_expiry_time() -> datetime:
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)

async def send_otp_email(to_email: str, otp: str) -> bool:
    try:
        subject = "Your Password Reset OTP"
        body = f"Your OTP for password reset is: {otp}. It is valid for {OTP_EXPIRE_MINUTES} minutes."
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = EMAIL_USER
        msg['To'] = to_email

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        logger.info(f"OTP email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Error sending OTP email to {to_email}: {e}")
        return False
    


async def cleanup_expired_otps():
    result = await password_resets_collection.delete_many({
        "expires_at": {"$lt": datetime.utcnow()}
    })
    if result.deleted_count > 0:
        logger.info(f"[OTP CLEANUP] Deleted {result.deleted_count} expired OTP records")

async def get_current_user(authorization: str = Header(...)):
    """
    Extracts JWT token from the Authorization header and returns user data.
    Raises 401 if token is missing, invalid, or expired.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    
    token = authorization.split(" ")[1]
    payload = decode_jwt_token(token)
    
    if not payload.get("success"):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return payload["data"]  # contains user_id and role
