from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.classroom import ClassroomMembership, ClassroomTeacherSubject
from app.models.enums import MembershipRole, UserRole
from app.models.user import User


async def membership_for(db: AsyncSession, classroom_id: UUID, user: User) -> ClassroomMembership | None:
    return await db.scalar(
        select(ClassroomMembership).where(
            ClassroomMembership.classroom_id == classroom_id,
            ClassroomMembership.user_id == user.id,
        )
    )


async def require_class_member(
    db: AsyncSession, classroom_id: UUID, user: User, *, teacher_only: bool = False
) -> ClassroomMembership:
    membership = await membership_for(db, classroom_id, user)
    if membership is None:
        raise HTTPException(status_code=404, detail="Class not found.")
    if teacher_only and membership.role not in (MembershipRole.TEACHER, MembershipRole.CLASS_ADMIN) and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="A teacher assigned to this class is required.")
    return membership


async def require_class_admin(db: AsyncSession, classroom_id: UUID, user: User) -> ClassroomMembership:
    membership = await membership_for(db, classroom_id, user)
    if membership is None:
        raise HTTPException(status_code=404, detail="Class not found.")
    if membership.role != MembershipRole.CLASS_ADMIN and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only this class's admin can manage its teachers or ownership.")
    return membership


async def require_subject_teacher(db: AsyncSession, classroom_id: UUID, user: User, subject: str) -> ClassroomMembership:
    membership = await require_class_member(db, classroom_id, user)
    if membership.role == MembershipRole.CLASS_ADMIN or user.role == UserRole.ADMIN:
        return membership
    assigned = await db.scalar(
        select(ClassroomTeacherSubject.id).where(
            ClassroomTeacherSubject.classroom_id == classroom_id,
            ClassroomTeacherSubject.user_id == user.id,
            func.lower(ClassroomTeacherSubject.subject) == subject.strip().lower(),
        )
    )
    if membership.role != MembershipRole.TEACHER or assigned is None:
        raise HTTPException(status_code=403, detail="You are not assigned to teach this subject in this class.")
    return membership
