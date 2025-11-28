import secrets
from datetime import datetime, timedelta
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_token() -> str:
    """Generate a secure random session token."""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure random password reset token."""
    return secrets.token_urlsafe(32)


def get_session_expiry() -> datetime:
    """Get the expiry datetime for a new session."""
    return datetime.utcnow() + timedelta(days=settings.session_expire_days)


def get_password_reset_expiry() -> datetime:
    """Get the expiry datetime for a password reset token."""
    return datetime.utcnow() + timedelta(hours=settings.password_reset_expire_hours)
