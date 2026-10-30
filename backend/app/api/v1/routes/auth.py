from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.user import User
from app.schemas.auth import UserProfile, UserProfileUpdate

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def read_profile(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserProfile)
async def update_profile(payload: UserProfileUpdate, user: CurrentUser, db: DbSession) -> User:
    taken = await db.scalar(
        select(User.id).where(User.username == payload.username.lower(), User.id != user.id)
    )
    if taken:
        raise HTTPException(status_code=409, detail="That username is already in use.")
    user.username = payload.username.lower()
    user.display_name = payload.display_name
    user.avatar_id = payload.avatar_id
    user.onboarding_completed = payload.onboarding_completed
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="That username is already in use.") from exc
    await db.refresh(user)
    return user
