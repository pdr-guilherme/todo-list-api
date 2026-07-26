from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.todos import router as todos_router

SWAGGER_UI = {
    "displayOperationId": True,
    "syntaxHighlight.theme": "tomorrow-night",
}

app = FastAPI(
    title="To-do list API",
    swagger_ui_parameters=SWAGGER_UI,
    openapi_tags=[
        {"name": "auth", "description": "User signup, signin and detailing"},
        {"name": "todos", "description": "To-do management"},
    ],
)

app.include_router(auth_router)
app.include_router(todos_router)
