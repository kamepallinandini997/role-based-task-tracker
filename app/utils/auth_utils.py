import re
from passlib.context import CryptContext
from app.utils.logger import logger  # Import your logger
from app.utils.db_utils import users_collection

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    try:
        hashed = pwd_context.hash(password)
        logger.info("Password hashed successfully")
        return hashed
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        logger.info("Password verification result: %s", is_valid)
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False
    
async def get_user_by_email(email: str) -> dict | None:
    """
    Fetch a user by email from the database.
    Returns the user document if found, else None.
    """
    try:
        user = await users_collection.find_one({"email": email})
        if user:
            logger.info(f"User found with email: {email}")
        else:
            logger.info(f"No user found with email: {email}")
        return user
    except Exception as e:
        logger.error(f"Error fetching user by email ({email}): {e}")
        return None


def validate_password_strength(password: str) -> (bool, str):
    """
    Validate password strength.
    Returns (True, "") if valid, else (False, reason).
    """
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
