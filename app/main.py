from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers.auth import router as auth_router
from app.routers.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


SWAGGER_UI = {
    "displayOperationId": True,
    "syntaxHighlight.theme": "tomorrow-night",
}

app = FastAPI(
    title="To-do List API",
    description="Restful API for task management with token authentication.",
    contact={"name": "Pedro Guilherme", "url": "https://github.com/pdr-guilherme"},
    openapi_tags=[
        {"name": "auth", "description": "Create, authenticate and read user accounts"},
        {"name": "tasks", "description": "Create, read, update and delete tasks"},
    ],
    swagger_ui_parameters=SWAGGER_UI,
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(tasks_router)
