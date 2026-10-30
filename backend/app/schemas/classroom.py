from datetime import datetime
from uuid import UUID

from pydantic import Field, HttpUrl

from app.schemas.common import ORMModel


class ClassroomCreate(ORMModel):
    name: str = Field(min_length=2, max_length=100)
    course_code: str = Field(default="", max_length=24)
    description: str = Field(default="", max_length=5000)


class ClassroomSummary(ORMModel):
    id: UUID
    name: str
    course_code: str
    description: str
    join_code: str | None = None
    created_by: UUID
    member_role: str | None = None
    student_count: int = 0
    created_at: datetime


class JoinClass(ORMModel):
    join_code: str = Field(min_length=4, max_length=12)


class ResourceCreate(ORMModel):
    title: str = Field(min_length=2, max_length=120)
    url: HttpUrl


class ResourceRead(ORMModel):
    id: UUID
    classroom_id: UUID
    title: str
    url: str
    created_at: datetime


class AnnouncementCreate(ORMModel):
    title: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=1, max_length=10000)


class AnnouncementRead(ORMModel):
    id: UUID
    classroom_id: UUID
    title: str
    body: str
    author_id: UUID
    created_at: datetime


class AssignTeacher(ORMModel):
    email: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=2, max_length=80)


class TransferOwnership(ORMModel):
    new_owner_id: UUID


class TeacherAssignmentRead(ORMModel):
    user_id: UUID
    email: str
    display_name: str
    subject: str


class ClassMemberRead(ORMModel):
    id: UUID
    username: str
    display_name: str
    avatar_id: str
    membership_role: str
    subjects: list[str] = Field(default_factory=list)
