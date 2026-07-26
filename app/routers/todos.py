from fastapi import APIRouter, status

router = APIRouter(prefix="/todos", tags=["todos"])


@router.post("/", operation_id="create_todo", status_code=status.HTTP_201_CREATED)
def create_todo() -> None: ...


@router.get("/", operation_id="list_todos")
def list_todos() -> None: ...


@router.get("/{todo_id}", operation_id="get_todo")
def get_todo(todo_id: int) -> None: ...


@router.put("/{todo_id}", operation_id="update_todo")
def update_todo(todo_id: int) -> None: ...


@router.patch("/{todo_id}", operation_id="partial_update_todo")
def partial_update_todo(todo_id: int) -> None: ...


@router.delete(
    "/{todo_id}", operation_id="delete_todo", status_code=status.HTTP_204_NO_CONTENT
)
def delete_todo(todo_id: int) -> None: ...
