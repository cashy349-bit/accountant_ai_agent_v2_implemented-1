import hashlib
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import db_session
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
) -> tuple[User, str]:
    key = api_key or generate_api_key()

    user = User(
        company_id=company_id,
        email=email,
        api_key_hash=hash_api_key(key),
        role=role,
        active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user, key


def get_current_user(
    x_api_key: str | None = Header(default=None),
    db: Session | None = None,
) -> User:
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key",
        )

    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Authentication database dependency not configured",
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

    if not user.active:
        raise HTTPException(
            status_code=403,
            detail="User is inactive",
        )

    return user
