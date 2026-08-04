from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="Task title.")
    description: str | None = Field(
        default=None, max_length=300, description="Optional task description."
    )


class TaskCreate(TaskBase):
    model_config = ConfigDict(str_strip_whitespace=True)
    status: TaskStatus | None = Field(
        default=TaskStatus.PENDING, description="Task status. Defaults to pending."
    )


class TaskPublic(TaskBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(description="Task ID", json_schema_extra={"readOnly": True})
    status: TaskStatus = Field(description="Task status.")
    created_at: datetime = Field(
        description="...", json_schema_extra={"readOnly": True}
    )
    updated_at: datetime = Field(
        description="...", json_schema_extra={"readOnly": True}
    )


class TaskList(BaseModel):
    data: list[TaskPublic] = Field(description="List of user tasks.")
    page: int = Field(description="Current data page.")
    limit: int = Field(description="Number of tasks to be returned.")
    total: int = Field(description="Total count of user tasks.")


class TaskListQueryParams(BaseModel):
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=10, ge=1, le=100)
    search: str | None = Field(default=None, min_length=1, max_length=100)
    task_status: list[TaskStatus] | None = Field(default=None, alias="status")


class TaskUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        min_length=1, max_length=100, description="Task title. Can not be empty"
    )
    description: str | None = Field(max_length=300, description="Task description.")
    status: TaskStatus = Field(description="Task status.")


class TaskPartialUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Task title.",
    )
    description: str | None = Field(
        default=None, max_length=300, description="Optional task description."
    )
    status: TaskStatus | None = Field(default=None, description="Task status.")
