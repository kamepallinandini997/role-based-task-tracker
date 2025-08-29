from app.utils.db_utils import projects_collection, tasks_collection
from datetime import datetime
from bson import ObjectId
from app.utils.logger import logger
from app.schemas.project_schema import ProjectResponse

async def create_project(user_id: str, project_data: dict) -> dict:
    try:
        # Case-insensitive duplicate check
        existing_project = await projects_collection.find_one(
            {"name": {"$regex": f"^{project_data['name']}$", "$options": "i"}}
        )
        if existing_project:
            return {"success": False, "message": "Project with this name already exists"}

        # Add metadata
        project_data["created_by"] = user_id
        project_data["created_at"] = datetime.utcnow()
        project_data["updated_at"] = datetime.utcnow()

        result = await projects_collection.insert_one(project_data)

        # Build response using Pydantic
        project_resp = ProjectResponse(
            id=str(result.inserted_id),
            name=project_data["name"],
            description=project_data.get("description"),
            status=project_data.get("status", "active"),
            created_by=project_data["created_by"],
            created_at=project_data["created_at"],
            updated_at=project_data["updated_at"],
        )

        project_resp_dict = project_resp.model_dump()
        project_resp_dict["tasks"] = []

        logger.info(f"Project created: {project_data['name']} by user_id={user_id}")
        return {"success": True, "data": project_resp_dict}

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        return {"success": False, "message": "Internal server error"}


async def update_project(project_id: str, update_data: dict) -> dict:
    try:
        update_data["updated_at"] = datetime.utcnow()
        result = await projects_collection.update_one({"_id": ObjectId(project_id)}, {"$set": update_data})
        if result.matched_count == 0:
            return {"success": False, "message": "Project not found"}

        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        project["id"] = str(project["_id"])
        project["tasks"] = await tasks_collection.find({"project_id": project_id}).to_list(100)

        project_resp = ProjectResponse(
            id=project["id"],
            name=project["name"],
            description=project.get("description"),
            status=project["status"],
            created_by=project["created_by"],
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )
        project_dict = project_resp.model_dump()
        project_dict["tasks"] = project["tasks"]

        return {"success": True, "data": project_dict}

    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return {"success": False, "message": "Internal server error"}


async def get_project(project_id: str) -> dict:
    try:
        project = await projects_collection.find_one({"_id": ObjectId(project_id)})
        if not project:
            return {"success": False, "message": "Project not found"}

        project["id"] = str(project["_id"])
        project["tasks"] = await tasks_collection.find({"project_id": project_id}).to_list(100)

        project_resp = ProjectResponse(
            id=project["id"],
            name=project["name"],
            description=project.get("description"),
            status=project["status"],
            created_by=project["created_by"],
            created_at=project["created_at"],
            updated_at=project["updated_at"],
        )
        project_dict = project_resp.model_dump()
        project_dict["tasks"] = project["tasks"]

        return {"success": True, "data": project_dict}
    except Exception as e:
        logger.error(f"Error fetching project: {e}")
        return {"success": False, "message": "Internal server error"}


async def list_projects() -> dict:
    try:
        projects_cursor = projects_collection.find()
        projects = await projects_cursor.to_list(100)
        project_list = []

        for p in projects:
            p["id"] = str(p["_id"])
            tasks = await tasks_collection.find({"project_id": p["id"]}).to_list(100)
            project_resp = ProjectResponse(
                id=p["id"],
                name=p["name"],
                description=p.get("description"),
                status=p["status"],
                created_by=p["created_by"],
                created_at=p["created_at"],
                updated_at=p["updated_at"],
            )
            project_dict = project_resp.model_dump()
            project_dict["tasks"] = tasks
            project_list.append(project_dict)

        return {"success": True, "data": project_list}
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return {"success": False, "message": "Internal server error"}


async def delete_project(project_id: str) -> dict:
    try:
        result = await projects_collection.delete_one({"_id": ObjectId(project_id)})
        if result.deleted_count == 0:
            return {"success": False, "message": "Project not found"}

        await tasks_collection.delete_many({"project_id": project_id})
        return {"success": True, "message": "Project and its tasks deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        return {"success": False, "message": "Internal server error"}
