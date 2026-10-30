import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.assignment import Assignment, AssignmentQuestion, Submission
from app.models.classroom import Classroom, ClassroomMembership, ClassroomTeacherSubject
from app.models.enums import AssignmentType, MembershipRole
from app.models.user import User
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentRead,
    GradeCreate,
    QuestionRead,
    SubmissionRead,
    AssignmentUpdate,
)
from app.services.classroom_access import require_class_member, require_subject_teacher

router = APIRouter()
ALLOWED_UPLOAD_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def load_questions(db: DbSession, assignment_id: UUID) -> list[AssignmentQuestion]:
    return list(
        (
            await db.scalars(
                select(AssignmentQuestion)
                .where(AssignmentQuestion.assignment_id == assignment_id)
                .order_by(AssignmentQuestion.position)
            )
        ).all()
    )


async def assignment_for_user(assignment_id: UUID, user: User, db: DbSession) -> Assignment:
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    membership = await require_class_member(db, assignment.classroom_id, user)
    if membership.role == MembershipRole.TEACHER:
        await require_subject_teacher(db, assignment.classroom_id, user, assignment.subject)
    return assignment


async def assignment_response(
    assignment: Assignment, user: User, db: DbSession, *, include_teacher_score: bool = False
) -> AssignmentRead:
    questions = await load_questions(db, assignment.id)
    response = AssignmentRead(
        id=assignment.id,
        classroom_id=assignment.classroom_id,
        created_by=assignment.created_by,
        title=assignment.title,
        subject=assignment.subject,
        instructions=assignment.instructions,
        assignment_type=assignment.assignment_type,
        points=assignment.points,
        due_at=assignment.due_at,
        auto_grade=assignment.auto_grade,
        created_at=assignment.created_at,
        questions=[
            QuestionRead(id=q.id, position=q.position, prompt=q.prompt, choices=q.choices)
            for q in questions
        ],
    )
    membership = await db.scalar(
        select(ClassroomMembership).where(
            ClassroomMembership.classroom_id == assignment.classroom_id,
            ClassroomMembership.user_id == user.id,
        )
    )
    if membership and membership.role != MembershipRole.STUDENT:
        return response
    submission = await db.scalar(
        select(Submission).where(
            Submission.assignment_id == assignment.id,
            Submission.student_id == user.id,
        )
    )
    if submission:
        response.submission_status = "returned" if submission.returned_at else "submitted"
        if submission.returned_at:
            response.returned_score = submission.grade
            response.returned_feedback = submission.feedback
    return response


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(payload: AssignmentCreate, user: CurrentUser, db: DbSession):
    await require_subject_teacher(db, payload.classroom_id, user, payload.subject)
    if payload.assignment_type != AssignmentType.QUIZ and payload.questions:
        raise HTTPException(status_code=422, detail="Only quizzes can include multiple-choice questions.")
    assignment = Assignment(
        classroom_id=payload.classroom_id,
        created_by=user.id,
        title=payload.title.strip(),
        subject=payload.subject.strip(),
        instructions=payload.instructions.strip(),
        assignment_type=payload.assignment_type,
        points=payload.points,
        due_at=payload.due_at,
        auto_grade=payload.auto_grade,
    )
    db.add(assignment)
    await db.flush()
    for position, question in enumerate(payload.questions):
        db.add(
            AssignmentQuestion(
                assignment_id=assignment.id,
                position=position,
                prompt=question.prompt.strip(),
                choices=question.choices,
                answer_key=question.answer_key,
            )
        )
    await db.commit()
    await db.refresh(assignment)
    return await assignment_response(assignment, user, db, include_teacher_score=True)


@router.get("/classroom/{classroom_id}", response_model=list[AssignmentRead])
async def list_assignments(classroom_id: UUID, user: CurrentUser, db: DbSession):
    membership = await require_class_member(db, classroom_id, user)
    allowed_subjects = None
    if membership.role == MembershipRole.TEACHER:
        allowed_subjects = [subject.lower() for subject in (await db.scalars(
            select(ClassroomTeacherSubject.subject).where(
                ClassroomTeacherSubject.classroom_id == classroom_id,
                ClassroomTeacherSubject.user_id == user.id,
            )
        )).all()]
    assignments = list((
        await db.scalars(
            select(Assignment)
            .where(Assignment.classroom_id == classroom_id)
            .order_by(Assignment.due_at)
        )
    ).all())
    if allowed_subjects is not None:
        assignments = [assignment for assignment in assignments if assignment.subject.lower() in allowed_subjects]
    return [await assignment_response(a, user, db) for a in assignments]


@router.get("/{assignment_id}", response_model=AssignmentRead)
async def read_assignment(assignment_id: UUID, user: CurrentUser, db: DbSession):
    assignment = await assignment_for_user(assignment_id, user, db)
    return await assignment_response(assignment, user, db)


@router.patch("/{assignment_id}", response_model=AssignmentRead)
async def update_assignment(assignment_id: UUID, payload: AssignmentUpdate, user: CurrentUser, db: DbSession):
    assignment = await assignment_for_user(assignment_id, user, db)
    await require_subject_teacher(db, assignment.classroom_id, user, assignment.subject)
    await require_subject_teacher(db, assignment.classroom_id, user, payload.subject)
    assignment.title = payload.title.strip()
    assignment.subject = payload.subject.strip()
    assignment.instructions = payload.instructions.strip()
    assignment.points = payload.points
    assignment.due_at = payload.due_at
    await db.commit()
    await db.refresh(assignment)
    return await assignment_response(assignment, user, db, include_teacher_score=True)


