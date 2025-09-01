from http.client import HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from app.utils.db_utils import task_collection
from app.schemas import (
    TaskCreate,
    TaskUpdateAdmin,
    TaskUpdateDeveloper,
    TaskUpdateTester,
    TaskAppendRemarks,
    DevStatus,
    TesterStatus
)
from app.utils.db_utils import users_collection
from app.utils.logger import logger  

# --- Helpers ---------------------------------------------------------------

def _oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError("Invalid id")

def _serialize_task(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    doc.setdefault("assigned_to_dev", None)
    doc.setdefault("assigned_to_tester", None)
    doc.setdefault("dev_status", None)
    doc.setdefault("tester_status", None)
    doc.setdefault("remarks", [])
    return doc

# --- Create ----------------------------------------------------------------

async def create_task(task_data: TaskCreate) -> Dict[str, Any]:
    now = datetime.utcnow()
    doc = task_data.dict()
    assigned_dev = doc.get("assigned_to_dev")
    assigned_tester = doc.get("assigned_to_tester")
    doc["dev_status"] = DevStatus.pending.value if assigned_dev else None
    doc["tester_status"] = TesterStatus.pending.value if assigned_tester else None
    doc["remarks"] = []
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await task_collection.insert_one(doc)
    created = await task_collection.find_one({"_id": result.inserted_id})
    
    logger.info(f"Task created: {doc.get('title')} by {doc.get('created_by')} (ID: {str(result.inserted_id)})")
    return _serialize_task(created)

# --- Get -------------------------------------------------------------------

async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = _oid(task_id)
    except ValueError:
        logger.error(f"Invalid task ID format: {task_id}")
        return None
    doc = await task_collection.find_one({"_id": oid})
    return _serialize_task(doc)

# --- Assign (Admin/Manager) ------------------------------------------------

async def assign_task(task_id: str, developer: Optional[str] = None, tester: Optional[str] = None) -> Dict[str, Any]:
    """
    Assign developer and/or tester. Validates that users exist.
    Auto-sets dev_status/tester_status to 'pending' when assignment happens.
    Returns updated task.
    """
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        logger.error(f"Task not found for assignment: {task_id}")
        raise ValueError("Task not found")

    update = {}

    # --- Validate developer ---
    if developer is not None:
        dev_user = await users_collection.find_one({"email": developer, "role": "developer"})
        if not dev_user:
            logger.warning(f"Assignment failed: Developer {developer} not found")
            raise HTTPException(status_code=400, detail=f"Developer {developer} does not exist")
        update["assigned_to_dev"] = developer
        if not task.get("dev_status"):
            update["dev_status"] = DevStatus.pending.value

    # --- Validate tester ---
    if tester is not None:
        tester_user = await users_collection.find_one({"email": tester, "role": "tester"})
        if not tester_user:
            logger.warning(f"Assignment failed: Tester {tester} not found")
            raise HTTPException(status_code=400, detail=f"Tester {tester} does not exist")
        update["assigned_to_tester"] = tester
        if not task.get("tester_status"):
            update["tester_status"] = TesterStatus.pending.value

    if not update:
        logger.info(f"No changes for task assignment: {task_id}")
        return _serialize_task(task)

    update["updated_at"] = datetime.utcnow()
    updated_task = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )

    logger.info(
        f"Task {task_id} assigned successfully by service. Dev: {developer}, Tester: {tester}"
    )
    return _serialize_task(updated_task)


# --- Admin full update -----------------------------------------------------

async def update_task_admin(task_id: str, payload: TaskUpdateAdmin) -> Dict[str, Any]:
    oid = _oid(task_id)
    current = await task_collection.find_one({"_id": oid})
    if not current:
        logger.error(f"Admin tried updating non-existent task: {task_id}")
        raise ValueError("Task not found")

    data = payload.dict(exclude_none=True)
    to_set = {}
    for f in ["title", "description", "priority", "due_date", "assigned_to_dev", "assigned_to_tester"]:
        if f in data:
            to_set[f] = data[f]

    if "assigned_to_dev" in to_set and not current.get("dev_status"):
        to_set["dev_status"] = DevStatus.pending.value
    if "assigned_to_tester" in to_set and not current.get("tester_status"):
        to_set["tester_status"] = TesterStatus.pending.value

    if to_set:
        to_set["updated_at"] = datetime.utcnow()
        updated = await task_collection.find_one_and_update(
            {"_id": oid}, {"$set": to_set}, return_document=ReturnDocument.AFTER
        )
        logger.info(f"Task {task_id} updated by Admin/Manager")
        return _serialize_task(updated)

    return _serialize_task(current)

