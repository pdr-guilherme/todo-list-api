from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.dependencies import CurrentUser, SessionDep
from app.models.auth import Token, User
from app.rate_limit import limiter
from app.schema.auth import LoginData, TokenResponse, UserCreate, UserPublic
from app.security import DUMMY_HASH, create_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    operation_id="register",
    summary="Create an account",
    description="Creates a new account and returns an authentication token",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenResponse,
)
@limiter.limit("3/minute")
def register(
    request: Request,
    response: Response,
    data: UserCreate,
    db: SessionDep,
) -> TokenResponse:
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


@router.post(
    "/login",
    operation_id="login",
    description="Validates the given credentials and returns an authentication token",
    response_model=TokenResponse,
)
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    data: LoginData,
    db: SessionDep,
) -> TokenResponse:
    user = db.execute(select(User).where(User.email == data.email)).scalar_one_or_none()
    hashed = user.hashed_password if user else DUMMY_HASH
    password_valid = verify_password(data.password, hashed)

    if user is None or not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    return TokenResponse(token=user.token.key)


@router.get(
    "/me",
    summary="Get user data",
    description="Searches for the authenticated user and returns its data",
    operation_id="get_profile",
    response_model=UserPublic,
)
def get_profile(user: CurrentUser) -> UserPublic:
    return user
