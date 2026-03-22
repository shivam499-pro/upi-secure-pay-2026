"""
UPI SECURE PAY - Authentication Router
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from core.dependencies import get_current_user
from core.redis_client import get_redis
import database
import uuid

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


def get_db():
    """Get database session"""
    if database.SessionLocal is None:
        raise HTTPException(503, "Database not initialized")
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_by_email(db, email: str):
    """Get user by email from database"""
    from sqlalchemy import text
    result = db.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
    row = result.fetchone()
    if row:
        return type('User', (), {
            'id': row[0],
            'email': row[1],
            'name': row[2],
            'hashed_password': row[3],
            'role': row[4]
        })()
    return None


def get_user_by_id(db, user_id: str):
    """Get user by ID from database"""
    from sqlalchemy import text
    result = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
    row = result.fetchone()
    if row:
        return type('User', (), {
            'id': row[0],
            'email': row[1],
            'name': row[2],
            'hashed_password': row[3],
            'role': row[4]
        })()
    return None


def create_user(db, email: str, password: str, name: str, role: str):
    """Create a new user in database"""
    from sqlalchemy import text
    user_id = str(uuid.uuid4())
    hashed = get_password_hash(password)
    db.execute(
        text("INSERT INTO users (id, email, name, hashed_password, role) VALUES (:id, :email, :name, :password, :role)"),
        {"id": user_id, "email": email, "name": name, "password": hashed, "role": role}
    )
    db.commit()
    return user_id


def count_users(db):
    """Count total users"""
    from sqlalchemy import text
    result = db.execute(text("SELECT COUNT(*) FROM users"))
    row = result.fetchone()
    return row[0] if row else 0


def init_users_table():
    pass


# Initialize users table on module load
try:
    init_users_table()
except:
    pass  # Will be initialized on startup


@router.post("/register", status_code=201)
async def register(req: RegisterRequest, db=Depends(get_db)):
    """Register a new user"""
    existing = get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(400, "Email already registered")
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    
    # First user is admin
    role = "admin" if count_users(db) == 0 else "user"
    
    user_id = create_user(db, req.email, req.password, req.name, role)
    
    return {"message": "Registered successfully", "user_id": user_id, "role": role}


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """Login and get access token"""
    user = get_user_by_email(db, form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    
    # Store session in Redis
    redis = await get_redis()
    if redis:
        await redis.setex(f"session:{user.id}", 3600, user.email)
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role,
    }


@router.post("/refresh")
async def refresh_token(req: RefreshRequest, db=Depends(get_db)):
    """Refresh access token"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    
    user = get_user_by_id(db, payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout and clear session"""
    redis = await get_redis()
    if redis:
        await redis.delete(f"session:{current_user['user_id']}")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Get current user info"""
    user = get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }
