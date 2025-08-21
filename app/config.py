import os
# Mongo Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://kamepallinandini:nandini0987@resumestore.08fnipm.mongodb.net/")
DB_NAME = os.getenv("DB_NAME", "task_tracker")

# JWT configuration
SECRET_KEY = "your_secret_key_here"  # move to config/env in production
ALGORITHM = "HS256"

import os

# SMTP Email configuration
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")  # Default Gmail SMTP
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))          # 587 for TLS
EMAIL_USER = os.getenv("EMAIL_USER", "your_email@gmail.com")  # Replace with your email
EMAIL_PASS = os.getenv("EMAIL_PASS", "your_email_password")   # Replace with app password
