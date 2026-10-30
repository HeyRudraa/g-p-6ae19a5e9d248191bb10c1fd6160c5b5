from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class GradeRow(BaseModel):
    submission_id: UUID
    assignment_id: UUID
    assignment_title: str
    classroom_id: UUID
    classroom_name: str
    student_id: UUID
    student_name: str | None = None
    points: float
    grade: float | None
    suggested_score: float | None = None
    feedback: str
    submitted_at: datetime
    returned_at: datetime | None
