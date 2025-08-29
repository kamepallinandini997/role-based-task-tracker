from fastapi import APIRouter, Depends
from app.schemas.project_schema import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import create_project, update_project, get_project, list_projects, delete_project
from app.utils.auth_utils import get_current_user

router = APIRouter()

# RB check helper
def check_role(user, allowed_roles=["admin", "manager"]):
    return user["role"] in allowed_roles

# Create project
@router.post("/", response_model=dict)
async def creates_project(project: ProjectCreate, user=Depends(get_current_user)):
    if not check_role(user):
        return {"success": False, "message": "Not authorized"}
    result = await create_project(user["user_id"], project.model_dump())
    return result

# Update project
@router.put("/{project_id}", response_model=dict)
async def updates_project(project_id: str, project: ProjectUpdate, user=Depends(get_current_user)):
    if not check_role(user):
        return {"success": False, "message": "Not authorized"}
    return await update_project(project_id, project.model_dump(exclude_unset=True))

# Get single project
@router.get("/{project_id}", response_model=dict)
async def gets_project(project_id: str, user=Depends(get_current_user)):
    return await get_project(project_id)

# List all projects
@router.get("/", response_model=dict)
async def lists_projects(user=Depends(get_current_user)):
    return await list_projects()

# Delete project
@router.delete("/{project_id}", response_model=dict)
async def deletes_project(project_id: str, user=Depends(get_current_user)):
    if not check_role(user):
        return {"success": False, "message": "Not authorized"}
    return await delete_project(project_id)
