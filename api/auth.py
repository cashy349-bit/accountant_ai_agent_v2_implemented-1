import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from database.models import User


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def create_user(
    db: Session,
    company_id: str,
    email: str,
    role: str = "reviewer",
    api_key: str | None = None,
    api_key_expires_at: datetime | None = None,
) -> tuple[User, str]:
    key = api_key or generate_api_key()

    user = User(
        company_id=company_id,
        email=email,
        api_key_hash=hash_api_key(key),
        api_key_created_at=datetime.now(timezone.utc),
        api_key_expires_at=api_key_expires_at,
        api_key_revoked_at=None,
        role=role,
        active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, key


def get_current_user(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
        )

    user = db.scalar(
        select(User).where(
            User.api_key_hash == hash_api_key(x_api_key),
        )
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
        )

    now = datetime.now(timezone.utc)

    if user.api_key_revoked_at is not None:
        raise HTTPException(
            status_code=401,
            detail="API key has been revoked",
        )

    if user.api_key_expires_at is not None:
        expires_at = user.api_key_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(
                status_code=401,
                detail="API key has expired",
            )

    if not user.active:
        raise HTTPException(
            status_code=403,
            detail="User is inactive",
        )

    return user
