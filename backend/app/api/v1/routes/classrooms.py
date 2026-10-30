import secrets
import string
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models.classroom import Announcement, Classroom, ClassroomMembership, ClassroomResource, ClassroomTeacherSubject
from app.models.enums import MembershipRole, UserRole
from app.models.user import User
from app.schemas.classroom import (
    AnnouncementCreate,
    AnnouncementRead,
    ClassroomCreate,
    ClassroomSummary,
    JoinClass,
    ResourceCreate,
    ResourceRead,
    AssignTeacher,
    TransferOwnership,
    TeacherAssignmentRead,
    ClassMemberRead,
)
from app.services.classroom_access import membership_for, require_class_admin, require_class_member

router = APIRouter()


def new_code() -> str:
    alphabet = string.ascii_uppercase + "23456789"
    return "".join(secrets.choice(alphabet) for _ in range(7))


@router.get("", response_model=list[ClassroomSummary])
async def list_classrooms(user: CurrentUser, db: DbSession) -> list[ClassroomSummary]:
    rows = await db.execute(
        select(Classroom, ClassroomMembership.role)
        .join(ClassroomMembership, ClassroomMembership.classroom_id == Classroom.id)
        .where(ClassroomMembership.user_id == user.id)
        .order_by(Classroom.created_at.desc())
    )
    result = []
    for classroom, role in rows:
        count = await db.scalar(
            select(func.count()).select_from(ClassroomMembership).where(
                ClassroomMembership.classroom_id == classroom.id,
                ClassroomMembership.role == MembershipRole.STUDENT,
            )
        )
        result.append(
            ClassroomSummary(
                **{k: getattr(classroom, k) for k in ("id", "name", "course_code", "description", "created_by", "created_at")},
                join_code=classroom.join_code if role == MembershipRole.CLASS_ADMIN or user.role == UserRole.ADMIN else None,
                member_role=role.value,
                student_count=count or 0,
            )
        )
    return result


@router.post("", response_model=ClassroomSummary, status_code=status.HTTP_201_CREATED)
async def create_classroom(payload: ClassroomCreate, user: CurrentUser, db: DbSession) -> ClassroomSummary:
    for _ in range(5):
        code = new_code()
        if not await db.scalar(select(Classroom.id).where(Classroom.join_code == code)):
            break
    classroom = Classroom(**payload.model_dump(), join_code=code, created_by=user.id)
    db.add(classroom)
    await db.flush()
    db.add(ClassroomMembership(classroom_id=classroom.id, user_id=user.id, role=MembershipRole.CLASS_ADMIN))
    await db.commit()
    await db.refresh(classroom)
    return ClassroomSummary(
        id=classroom.id,
        name=classroom.name,
        course_code=classroom.course_code,
        description=classroom.description,
        join_code=classroom.join_code,
        created_by=classroom.created_by,
        member_role=MembershipRole.CLASS_ADMIN.value,
        student_count=0,
        created_at=classroom.created_at,
    )


@router.post("/join", response_model=ClassroomSummary)
async def join_classroom(payload: JoinClass, user: CurrentUser, db: DbSession) -> ClassroomSummary:
    classroom = await db.scalar(
        select(Classroom).where(Classroom.join_code == payload.join_code.strip().upper())
    )
    if classroom is None:
        raise HTTPException(status_code=404, detail="We could not find a class with that code.")
    membership = await db.scalar(
        select(ClassroomMembership).where(
            ClassroomMembership.classroom_id == classroom.id,
            ClassroomMembership.user_id == user.id,
        )
    )
    if membership is None:
        db.add(ClassroomMembership(classroom_id=classroom.id, user_id=user.id, role=MembershipRole.STUDENT))
        await db.commit()
        member_role = MembershipRole.STUDENT
    else:
        member_role = membership.role
    count = await db.scalar(
        select(func.count()).select_from(ClassroomMembership).where(
            ClassroomMembership.classroom_id == classroom.id,
            ClassroomMembership.role == MembershipRole.STUDENT,
        )
    )
    return ClassroomSummary(
        id=classroom.id,
        name=classroom.name,
        course_code=classroom.course_code,
        description=classroom.description,
        join_code=None,
        created_by=classroom.created_by,
        member_role=member_role.value,
        student_count=count or 0,
        created_at=classroom.created_at,
    )


