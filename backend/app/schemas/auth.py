import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class RegisterRequest(LoginRequest):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-z][a-z0-9_]*$")

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        categories = sum(
            bool(re.search(pattern, password))
            for pattern in [r"[a-z]", r"[A-Z]", r"[0-9]", r"[^a-zA-Z0-9]"]
        )
        if len(password) < 12 or categories < 3:
            raise ValueError("Password requires >=12 characters and 3 character categories")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    csrf_token: str
