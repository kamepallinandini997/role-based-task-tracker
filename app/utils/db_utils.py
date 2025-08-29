from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGO_URL, DB_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_collection = db["users"]
login_attempts_collection   = db["login_attempts"]
password_resets_collection = db["password_resets"]
projects_collection = db["projects"]
task_collection = db["tasks"]
