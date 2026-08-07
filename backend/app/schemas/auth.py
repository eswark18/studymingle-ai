import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)
    education_track: str | None = Field(default=None, max_length=32)
    grade_or_year: str | None = Field(default=None, max_length=32)
    turnstile_token: str | None = Field(default=None, max_length=2048)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(
            character.isdigit() for character in value
        ):
            raise ValueError("Password must contain at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    turnstile_token: str | None = Field(default=None, max_length=2048)


class DeleteAccountRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None
    education_track: str | None
    grade_or_year: str | None
    email_verified_at: datetime | None
    created_at: datetime
