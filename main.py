from app.utils.logger import logger
from app.routes import user_routes,project_routes
from fastapi import FastAPI

app = FastAPI(
    title = "Role Based Task Assignment and Tracking System",
    version = "1.0.0"
)

@app.get("/health-check")
def health_check():
    logger.info("Application started successfully")
    return {"Status": "Healthy"}

app.include_router(user_routes.router, prefix="/users")
app.include_router(project_routes.router, prefix="/projects")