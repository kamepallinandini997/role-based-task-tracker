from datetime import datetime
from app.utils.db_utils import users_collection
from app.schemas.user_schema import RegisterUser
from app.utils.auth_utils import get_user_by_email, hash_password, validate_password_strength
from app.utils.logger import logger
from datetime import datetime

async def register_user(user: RegisterUser) -> tuple[bool, str]:
    try:
        # Check if user already exists
        existing_user = await get_user_by_email(user.email)
        if existing_user:
            logger.warning(f"Registration failed: User already exists with email {user.email}")
            return False, "User already exists with this email."

        # Validate password strength
        if not validate_password_strength(user.password):
            logger.warning(f"Weak password attempt for email {user.email}")
            return False, "Password does not meet the required strength."

        # Hash password
        hashed_pwd = hash_password(user.password)

        # Prepare user document
        user_data = user.model_dump()
        user_data["password"] = hashed_pwd
        user_data["created_at"] = datetime.utcnow()
        user_data["date_of_birth"] = datetime.combine(user.date_of_birth, datetime.min.time())
        user_data["date_of_joining"] = datetime.combine(user.date_of_joining, datetime.min.time())


        # Insert user
        await users_collection.insert_one(user_data)

        logger.info(f"User registered successfully: {user.email}")
        return True, "User registered successfully."

    except Exception as e:
        logger.error(f"Error during user registration: {str(e)}")
        return False, "Internal Server Error"
