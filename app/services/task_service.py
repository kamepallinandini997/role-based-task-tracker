# app/services/task_service.py
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

from app.db import task_collection  # your motor collection
from app.schemas.task import (
    TaskCreate,
    TaskUpdateAdmin,
    TaskUpdateDeveloper,
    TaskUpdateTester,
    TaskAppendRemarks,
    TaskOut,
)
from app.schemas.task import DevStatus, TesterStatus

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
    # ensure fields exist
    doc.setdefault("assigned_to_dev", None)
    doc.setdefault("assigned_to_tester", None)
    doc.setdefault("dev_status", None)
    doc.setdefault("tester_status", None)
    doc.setdefault("remarks", [])
    # created_at/updated_at might be stored as datetime already
    return doc

# --- Create ----------------------------------------------------------------

async def create_task(task_data: TaskCreate) -> Dict[str, Any]:
    """
    Create a task. If assigned_to_dev/tester provided, set corresponding status to 'pending'.
    Returns the created task as dict (serialized).
    """
    now = datetime.utcnow()
    doc = task_data.dict()
    # ensure defaults / initialize statuses/remarks
    assigned_dev = doc.get("assigned_to_dev")
    assigned_tester = doc.get("assigned_to_tester")
    doc["dev_status"] = DevStatus.pending.value if assigned_dev else None
    doc["tester_status"] = TesterStatus.pending.value if assigned_tester else None
    doc["remarks"] = []
    doc["created_at"] = now
    doc["updated_at"] = now

    result = await task_collection.insert_one(doc)
    created = await task_collection.find_one({"_id": result.inserted_id})
    return _serialize_task(created)

# --- Get -------------------------------------------------------------------

async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    try:
        oid = _oid(task_id)
    except ValueError:
        return None
    doc = await task_collection.find_one({"_id": oid})
    return _serialize_task(doc)

# --- Assign (Admin/Manager) ------------------------------------------------

async def assign_task(task_id: str, developer: Optional[str] = None, tester: Optional[str] = None) -> Dict[str, Any]:
    """
    Assign developer and/or tester. Auto-sets dev_status/tester_status to 'pending'
    when assignment happens and the status was previously None.
    Returns updated task.
    """
    oid = _oid(task_id)
    current = await task_collection.find_one({"_id": oid})
    if not current:
        raise ValueError("Task not found")

    update = {}
    # set assigned_to and set status to pending if previously None or empty
    if developer is not None:
        update["assigned_to_dev"] = developer
        if not current.get("dev_status"):
            update["dev_status"] = DevStatus.pending.value
    if tester is not None:
        update["assigned_to_tester"] = tester
        if not current.get("tester_status"):
            update["tester_status"] = TesterStatus.pending.value

    if not update:
        # nothing to change
        return _serialize_task(current)

    update["updated_at"] = datetime.utcnow()
    updated = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    return _serialize_task(updated)

# --- Admin full update -----------------------------------------------------

async def update_task_admin(task_id: str, payload: TaskUpdateAdmin) -> Dict[str, Any]:
    """
    Admin/Manager full update (title, description, priority, due_date, assigned_to_*).
    This enforces auto-status logic when assignees are added.
    """
    oid = _oid(task_id)
    current = await task_collection.find_one({"_id": oid})
    if not current:
        raise ValueError("Task not found")

    data = payload.dict(exclude_none=True)
    to_set = {}
    # fields allowed for admin update
    for f in ["title", "description", "priority", "due_date", "assigned_to_dev", "assigned_to_tester"]:
        if f in data:
            to_set[f] = data[f]

    # handle auto-status for assignments
    if "assigned_to_dev" in to_set:
        if not current.get("dev_status"):
            to_set["dev_status"] = DevStatus.pending.value
    if "assigned_to_tester" in to_set:
        if not current.get("tester_status"):
            to_set["tester_status"] = TesterStatus.pending.value

    if to_set:
        to_set["updated_at"] = datetime.utcnow()
        updated = await task_collection.find_one_and_update(
            {"_id": oid}, {"$set": to_set}, return_document=ReturnDocument.AFTER
        )
        return _serialize_task(updated)

    # nothing changed
    return _serialize_task(current)

# --- Developer updates -----------------------------------------------------

async def update_dev_status(task_id: str, user_email: str, payload: TaskUpdateDeveloper) -> Dict[str, Any]:
    """
    Developer updates dev_status for own assigned tasks.
    Allowed values come from DevStatus enum.
    """
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        raise ValueError("Task not found")

    if task.get("assigned_to_dev") != user_email:
        raise PermissionError("Task not assigned to this developer")

    new_status = payload.dev_status.value if isinstance(payload.dev_status, DevStatus) else payload.dev_status
    # minimal validation for status transitions could be added here
    update = {"dev_status": new_status, "updated_at": datetime.utcnow()}
    updated = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    return _serialize_task(updated)