@router.post("/{assignment_id}/submissions", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: UUID,
    user: CurrentUser,
    db: DbSession,
    text_response: Annotated[str, Form()] = "",
    answers_json: Annotated[str, Form()] = "{}",
    file: Annotated[UploadFile | None, File()] = None,
):
    assignment = await assignment_for_user(assignment_id, user, db)
    membership = await require_class_member(db, assignment.classroom_id, user)
    if membership.role != MembershipRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only a learner in this class can submit work.")
    existing = await db.scalar(
        select(Submission).where(Submission.assignment_id == assignment.id, Submission.student_id == user.id)
    )
    if existing:
        raise HTTPException(status_code=409, detail="This assignment has already been submitted.")
    try:
        answers = json.loads(answers_json or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Quiz answers must be valid JSON.") from exc
    if not isinstance(answers, dict):
        raise HTTPException(status_code=422, detail="Quiz answers must be an object.")
    questions = await load_questions(db, assignment.id)
    suggested = None
    if questions:
        valid_ids = {str(q.id) for q in questions}
        if set(answers) != valid_ids:
            raise HTTPException(status_code=422, detail="Answer every quiz question before submitting.")
        for question in questions:
            if answers[str(question.id)] not in [chr(ord("A") + i) for i in range(len(question.choices))]:
                raise HTTPException(status_code=422, detail="A quiz answer does not match an available choice.")
        if assignment.auto_grade:
            correct = sum(answers[str(q.id)] == q.answer_key for q in questions)
            suggested = round((correct / len(questions)) * assignment.points * 2) / 2
        text_response = json.dumps(answers)
    if not text_response.strip() and not file and not questions:
        raise HTTPException(status_code=422, detail="Add a response or attach a file before submitting.")

    file_key = None
    file_name = None
    if file and file.filename:
        if file.content_type not in ALLOWED_UPLOAD_TYPES:
            raise HTTPException(status_code=415, detail="This file type is not supported.")
        max_bytes = get_settings().max_upload_mb * 1024 * 1024
        content = await file.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise HTTPException(status_code=413, detail=f"Files must be smaller than {get_settings().max_upload_mb} MB.")
        file_name = Path(file.filename).name[:255]
        file_key = f"{uuid.uuid4().hex}{Path(file_name).suffix.lower()[:10]}"
        upload_root = Path(get_settings().upload_dir).resolve()
        upload_root.mkdir(parents=True, exist_ok=True)
        (upload_root / file_key).write_bytes(content)

    submission = Submission(
        assignment_id=assignment.id,
        student_id=user.id,
        text_response=text_response.strip(),
        file_key=file_key,
        file_name=file_name,
        suggested_score=suggested,
    )
    db.add(submission)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if file_key:
            (Path(get_settings().upload_dir).resolve() / file_key).unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="This assignment has already been submitted.") from exc
    await db.refresh(submission)
    return submission


@router.get("/{assignment_id}/submission", response_model=SubmissionRead)
async def read_my_submission(assignment_id: UUID, user: CurrentUser, db: DbSession):
    assignment = await assignment_for_user(assignment_id, user, db)
    submission = await db.scalar(
        select(Submission).where(
            Submission.assignment_id == assignment.id,
            Submission.student_id == user.id,
        )
    )
    if not submission:
        raise HTTPException(status_code=404, detail="You have not submitted this assignment yet.")
    if not submission.returned_at:
        submission.suggested_score = None
    return submission


@router.get("/{assignment_id}/submissions", response_model=list[SubmissionRead])
async def list_submissions(assignment_id: UUID, user: CurrentUser, db: DbSession):
    assignment = await assignment_for_user(assignment_id, user, db)
    await require_subject_teacher(db, assignment.classroom_id, user, assignment.subject)
    return list(
        (
            await db.scalars(
                select(Submission)
                .where(Submission.assignment_id == assignment_id)
                .order_by(Submission.submitted_at)
            )
        ).all()
    )


@router.post("/submissions/{submission_id}/grade", response_model=SubmissionRead)
async def grade_submission(submission_id: UUID, payload: GradeCreate, user: CurrentUser, db: DbSession):
    submission = await db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    assignment = await db.get(Assignment, submission.assignment_id)
    await require_subject_teacher(db, assignment.classroom_id, user, assignment.subject)
    if payload.grade > assignment.points:
        raise HTTPException(status_code=422, detail="The grade cannot exceed the assignment points.")
    submission.grade = payload.grade
    submission.feedback = payload.feedback.strip()
    submission.graded_by = user.id
    submission.returned_at = datetime.now(timezone.utc) if payload.return_to_student else None
    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/submissions/{submission_id}/file")
async def download_submission_file(submission_id: UUID, user: CurrentUser, db: DbSession):
    submission = await db.get(Submission, submission_id)
    if not submission or not submission.file_key:
        raise HTTPException(status_code=404, detail="Submission file not found.")
    assignment = await db.get(Assignment, submission.assignment_id)
    await require_class_member(db, assignment.classroom_id, user)
    if user.id != submission.student_id:
        await require_subject_teacher(db, assignment.classroom_id, user, assignment.subject)
    root = Path(get_settings().upload_dir).resolve()
    target = (root / submission.file_key).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Submission file is no longer available.")
    return FileResponse(target, filename=submission.file_name or "submission", content_disposition_type="attachment")
