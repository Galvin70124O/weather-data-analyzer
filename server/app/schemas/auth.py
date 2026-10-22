"""Request and response bodies for accounts. Validation lives here, not in the routes."""
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES

# Letters, digits, dot, dash, underscore. No "@", so a username can never look like an email.
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
MIN_PASSWORD_LENGTH = 8


def check_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    return value


class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError("Username must be 3-32 characters: letters, numbers, dot, dash or underscore.")
        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return value.strip().lower()

    _password = field_validator("password")(check_password)


class LoginIn(BaseModel):
    identifier: str = Field(min_length=1, max_length=254, description="Username or email")
    password: str = Field(min_length=1, max_length=200)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str

    _new_password = field_validator("new_password")(check_password)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    units: Literal["metric", "imperial"]
    created_at: datetime


class PreferencesIn(BaseModel):
    units: Literal["metric", "imperial"]