@router.get("/{classroom_id}", response_model=ClassroomSummary)
async def read_classroom(classroom_id: UUID, user: CurrentUser, db: DbSession) -> ClassroomSummary:
    membership = await require_class_member(db, classroom_id, user)
    classroom = await db.get(Classroom, classroom_id)
    count = await db.scalar(
        select(func.count()).select_from(ClassroomMembership).where(
            ClassroomMembership.classroom_id == classroom_id,
            ClassroomMembership.role == MembershipRole.STUDENT,
        )
    )
    return ClassroomSummary(
        id=classroom.id,
        name=classroom.name,
        course_code=classroom.course_code,
        description=classroom.description,
        join_code=classroom.join_code if membership.role == MembershipRole.CLASS_ADMIN or user.role == UserRole.ADMIN else None,
        created_by=classroom.created_by,
        member_role=membership.role.value,
        student_count=count or 0,
        created_at=classroom.created_at,
    )


@router.get("/{classroom_id}/members", response_model=list[ClassMemberRead])
async def classroom_members(classroom_id: UUID, user: CurrentUser, db: DbSession):
    await require_class_member(db, classroom_id, user)
    rows = await db.execute(
        select(User, ClassroomMembership.role)
        .join(ClassroomMembership, ClassroomMembership.user_id == User.id)
        .where(ClassroomMembership.classroom_id == classroom_id)
        .order_by(ClassroomMembership.role, User.display_name)
    )
    result = []
    for member, role in rows:
        subjects = list((await db.scalars(
            select(ClassroomTeacherSubject.subject).where(
                ClassroomTeacherSubject.classroom_id == classroom_id,
                ClassroomTeacherSubject.user_id == member.id,
            )
        )).all())
        result.append(ClassMemberRead(
            id=member.id, username=member.username,
            display_name=member.display_name, avatar_id=member.avatar_id,
            membership_role=role.value, subjects=subjects,
        ))
    return result


@router.get("/{classroom_id}/teachers", response_model=list[TeacherAssignmentRead])
async def list_class_teachers(classroom_id: UUID, user: CurrentUser, db: DbSession):
    await require_class_admin(db, classroom_id, user)
    rows = await db.execute(
        select(User, ClassroomTeacherSubject.subject)
        .join(ClassroomTeacherSubject, ClassroomTeacherSubject.user_id == User.id)
        .where(ClassroomTeacherSubject.classroom_id == classroom_id)
        .order_by(User.display_name, ClassroomTeacherSubject.subject)
    )
    return [TeacherAssignmentRead(user_id=teacher.id, email=teacher.email, display_name=teacher.display_name, subject=subject)
            for teacher, subject in rows]


@router.post("/{classroom_id}/teachers", response_model=TeacherAssignmentRead, status_code=201)
async def assign_teacher(classroom_id: UUID, payload: AssignTeacher, user: CurrentUser, db: DbSession):
    await require_class_admin(db, classroom_id, user)
    teacher = await db.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if teacher is None:
        raise HTTPException(status_code=404, detail="That user must create an Orbit account before being assigned.")
    membership = await db.scalar(select(ClassroomMembership).where(
        ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.user_id == teacher.id
    ))
    if membership is None:
        membership = ClassroomMembership(classroom_id=classroom_id, user_id=teacher.id, role=MembershipRole.TEACHER)
        db.add(membership)
    elif membership.role == MembershipRole.CLASS_ADMIN:
        raise HTTPException(status_code=409, detail="The class admin already has full teacher access.")
    else:
        membership.role = MembershipRole.TEACHER
    subject = payload.subject.strip()
    existing = await db.scalar(select(ClassroomTeacherSubject).where(
        ClassroomTeacherSubject.classroom_id == classroom_id,
        ClassroomTeacherSubject.user_id == teacher.id,
        func.lower(ClassroomTeacherSubject.subject) == subject.lower(),
    ))
    if existing is None:
        db.add(ClassroomTeacherSubject(classroom_id=classroom_id, user_id=teacher.id, subject=subject, assigned_by=user.id))
    await db.commit()
    return TeacherAssignmentRead(user_id=teacher.id, email=teacher.email, display_name=teacher.display_name, subject=subject)


