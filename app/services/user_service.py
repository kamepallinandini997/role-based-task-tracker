from datetime import datetime
from app.utils.db_utils import users_collection,login_attempts_collection
from app.schemas.user_schema import RegisterUser
from app.utils.auth_utils import create_jwt_token, get_user_by_email, hash_password, validate_password_strength, verify_password
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

async def login_user(email: str, password: str) -> dict:
    existing_user = await get_user_by_email(email)
    
    if not existing_user:
        await login_attempts_collection.insert_one({
            "email": email,
            "timestamp": datetime.utcnow(),
            "success": False,
        })
        logger.warning(f"Login failed: user not found for email={email}")
        return {"success": False, "message": "Invalid credentials", "data": None}
    
    password_valid = verify_password(password, existing_user["password"])
    if not password_valid:
        await login_attempts_collection.insert_one({
            "user_id": str(existing_user["_id"]),
            "timestamp": datetime.utcnow(),
            "success": False,
        })
        logger.warning(f"Login failed: invalid password for email={email}")
        return {"success": False, "message": "Invalid credentials", "data": None}
    
    # Successful login
    token = create_jwt_token(str(existing_user["_id"]), existing_user["role"])
    
    await login_attempts_collection.insert_one({
        "user_id": str(existing_user["_id"]),
        "timestamp": datetime.utcnow(),
        "success": True,
    })
    logger.info(f"Login successful for user_id={existing_user['_id']} email={email}")
    
    return {
        "success": True,
        "message": "Login successful",
        "data": {
            "token": token,
            "user": {
                "id": str(existing_user["_id"]),
                "email": existing_user["email"],
                "role": existing_user["role"]
            }
        }
    }