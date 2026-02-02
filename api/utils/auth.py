import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.database import get_db
from api.models.settings import AuthToken, UserSettings

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24

security = HTTPBearer()


@dataclass
class CurrentUser:
    username: str
    token_id: str
    scope: str
    token_type: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def generate_token() -> tuple[str, str]:
    """Generate an opaque token and its SHA-256 hash. Returns (raw_token, token_hash)."""
    raw = "sdl_" + secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    """SHA-256 hex digest of a raw token string."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_access_token(subject: str = "user") -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    token = credentials.credentials

    # New opaque token path
    if token.startswith("sdl_"):
        token_hash = hash_token(token)
        result = await db.execute(
            select(AuthToken).where(AuthToken.token_hash == token_hash)
        )
        auth_token = result.scalar_one_or_none()
        if auth_token is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # Update last_used_at
        await db.execute(
            update(AuthToken)
            .where(AuthToken.id == auth_token.id)
            .values(last_used_at=datetime.now(timezone.utc))
        )
        await db.commit()

        # Get username from settings
        username_row = await db.execute(
            select(UserSettings).where(UserSettings.key == "username")
        )
        username = username_row.scalar_one_or_none()
        uname = username.value if username else "admin"

        return CurrentUser(
            username=uname,
            token_id=auth_token.id,
            scope=auth_token.scope,
            token_type=auth_token.token_type,
        )

    # Legacy JWT fallback
    try:
        payload = decode_token(token)
        subject: str = payload.get("sub")
        if subject is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    result = await db.execute(select(UserSettings).where(UserSettings.key == "password_hash"))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No user configured")

    return CurrentUser(
        username="admin",
        token_id="legacy_jwt",
        scope="read_write",
        token_type="session",
    )
