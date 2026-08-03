from typing import Annotated

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth import Token
from app.models.tasks import Task
from app.schema.auth import UserPublic

SessionDep = Annotated[Session, Depends(get_db)]

security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: SessionDep,
) -> UserPublic:
    token = credentials.credentials
    db_token = db.execute(select(Token).where(Token.key == token)).scalar_one_or_none()

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return UserPublic.model_validate(db_token.user)


CurrentUser = Annotated[UserPublic, Depends(get_current_user)]


def get_task_or_404(
    task_id: Annotated[int, Path(description="Task ID", ge=1)],
    db: SessionDep,
    user: CurrentUser,
) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return task


CurrentTask = Annotated[Task, Depends(get_task_or_404)]
