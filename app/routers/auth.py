from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, SessionDep
from app.models.auth import Token, User
from app.schema.auth import LoginData, TokenResponse, UserCreate
from app.security import DUMMY_HASH, create_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    operation_id="register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
)
def register(data: UserCreate, db: SessionDep) -> TokenResponse:
    hashed_password = hash_password(data.password)
    db_user = User(name=data.name, email=data.email, hashed_password=hashed_password)

    try:
        db.add(db_user)
        db.flush()

        token = create_token()
        db_token = Token(key=token, user_id=db_user.id)
        db.add(db_token)

        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from error

    db.refresh(db_user)
    db.refresh(db_token)

    response = TokenResponse(token=token)
    return response


@router.post("/login", operation_id="login", response_model=TokenResponse)
def login(data: LoginData, db: SessionDep) -> TokenResponse:
    user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    hashed = user.hashed_password if user else DUMMY_HASH
    password_valid = verify_password(data.password, hashed)

    if user is None or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return TokenResponse(token=user.token.key)


@router.get("/me", operation_id="get_profile")
def get_profile(user: CurrentUser):
    return user
