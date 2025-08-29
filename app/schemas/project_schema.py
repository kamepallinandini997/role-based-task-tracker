from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: Literal["active","completed","on_hold"] = "active"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    status: Optional[Literal["active","completed","on_hold"]]

class ProjectResponse(ProjectBase):
    id: str
    created_by: str
    created_at: datetime
    updated_at: datetime