@router.delete("/{classroom_id}/teachers/{teacher_id}", status_code=204)
async def remove_teacher_subject(classroom_id: UUID, teacher_id: UUID, user: CurrentUser, db: DbSession, subject: str = Query(min_length=2, max_length=80)):
    await require_class_admin(db, classroom_id, user)
    assignment = await db.scalar(select(ClassroomTeacherSubject).where(
        ClassroomTeacherSubject.classroom_id == classroom_id,
        ClassroomTeacherSubject.user_id == teacher_id,
        func.lower(ClassroomTeacherSubject.subject) == subject.strip().lower(),
    ))
    if assignment is None:
        raise HTTPException(status_code=404, detail="Teacher subject assignment not found.")
    await db.delete(assignment)
    remaining = await db.scalar(select(ClassroomTeacherSubject.id).where(
        ClassroomTeacherSubject.classroom_id == classroom_id,
        ClassroomTeacherSubject.user_id == teacher_id,
    ).limit(1))
    if remaining is None:
        membership = await membership_for(db, classroom_id, await db.get(User, teacher_id))
        if membership and membership.role == MembershipRole.TEACHER:
            membership.role = MembershipRole.STUDENT
    await db.commit()
    return Response(status_code=204)


@router.post("/{classroom_id}/ownership", response_model=ClassroomSummary)
async def transfer_ownership(classroom_id: UUID, payload: TransferOwnership, user: CurrentUser, db: DbSession):
    await require_class_admin(db, classroom_id, user)
    next_admin = await db.scalar(select(ClassroomMembership).where(
        ClassroomMembership.classroom_id == classroom_id,
        ClassroomMembership.user_id == payload.new_owner_id,
    ))
    if next_admin is None:
        raise HTTPException(status_code=404, detail="The new owner must already be a member of this class.")
    classroom = await db.get(Classroom, classroom_id)
    current_admin = await membership_for(db, classroom_id, user)
    if next_admin.user_id != current_admin.user_id:
        current_admin.role = MembershipRole.TEACHER
        next_admin.role = MembershipRole.CLASS_ADMIN
        classroom.created_by = next_admin.user_id
        await db.commit()
        await db.refresh(classroom)
    count = await db.scalar(select(func.count()).select_from(ClassroomMembership).where(
        ClassroomMembership.classroom_id == classroom_id, ClassroomMembership.role == MembershipRole.STUDENT
    ))
    return ClassroomSummary(id=classroom.id, name=classroom.name, course_code=classroom.course_code,
        description=classroom.description, join_code=classroom.join_code, created_by=classroom.created_by,
        member_role=MembershipRole.CLASS_ADMIN.value, student_count=count or 0, created_at=classroom.created_at)


@router.post("/{classroom_id}/resources", response_model=ResourceRead, status_code=201)
async def create_resource(classroom_id: UUID, payload: ResourceCreate, user: CurrentUser, db: DbSession):
    await require_class_member(db, classroom_id, user, teacher_only=True)
    resource = ClassroomResource(
        classroom_id=classroom_id, title=payload.title, url=str(payload.url), added_by=user.id
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.get("/{classroom_id}/resources", response_model=list[ResourceRead])
async def list_resources(classroom_id: UUID, user: CurrentUser, db: DbSession):
    await require_class_member(db, classroom_id, user)
    return list((await db.scalars(select(ClassroomResource).where(ClassroomResource.classroom_id == classroom_id).order_by(ClassroomResource.created_at.desc()))).all())


@router.post("/{classroom_id}/announcements", response_model=AnnouncementRead, status_code=201)
async def create_announcement(classroom_id: UUID, payload: AnnouncementCreate, user: CurrentUser, db: DbSession):
    await require_class_member(db, classroom_id, user, teacher_only=True)
    item = Announcement(classroom_id=classroom_id, author_id=user.id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{classroom_id}/announcements", response_model=list[AnnouncementRead])
async def list_announcements(classroom_id: UUID, user: CurrentUser, db: DbSession):
    await require_class_member(db, classroom_id, user)
    return list((await db.scalars(select(Announcement).where(Announcement.classroom_id == classroom_id).order_by(Announcement.created_at.desc()))).all())
