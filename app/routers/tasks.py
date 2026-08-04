from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select

from app.dependencies import CurrentTask, CurrentUser, SessionDep
from app.models.tasks import Task
from app.schema.tasks import (
    TaskCreate,
    TaskList,
    TaskPartialUpdate,
    TaskPublic,
    TaskStatus,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/",
    operation_id="create_task",
    summary="Create a new task",
    description="Creates a task linked to the authenticated user. Title is required.",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskPublic,
    responses={404: {"description": "Task not found"}},
)
def create_task(
    user: CurrentUser,
    data: TaskCreate,
    db: SessionDep,
) -> TaskPublic:
    db_task = Task(
        user_id=user.id,
        title=data.title,
        description=data.description,
        status=data.status,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return TaskPublic.model_validate(db_task)


@router.get(
    "/",
    operation_id="list_tasks",
    summary="List all tasks",
    description="List all tasks belonging to the authenticated user.",
    response_model=TaskList,
    responses={404: {"description": "Task not found"}},
)
def list_tasks(
    user: CurrentUser,
    db: SessionDep,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    search: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    task_status: Annotated[list[TaskStatus] | None, Query(alias="status")] = None,
) -> TaskList:
    query = select(Task).where(Task.user_id == user.id).order_by(Task.id)
    count_query = select(func.count()).select_from(Task).where(Task.user_id == user.id)

    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
        count_query = count_query.where(Task.title.ilike(f"%{search}%"))

    if task_status:
        query = query.where(Task.status.in_(task_status))
        count_query = count_query.where(Task.status.in_(task_status))

    tasks = db.execute(query.offset((page - 1) * limit).limit(limit)).scalars().all()
    total = db.execute(count_query).scalar_one()

    return TaskList(
        data=[TaskPublic.model_validate(task) for task in tasks],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/{task_id}",
    operation_id="get_task",
    summary="Detail a task",
    description="Returns all details from a task.",
    response_model=TaskPublic,
    responses={404: {"description": "Task not found"}},
)
def get_task(
    task: CurrentTask,
) -> TaskPublic:
    return TaskPublic.model_validate(task)


@router.put(
    "/{task_id}",
    operation_id="update_task",
    summary="Update a task",
    description="Updates a task. All fields are required",
    response_model=TaskPublic,
    responses={404: {"description": "Task not found"}},
)
def update_task(
    task: CurrentTask,
    data: TaskUpdate,
    db: SessionDep,
) -> TaskPublic:
    update_data = data.model_dump()
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return TaskPublic.model_validate(task)


@router.patch(
    "/{task_id}",
    operation_id="partial_update_task",
    summary="Partially update a task",
    description="Updates a task. Only sent fields are updated.",
    response_model=TaskPublic,
    responses={404: {"description": "Task not found"}},
)
def partial_update_task(
    task: CurrentTask,
    data: TaskPartialUpdate,
    db: SessionDep,
) -> TaskPublic:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    return TaskPublic.model_validate(task)


@router.delete(
    "/{task_id}",
    operation_id="delete_task",
    summary="Delete a task",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Task not found"}},
)
def delete_task(
    task: CurrentTask,
    db: SessionDep,
) -> None:
    db.delete(task)
    db.commit()
    return None
