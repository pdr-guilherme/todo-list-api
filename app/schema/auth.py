from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(description="User name.", max_length=100)
    email: EmailStr = Field(
        description="User email. Will be used to log-in.", max_length=100
    )
    password: str = Field(
        description="Account password. Will be used to log-in.", min_length=8
    )


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="User ID.", json_schema_extra={"readOnly": True})
    name: str = Field(description="User name.")
    email: EmailStr = Field(description="User email.")


class TokenResponse(BaseModel):
    token: str = Field(
        description=(
            "Authentication token. Used to validate user authenticity via "
            "`Authorization: Bearer <token>` header in requests."
        ),
        json_schema_extra={"readOnly": True},
    )


class LoginData(BaseModel):
    email: EmailStr = Field(description="Account email.")
    password: str = Field(description="Account password.")
