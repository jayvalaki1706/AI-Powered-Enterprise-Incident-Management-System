from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class DepartmentCreate(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamCreate(BaseModel):
    name: str
    department_id: UUID


class TeamResponse(BaseModel):
    id: UUID
    name: str
    department_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
