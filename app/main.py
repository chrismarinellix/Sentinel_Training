import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, SessionLocal
from app.auth.router import router as auth_router
from app.auth.dependencies import get_current_user_from_cookie

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Vysus Training Platform",
    description="Grid Connection Engineering Training",
    version="1.0.0"
)

app.state.limiter = limiter


# Rate limit error handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTMLResponse(
        content="<h1>Too many requests</h1><p>Please try again later.</p>",
        status_code=429
    )


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to protect static files behind authentication."""

    PUBLIC_PATHS = [
        "/login",
        "/register",
        "/reset-password",
        "/forgot-password",
        "/api/auth/",
        "/api/health",
        "/favicon.ico",
    ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Allow public paths
        if any(path.startswith(p) for p in self.PUBLIC_PATHS):
            return await call_next(request)

        # Check authentication for all other paths
        session_token = request.cookies.get("session_token")

        if not session_token:
            return RedirectResponse(url="/login", status_code=302)

        # Verify session in database
        db = SessionLocal()
        try:
            user = get_current_user_from_cookie(session_token, db)
            if not user:
                response = RedirectResponse(url="/login", status_code=302)
                response.delete_cookie("session_token")
                return response
            # Add user to request state for use in endpoints
            request.state.user = user
        except Exception:
            return RedirectResponse(url="/login", status_code=302)
        finally:
            db.close()

        return await call_next(request)


# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Include auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "vysus-training-platform"}


# Public pages
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "login.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Login page not found")


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "register.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Register page not found")


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "reset-password.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Reset password page not found")


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    file_path = os.path.join(os.path.dirname(__file__), "..", "static", "forgot-password.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Forgot password page not found")


# Protected static files - serve after auth middleware checks
@app.get("/")
async def root():
    return RedirectResponse(url="/training-plan.html")


@app.get("/{path:path}")
async def serve_static(path: str, request: Request):
    """Serve protected static files."""
    # Security: prevent directory traversal
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")

    file_path = os.path.join(os.path.dirname(__file__), "..", "static", path)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)

    raise HTTPException(status_code=404, detail="File not found")
