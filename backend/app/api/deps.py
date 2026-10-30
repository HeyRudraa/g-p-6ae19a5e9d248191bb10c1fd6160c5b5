import re
import secrets
import string
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin.exceptions import FirebaseError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.firebase import get_firebase_app
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User

bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]


def username_from_email(email: str) -> str:
    root = re.sub(r"[^a-z0-9_]", "_", email.partition("@")[0].lower()).strip("_") or "learner"
    return f"{root[:21]}_{''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(5))}"


async def current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    settings = get_settings()
    if not settings.firebase_project_id:
        raise HTTPException(status_code=503, detail="Firebase Authentication is not configured on this API.")
    try:
        claims = firebase_auth.verify_id_token(
            credentials.credentials,
            app=get_firebase_app(),
            check_revoked=settings.firebase_check_revoked,
        )
    except (ValueError, FirebaseError) as exc:
        raise HTTPException(status_code=401, detail="Your sign-in has expired. Sign in again.") from exc
    if not claims.get("email_verified"):
        raise HTTPException(status_code=403, detail="Verify your email before using Orbit.")
    email = (claims.get("email") or "").strip().lower()
    uid = claims.get("uid")
    if not email or not uid:
        raise HTTPException(status_code=401, detail="The identity token is missing required profile claims.")
    user = await db.scalar(select(User).where(User.firebase_uid == uid))
    if user is None:
        user = User(
            firebase_uid=uid,
            email=email,
            username=username_from_email(email),
            display_name=(claims.get("name") or email.partition("@")[0])[:120],
            avatar_id="orbit",
            role=UserRole.STUDENT,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="This Orbit account has been disabled.")
    elif user.email != email:
        user.email = email
        await db.commit()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db():
        yield session
