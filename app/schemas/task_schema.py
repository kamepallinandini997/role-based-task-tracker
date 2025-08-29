from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from enum import Enum

class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    developer = "developer"
    tester = "tester"

class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class DevStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class TesterStatus(str, Enum):
    pending = "pending"
    tested = "tested"
    closed = "closed"


# -------- Base --------
class TaskBase(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: Optional[str] = Field(default=None, max_length=10_000)
    priority: Priority = Priority.medium
    due_date: Optional[datetime] = None
    project_id: str = Field(..., description="Project ObjectId as string")

# -------- Create --------
class TaskCreate(TaskBase):
    created_by: EmailStr
    # Optional assignees at create time.
    assigned_to_dev: Optional[EmailStr] = None
    assigned_to_tester: Optional[EmailStr] = None

# -------- Admin/Manager update (no direct status writes) --------
class TaskUpdateAdmin(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=160)
    description: Optional[str] = Field(default=None, max_length=10_000)
    priority: Optional[Priority] = None
    due_date: Optional[datetime] = None
    assigned_to_dev: Optional[EmailStr] = None
    assigned_to_tester: Optional[EmailStr] = None

# -------- Developer update (only dev status) --------
class TaskUpdateDeveloper(BaseModel):
    dev_status: DevStatus

# -------- Tester update (status + optional remarks) --------
class TaskUpdateTester(BaseModel):
    tester_status: TesterStatus
    # optional add/replace pattern: pass list to replace; use separate endpoint to append
    remarks: Optional[List[str]] = None

# -------- Remarks append endpoints (optional but handy) --------
class TaskAppendRemarks(BaseModel):
    remarks: List[str] = Field(min_length=1)

# -------- Filtering (shared) --------
class TaskFilter(BaseModel):
    # Admin/Manager can use all; Dev/Tester will be constrained in service layer
    project_id: Optional[str] = None
    assigned_to_dev: Optional[EmailStr] = None
    assigned_to_tester: Optional[EmailStr] = None
    dev_status: Optional[DevStatus] = None
    tester_status: Optional[TesterStatus] = None
    created_by: Optional[EmailStr] = None
    # user-based filters (resolved via user service -> query by users then task assignees)
    experience_gt: Optional[int] = Field(default=None, ge=0, description="Years")
    joined_after: Optional[datetime] = None

# -------- DB Model -> Response --------
class TaskOut(TaskBase):
    id: str = Field(alias="id")  # expose stringified ObjectId
    assigned_to_dev: Optional[EmailStr] = None
    assigned_to_tester: Optional[EmailStr] = None
    dev_status: Optional[DevStatus] = None
    tester_status: Optional[TesterStatus] = None
    remarks: List[str] = []
    created_by: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
