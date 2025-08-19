from app.utils.logger import logger
from fastapi import FastAPI

app = FastAPI(
    title = "Role Based Task Assignment and Tracking System",
    version = "1.0.0"
)

@app.get("/health-check")
def health_check():
    logger.info("Application started successfully")
    return {"Status": "Healthy"}

