import os
# Mongo Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kamepallinandini:nandini0987@resumestore.08fnipm.mongodb.net/")
DB_NAME = os.getenv("DB_NAME", "task_tracker")

# JWT configuration
SECRET_KEY = "your_secret_key_here"  # move to config/env in production
ALGORITHM = "HS256"