# --- Developer updates -----------------------------------------------------

async def update_dev_status(task_id: str, user_email: str, payload: TaskUpdateDeveloper) -> Dict[str, Any]:
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        logger.error(f"Developer {user_email} tried updating non-existent task: {task_id}")
        raise ValueError("Task not found")

    if task.get("assigned_to_dev") != user_email:
        logger.warning(f"Unauthorized Dev {user_email} attempted status update for task {task_id}")
        raise PermissionError("Task not assigned to this developer")

    new_status = payload.dev_status.value if isinstance(payload.dev_status, DevStatus) else payload.dev_status
    update = {"dev_status": new_status, "updated_at": datetime.utcnow()}
    updated = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    logger.info(f"Developer {user_email} updated status for Task {task_id} → {new_status}")
    return _serialize_task(updated)

async def append_dev_remarks(task_id: str, user_email: str, payload: TaskAppendRemarks) -> Dict[str, Any]:
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        logger.error(f"Developer {user_email} tried adding remarks to non-existent task: {task_id}")
        raise ValueError("Task not found")
    if task.get("assigned_to_dev") != user_email:
        logger.warning(f"Unauthorized Dev {user_email} attempted to add remarks for task {task_id}")
        raise PermissionError("Task not assigned to this developer")

    now = datetime.utcnow()
    tagged = [f"DEV ({user_email}) [{now.isoformat()}]: {r}" for r in payload.remarks]
    updated = await task_collection.find_one_and_update(
        {"_id": oid},
        {"$push": {"remarks": {"$each": tagged}}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    logger.info(f"Developer {user_email} added remarks to Task {task_id}")
    return _serialize_task(updated)

# --- Tester updates --------------------------------------------------------

async def update_tester_status(task_id: str, user_email: str, payload: TaskUpdateTester) -> Dict[str, Any]:
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        logger.error(f"Tester {user_email} tried updating non-existent task: {task_id}")
        raise ValueError("Task not found")
    if task.get("assigned_to_tester") != user_email:
        logger.warning(f"Unauthorized Tester {user_email} attempted status update for task {task_id}")
        raise PermissionError("Task not assigned to this tester")

    if task.get("dev_status") != DevStatus.completed.value:
        logger.warning(f"Tester {user_email} attempted to update status before Dev completed task {task_id}")
        raise PermissionError("Developer must complete the task before tester can update status")

    update = {
        "tester_status": payload.tester_status.value if isinstance(payload.tester_status, TesterStatus) else payload.tester_status,
        "updated_at": datetime.utcnow()
    }

    if payload.remarks is not None:
        update["remarks"] = payload.remarks

    updated = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    logger.info(f"Tester {user_email} updated status for Task {task_id}")
    return _serialize_task(updated)

async def append_tester_remarks(task_id: str, user_email: str, payload: TaskAppendRemarks) -> Dict[str, Any]:
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        logger.error(f"Tester {user_email} tried adding remarks to non-existent task: {task_id}")
        raise ValueError("Task not found")
    if task.get("assigned_to_tester") != user_email:
        logger.warning(f"Unauthorized Tester {user_email} attempted to add remarks for task {task_id}")
        raise PermissionError("Task not assigned to this tester")

    now = datetime.utcnow()
    tagged = [f"TESTER ({user_email}) [{now.isoformat()}]: {r}" for r in payload.remarks]
    updated = await task_collection.find_one_and_update(
        {"_id": oid},
        {"$push": {"remarks": {"$each": tagged}}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    logger.info(f"Tester {user_email} added remarks to Task {task_id}")
    return _serialize_task(updated)

# --- Delete ----------------------------------------------------------------

async def delete_task(task_id: str) -> bool:
    oid = _oid(task_id)
    result = await task_collection.delete_one({"_id": oid})
    if result.deleted_count == 1:
        logger.warning(f"Task deleted: {task_id}")
        return True
    else:
        logger.error(f"Failed to delete task: {task_id}")
        return False
