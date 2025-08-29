from app.utils.db_utils import projects_collection,tasks_collection
from datetime import datetime
from bson import ObjectId
from app.utils.logger import logger

#create new project
async def create_project(user_id: str, project_data: dict) -> dict:
    try:
        project_data["created_by"] = user_id
        project_data["created_at"] = datetime.utcnow()
        project_data["updated_at"] = datetime.utcnow()
        result = await projects_collection.insert_one(project_data)

        # Convert ObjectId to string
        project_data["id"] = str(result.inserted_id)
        project_data["tasks"] = []

        logger.info(f"Project created: {project_data['name']} by user_id={user_id}")
        return {"success": True, "data": project_data}
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return {"success": False, "message": "Internal server error"}

# update existing project
async def update_project(project_id: str, update_data: dict) -> dict:
    try:
        update_data["updated_at"] = datetime.utcnow()
        result = await projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
        if result.matched_count == 0:
            logger.warning(f"Project not found for update: project_id={project_id}")
            return {"success": False, "message": "Project not found"}

        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        project["id"] = str(project["_id"])
        project["tasks"] = await tasks_collection.find({"project_id": project_id}).to_list(100)
        logger.info(f"Project updated: project_id={project_id}")
        return {"success": True, "data": project}
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return {"success": False, "message": "Internal server error"}


# get single project by id
async def get_project(project_id: str) -> dict:
    try:
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            logger.warning(f"Project not found: project_id={project_id}")
            return {"success": False, "message": "Project not found"}

        project["id"] = str(project["_id"])
        project["tasks"] = await tasks_collection.find({"project_id": project_id}).to_list(100)
        return {"success": True, "data": project}
    except Exception as e:
        logger.error(f"Error fetching project: {e}")
        return {"success": False, "message": "Internal server error"}


# list all projects
async def list_projects() -> dict:
    try:
        projects_cursor = projects_collection.find()
        projects = await projects_cursor.to_list(100)
        for p in projects:
            p["id"] = str(p["_id"])
            p["tasks"] = await tasks_collection.find({"project_id": str(p["_id"])}).to_list(100)
        return {"success": True, "data": projects}
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return {"success": False, "message": "Internal server error"}


# delete project and its tasks
async def delete_project(project_id: str) -> dict:
    try:
        result = await projects_collection.delete_one({"_id": ObjectId(project_id)})
        if result.deleted_count == 0:
            logger.warning(f"Project not found for delete: project_id={project_id}")
            return {"success": False, "message": "Project not found"}

        await tasks_collection.delete_many({"project_id": project_id})
        logger.info(f"Project and tasks deleted: project_id={project_id}")
        return {"success": True, "message": "Project and its tasks deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return {"success": False, "message": "Internal server error"}
