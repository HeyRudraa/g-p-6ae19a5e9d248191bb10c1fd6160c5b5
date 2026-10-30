from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.assignment import Assignment, Submission
from app.models.classroom import Classroom, ClassroomMembership, ClassroomTeacherSubject
from app.models.enums import MembershipRole, UserRole
from app.models.user import User
from app.schemas.grades import GradeRow
from app.services.classroom_access import require_class_member

router = APIRouter()


@router.get("/me", response_model=list[GradeRow])
async def my_returned_grades(user: CurrentUser, db: DbSession):
    rows = await db.execute(
        select(Submission, Assignment, Classroom)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(Classroom, Assignment.classroom_id == Classroom.id)
        .where(Submission.student_id == user.id, Submission.returned_at.is_not(None))
        .order_by(Submission.returned_at.desc())
    )
    return [
        GradeRow(
            submission_id=sub.id,
            assignment_id=assignment.id,
            assignment_title=assignment.title,
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            student_id=user.id,
            student_name=None,
            points=assignment.points,
            grade=sub.grade,
            feedback=sub.feedback,
            submitted_at=sub.submitted_at,
            returned_at=sub.returned_at,
        )
        for sub, assignment, classroom in rows
    ]


@router.get("/classroom/{classroom_id}", response_model=list[GradeRow])
async def classroom_gradebook(classroom_id: UUID, user: CurrentUser, db: DbSession):
    membership = await require_class_member(db, classroom_id, user, teacher_only=True)
    allowed_subjects = None
    if membership.role == MembershipRole.TEACHER and user.role != UserRole.ADMIN:
        allowed_subjects = [value.lower() for value in (await db.scalars(select(ClassroomTeacherSubject.subject).where(
            ClassroomTeacherSubject.classroom_id == classroom_id,
            ClassroomTeacherSubject.user_id == user.id,
        ))).all()]
        if not allowed_subjects:
            return []
    query = (
        select(Submission, Assignment, Classroom, User)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .join(Classroom, Assignment.classroom_id == Classroom.id)
        .join(User, Submission.student_id == User.id)
        .where(Assignment.classroom_id == classroom_id)
    )
    if allowed_subjects is not None:
        query = query.where(func.lower(Assignment.subject).in_(allowed_subjects))
    rows = await db.execute(query.order_by(User.display_name, Assignment.title))
    return [
        GradeRow(
            submission_id=sub.id,
            assignment_id=assignment.id,
            assignment_title=assignment.title,
            classroom_id=classroom.id,
            classroom_name=classroom.name,
            student_id=student.id,
            student_name=student.display_name,
            points=assignment.points,
            grade=sub.grade,
            suggested_score=sub.suggested_score,
            feedback=sub.feedback,
            submitted_at=sub.submitted_at,
            returned_at=sub.returned_at,
        )
        for sub, assignment, classroom, student in rows
    ]
