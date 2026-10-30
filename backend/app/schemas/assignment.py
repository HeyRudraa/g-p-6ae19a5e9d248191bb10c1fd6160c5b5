from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import AssignmentType
from app.schemas.common import ORMModel


class QuestionCreate(ORMModel):
    prompt: str = Field(min_length=1, max_length=3000)
    choices: list[str] = Field(min_length=2, max_length=6)
    answer_key: str = Field(pattern=r"^[A-F]$")

    @model_validator(mode="after")
    def validate_answer_index(self):
        index = ord(self.answer_key) - ord("A")
        if index >= len(self.choices):
            raise ValueError("The answer key must point to an available choice.")
        return self


class AssignmentCreate(ORMModel):
    classroom_id: UUID
    subject: str = Field(default="General", min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=140)
    instructions: str = Field(default="", max_length=12000)
    assignment_type: AssignmentType
    points: float = Field(default=100, gt=0, le=10000)
    due_at: datetime
    auto_grade: bool = False
    questions: list[QuestionCreate] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def objective_quiz_needs_questions(self):
        if self.auto_grade and (self.assignment_type != AssignmentType.QUIZ or not self.questions):
            raise ValueError("Suggested quiz grading requires a quiz with objective questions.")
        return self


class AssignmentUpdate(ORMModel):
    subject: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=140)
    instructions: str = Field(default="", max_length=12000)
    points: float = Field(gt=0, le=10000)
    due_at: datetime


class QuestionRead(ORMModel):
    id: UUID
    position: int
    prompt: str
    choices: list[str]


class AssignmentRead(ORMModel):
    id: UUID
    classroom_id: UUID
    created_by: UUID
    title: str
    subject: str
    instructions: str
    assignment_type: AssignmentType
    points: float
    due_at: datetime
    auto_grade: bool
    created_at: datetime
    questions: list[QuestionRead] = Field(default_factory=list)
    submission_status: str | None = None
    returned_score: float | None = None
    returned_feedback: str | None = None


class SubmissionCreate(ORMModel):
    text_response: str = Field(default="", max_length=50000)
    answers: dict[UUID, str] = Field(default_factory=dict)


class GradeCreate(ORMModel):
    grade: float = Field(ge=0)
    feedback: str = Field(default="", max_length=12000)
    return_to_student: bool = True


class SubmissionRead(ORMModel):
    id: UUID
    assignment_id: UUID
    student_id: UUID
    text_response: str
    file_name: str | None
    suggested_score: float | None
    grade: float | None
    feedback: str
    submitted_at: datetime
    returned_at: datetime | None