async def append_dev_remarks(task_id: str, user_email: str, payload: TaskAppendRemarks) -> Dict[str, Any]:
    """
    Append developer remarks to the shared remarks array. Stores string entries as-is.
    """
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        raise ValueError("Task not found")
    if task.get("assigned_to_dev") != user_email:
        raise PermissionError("Task not assigned to this developer")

    now = datetime.utcnow()
    # we could include author & timestamp in remarks, but schema currently uses simple strings
    # to avoid schema change, prepend short author tag
    tagged = [f"DEV ({user_email}) [{now.isoformat()}]: {r}" for r in payload.remarks]
    updated = await task_collection.find_one_and_update(
        {"_id": oid},
        {"$push": {"remarks": {"$each": tagged}}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_task(updated)

# --- Tester updates --------------------------------------------------------

async def update_tester_status(task_id: str, user_email: str, payload: TaskUpdateTester) -> Dict[str, Any]:
    """
    Tester updates tester_status (testing/test/closed) for tasks assigned to them.
    Enforce that developer must have completed the task first (dev_status == 'completed').
    """
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        raise ValueError("Task not found")
    if task.get("assigned_to_tester") != user_email:
        raise PermissionError("Task not assigned to this tester")

    # require developer completed before testing (unless admin overrides)
    if task.get("dev_status") != DevStatus.completed.value:
        raise PermissionError("Developer must complete the task before tester can update status")

    # update tester_status and optionally replace remarks if provided
    update = {"tester_status": payload.tester_status.value if isinstance(payload.tester_status, TesterStatus) else payload.tester_status,
              "updated_at": datetime.utcnow()}

    if payload.remarks is not None:
        # replace remarks entirely (admin could still modify)
        update["remarks"] = payload.remarks

    updated = await task_collection.find_one_and_update(
        {"_id": oid}, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    return _serialize_task(updated)


async def append_tester_remarks(task_id: str, user_email: str, payload: TaskAppendRemarks) -> Dict[str, Any]:
    """
    Append tester remarks to the shared remarks array.
    """
    oid = _oid(task_id)
    task = await task_collection.find_one({"_id": oid})
    if not task:
        raise ValueError("Task not found")
    if task.get("assigned_to_tester") != user_email:
        raise PermissionError("Task not assigned to this tester")

    now = datetime.utcnow()
    tagged = [f"TESTER ({user_email}) [{now.isoformat()}]: {r}" for r in payload.remarks]
    updated = await task_collection.find_one_and_update(
        {"_id": oid},
        {"$push": {"remarks": {"$each": tagged}}, "$set": {"updated_at": now}},
        return_document=ReturnDocument.AFTER,
    )
    return _serialize_task(updated)

# --- Filtering / listing ---------------------------------------------------

async def _build_query_from_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    q = {}
    # direct task fields
    if filters.get("project_id"):
        q["project_id"] = filters["project_id"]
    if filters.get("assigned_to_dev"):
        q["assigned_to_dev"] = filters["assigned_to_dev"]
    if filters.get("assigned_to_tester"):
        q["assigned_to_tester"] = filters["assigned_to_tester"]
    if filters.get("dev_status"):
        q["dev_status"] = filters["dev_status"]
    if filters.get("tester_status"):
        q["tester_status"] = filters["tester_status"]
    if filters.get("created_by"):
        q["created_by"] = filters["created_by"]
    # Note: experience_gt and joined_after require lookup to users collection.
    # TODO: implement cross-collection filtering if user data is available.
    return q


async def get_all_tasks(filters: Dict[str, Any], current_user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return tasks according to the caller's role and provided filters.
    Admin/Manager: can see all tasks (filters respected)
    Developer: only tasks assigned_to_dev == their email
    Tester: only tasks assigned_to_tester == their email
    """
    q = await _build_query_from_filters(filters or {})
    role = current_user.get("role")
    email = current_user.get("email")
    if role == "developer":
        q["assigned_to_dev"] = email
    elif role == "tester":
        q["assigned_to_tester"] = email
    # managers/admins: no extra restriction (optionally managers could be scoped to projects)
    cursor = task_collection.find(q).sort("created_at", -1)
    docs = await cursor.to_list(length=500)  # cap list
    return [_serialize_task(d) for d in docs]

async def get_my_tasks(current_user: Dict[str, Any], filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    role = current_user.get("role")
    if role == "developer":
        filters = filters or {}
        filters["assigned_to_dev"] = current_user.get("email")
        return await get_all_tasks(filters, current_user)
    if role == "tester":
        filters = filters or {}
        filters["assigned_to_tester"] = current_user.get("email")
        return await get_all_tasks(filters, current_user)
    # for admin/manager, return all (or use get_all_tasks directly)
    return await get_all_tasks(filters or {}, current_user)

# --- Delete ----------------------------------------------------------------

async def delete_task(task_id: str) -> bool:
    oid = _oid(task_id)
    result = await task_collection.delete_one({"_id": oid})
    return result.deleted_count == 1
