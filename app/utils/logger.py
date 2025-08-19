import logging
from logging.handlers import RotatingFileHandler
import os

# Create logs directory if not exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR,exist_ok=True)

# Log file path
LOG_FILE = os.path.join(LOG_DIR,"app.log")

# Defining log format
log_format = '%(asctime)s - %(levelname)s - %(filename)s - %(message)s'
formatter = logging.Formatter(log_format)

# File Handler with rotation(5 MB for file and keep 5 bacup counts)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024,backupCount=5)
file_handler.setFormatter(formatter)

# Get the logger
logger = logging.getLogger("user_registration")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

