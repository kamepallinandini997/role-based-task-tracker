from datetime import datetime, timedelta
from app.utils.db_utils import users_collection,login_attempts_collection,password_resets_collection
from app.schemas.user_schema import RegisterUser
from app.utils.auth_utils import cleanup_expired_otps, create_jwt_token, generate_otp, get_user_by_email, hash_password, otp_expiry_time, send_otp_email, validate_password_strength, verify_password
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
        logger.warning(f"[LOGIN FAILED] User not found: email={email}")
        return {"success": False, "message": "Invalid credentials", "data": None}

    if existing_user.get("locked_until"):
        if datetime.utcnow() < existing_user["locked_until"]:
            logger.warning(
                f"[ACCOUNT LOCKED] Login attempt on locked account: email={email}, locked_until={existing_user['locked_until']}"
            )
            return {
                "success": False,
                "message": f"Account locked until {existing_user['locked_until']}. Please reset your password.",
                "action": "reset_password",
                "data": None
            }
        else:
            # Clear lock if time passed
            await users_collection.update_one(
                {"_id": existing_user["_id"]},
                {"$set": {"locked_until": None}}
            )
            logger.info(f"[LOCK CLEARED] Account unlocked automatically: email={email}")

    # Fetch last 5 login attempts
    last_attempts = await login_attempts_collection.find(
        {"user_id": str(existing_user["_id"])}
    ).sort("timestamp", -1).limit(5).to_list(5)

    consecutive_failures = 0
    for attempt in last_attempts:
        if not attempt["success"]:
            consecutive_failures += 1
        else:
            break  # Stop at first success

    if consecutive_failures >= 5:
        locked_until = datetime.utcnow() + timedelta(hours=2)
        await users_collection.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {"locked_until": locked_until}}
        )
        logger.warning(
            f"[ACCOUNT LOCKED] 5 consecutive failed attempts: email={email}, locked_until={locked_until}"
        )
        return {
            "success": False,
            "message": "Account locked due to 5 consecutive failed attempts. Please reset your password.",
            "action": "reset_password",
            "data": None
        }

    password_valid = verify_password(password, existing_user["password"])
    if not password_valid:
        await login_attempts_collection.insert_one({
            "user_id": str(existing_user["_id"]),
            "timestamp": datetime.utcnow(),
            "success": False,
        })
        logger.warning(f"[LOGIN FAILED] Invalid password: email={email}")
        return {"success": False, "message": "Invalid credentials", "data": None}
    
    # Successful login
    token = create_jwt_token(str(existing_user["_id"]), existing_user["role"])
    
    await login_attempts_collection.insert_one({
    "user_id": existing_user["_id"],
    "email": existing_user["email"],
    "token": token,
    "login_time": datetime.utcnow(),
    "expiry_time": datetime.utcnow() + timedelta(hours=24),
    "success": True,
    "expired": False,
    "logout_time": None
})
    logger.info(f"[LOGIN SUCCESS] User logged in: user_id={existing_user['_id']}, email={email}")
    
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


# Step 1: request password reset (generate OTP)
async def request_password_reset(email: str) -> dict:
    #
    await cleanup_expired_otps()

    otp = await generate_otp()
    expires_at = otp_expiry_time()
    
    await password_resets_collection.insert_one({
        "user_id": email,
        "otp": otp,
        "expires_at": expires_at,
        "created_at": datetime.utcnow()
    })
    
    # send OTP via email
    sent = await send_otp_email(email, otp)
    if not sent:
        return {"success": False, "message": "Failed to send OTP"}
    logger.info(f"Password reset OTP sent for email={email}")
    
    return {"success": True, "message": "OTP sent to your email"}

# Step 2: validate OTP
async def validate_password_reset_otp(email: str, otp: str) -> dict:
    
    record = await password_resets_collection.find_one({
        "user_id": email,
        "otp": otp,
        "expires_at": {"$gte": datetime.utcnow()}
    })
    if not record:
        logger.warning(f"Invalid or expired OTP ")
        return {"success": False, "message": "Invalid or expired OTP"}
    
    # Delete OTP after successful validation
    await password_resets_collection.delete_one({"_id": record["_id"]})
    logger.info(f"[OTP VALIDATED] OTP validated and removed for email={email}")

    
    logger.info(f"OTP validated for user : {email}")
    return {"success": True, "message": "OTP validated"}

# Step 3: change password
async def change_password(email: str, otp: str, new_password: str) -> dict:
    user = await get_user_by_email(email)
    
    if not user:
        return {"success": False, "message": "User not found"}
    
    # Validate OTP first
    otp_check = await validate_password_reset_otp(email, otp)
    if not otp_check["success"]:
        return otp_check
    
    # Validate password strength
    valid, reason = validate_password_strength(new_password)
    if not valid:
        return {"success": False, "message": reason}
    
    hashed = hash_password(new_password)
    if not hashed:
        return {"success": False, "message": "Error hashing password"}
    
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password": hashed,
            "password_changed_at": datetime.utcnow(),
            "locked_until": None
        }}
    )
    
    logger.info(f"Password changed successfully for user_id={user['_id']}")
    
    return {"success": True, "message": "Password changed successfully"}


