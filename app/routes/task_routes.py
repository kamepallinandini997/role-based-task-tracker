# app/routes/task_routes.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.utils.auth_utils import get_current_user
from app.schemas.task_schema import TaskCreate,TaskOut,TaskUpdateAdmin,TaskUpdateDeveloper,TaskUpdateTester,TaskAppendRemarks

from app.services.task_service import (create_task,get_task_by_id,get_all_tasks,update_task_admin,
    assign_task,delete_task,update_dev_status,append_dev_remarks,update_tester_status,append_tester_remarks,get_my_tasks)

router = APIRouter()


# ---------------- Admin / Manager ------------------------------------------

@router.post("/", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_new_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create tasks")
    created = await create_task(task)
    return created


@router.get("/", response_model=List[TaskOut])
async def list_all_tasks(
    project_id: Optional[str] = Query(None),
    assigned_to_dev: Optional[str] = Query(None),
    assigned_to_tester: Optional[str] = Query(None),
    dev_status: Optional[str] = Query(None),
    tester_status: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    # only admin/manager should call list-all; but service will also restrict by role automatically
    if current_user["role"] not in ("admin", "manager", "developer", "tester"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    filters = {
        "project_id": project_id,
        "assigned_to_dev": assigned_to_dev,
        "assigned_to_tester": assigned_to_tester,
        "dev_status": dev_status,
        "tester_status": tester_status,
        "created_by": created_by,
    }
    tasks = await get_all_tasks(filters, current_user)
    return tasks


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # enforce access: developers/testers only view their tasks
    if current_user["role"] == "developer" and task.get("assigned_to_dev") != current_user.get("email"):
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    if current_user["role"] == "tester" and task.get("assigned_to_tester") != current_user.get("email"):
        raise HTTPException(status_code=403, detail="Not authorized to access this task")

    return task


@router.put("/{task_id}", response_model=TaskOut)
async def update_existing_task_admin(task_id: str, payload: TaskUpdateAdmin, current_user: dict = Depends(get_current_user)):
    # only admin/manager can call this endpoint to update assignments/details
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Not authorized to perform full update")
    try:
        updated = await update_task_admin(task_id, payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.put("/{task_id}/assign", response_model=TaskOut)
async def assign_task_route(task_id: str, developer: Optional[str] = None, tester: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(status_code=403, detail="Not authorized to assign tasks")
    try:
        updated = await assign_task(task_id, developer, tester)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_existing_task(task_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete tasks")
    success = await delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found or deletion failed")
    return {"message": "Task deleted"}


# ---------------- Developer -------------------------------------------------

@router.get("/my", response_model=List[TaskOut])
async def get_my_tasks_route(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "developer":
        raise HTTPException(status_code=403, detail="Not a developer")
    tasks = await get_my_tasks(current_user)
    return tasks


@router.put("/{task_id}/status", response_model=TaskOut)
async def update_dev_status_route(task_id: str, payload: TaskUpdateDeveloper, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "developer":
        raise HTTPException(status_code=403, detail="Not a developer")
    try:
        updated = await update_dev_status(task_id, current_user["email"], payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return updated


@router.put("/{task_id}/remarks", response_model=TaskOut)
async def append_dev_remarks_route(task_id: str, payload: TaskAppendRemarks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "developer":
        raise HTTPException(status_code=403, detail="Not a developer")
    try:
        updated = await append_dev_remarks(task_id, current_user["email"], payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return updated


# ---------------- Tester ---------------------------------------------------

@router.get("/my-testing", response_model=List[TaskOut])
async def get_my_testing_tasks(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "tester":
        raise HTTPException(status_code=403, detail="Not a tester")
    tasks = await get_my_tasks(current_user)
    return tasks


@router.put("/{task_id}/test-status", response_model=TaskOut)
async def update_test_status_route(task_id: str, payload: TaskUpdateTester, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "tester":
        raise HTTPException(status_code=403, detail="Not a tester")
    try:
        updated = await update_tester_status(task_id, current_user["email"], payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return updated


@router.put("/{task_id}/test-remarks", response_model=TaskOut)
async def append_test_remarks_route(task_id: str, payload: TaskAppendRemarks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "tester":
        raise HTTPException(status_code=403, detail="Not a tester")
    try:
        updated = await append_tester_remarks(task_id, current_user["email"], payload)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return updated
