from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database import get_db
from app.models import User, Session as SessionModel, PasswordResetToken
from app.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.auth.utils import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_password_reset_token,
    get_session_expiry,
    get_password_reset_expiry,
)
from app.auth.dependencies import get_current_user
from app.email.service import send_password_reset_email
from app.config import get_settings

settings = get_settings()
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=MessageResponse)
@limiter.limit("5/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user. Only @vysusgroup.com emails allowed."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists"
        )

    # Create new user
    new_user = User(
        email=user_data.email.lower(),
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )

    db.add(new_user)
    db.commit()

    return {"message": "Registration successful. You can now log in."}


@router.post("/login", response_model=UserResponse)
@limiter.limit("10/15minutes")
async def login(
    request: Request,
    response: Response,
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Log in and create a session."""
    # Find user
    user = db.query(User).filter(User.email == user_data.email.lower()).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Create session
    session_token = generate_session_token()
    session = SessionModel(
        user_id=user.id,
        session_token=session_token,
        expires_at=get_session_expiry(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:500],
    )

    db.add(session)
    db.commit()

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        max_age=settings.session_expire_days * 24 * 60 * 60,
    )

    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Log out and destroy the session."""
    session_token = request.cookies.get("session_token")

    if session_token:
        # Delete session from database
        db.query(SessionModel).filter(
            SessionModel.session_token == session_token
        ).delete()
        db.commit()

    # Clear cookie
    response.delete_cookie("session_token")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get the current authenticated user."""
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """Request a password reset email."""
    # Always return success to prevent email enumeration
    user = db.query(User).filter(User.email == data.email.lower()).first()

    if user and user.is_active:
        # Invalidate any existing tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).update({"used": True})

        # Create new token
        token = generate_password_reset_token()
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=get_password_reset_expiry(),
        )

        db.add(reset_token)
        db.commit()

        # Send email
        try:
            await send_password_reset_email(user.email, token)
        except Exception:
            # Log error but don't expose to user
            pass

    return {"message": "If an account exists with this email, you will receive a password reset link."}


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using a valid token."""
    # Find valid token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == data.token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update user password
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    user.hashed_password = hash_password(data.new_password)
    user.updated_at = datetime.utcnow()

    # Mark token as used
    reset_token.used = True

    # Invalidate all user sessions (force re-login)
    db.query(SessionModel).filter(SessionModel.user_id == user.id).delete()

    db.commit()

    return {"message": "Password reset successful. Please log in with your new password."}
