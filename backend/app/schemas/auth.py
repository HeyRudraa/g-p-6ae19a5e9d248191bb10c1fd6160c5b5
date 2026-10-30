from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import ORMModel


class UserProfile(ORMModel):
    id: UUID
    firebase_uid: str
    email: EmailStr
    username: str
    display_name: str
    avatar_id: str
    onboarding_completed: bool


class UserProfileUpdate(ORMModel):
    username: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9_]+$")
    display_name: str = Field(min_length=2, max_length=120)
    avatar_id: Literal["orbit", "comet", "sun", "moon", "leaf", "spark", "wave", "star"]
    onboarding_completed: bool = True

    @field_validator("username", "display_name")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()
