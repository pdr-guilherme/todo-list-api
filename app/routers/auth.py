from fastapi import APIRouter, status

router = APIRouter(tags=["auth"])


@router.post("/register", operation_id="register", status_code=status.HTTP_201_CREATED)
def register() -> None: ...


@router.post("/login", operation_id="login")
def login() -> None: ...


@router.get("/me", operation_id="get_profile")
def get_profile() -> None: ...
