"""
UPI SECURE PAY - Authentication Router
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from core.dependencies import get_current_user
from core.redis_client import get_redis
import uuid

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory user storage (in production, use database)
_users: dict = {}


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=201)
async def register(req: RegisterRequest):
    """Register a new user"""
    if req.email in _users:
        raise HTTPException(400, "Email already registered")
    if len(req.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    
    user_id = str(uuid.uuid4())
    # First user is admin
    role = "admin" if not _users else "user"
    
    _users[req.email] = {
        "id": user_id,
        "email": req.email,
        "name": req.name,
        "hashed_password": get_password_hash(req.password),
        "role": role,
    }
    
    return {"message": "Registered successfully", "user_id": user_id, "role": role}


@router.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    user = _users.get(form.username)
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    
    access = create_access_token(user["id"], user["role"])
    refresh = create_refresh_token(user["id"])
    
    # Store session in Redis
    redis = await get_redis()
    if redis:
        await redis.setex(f"session:{user['id']}", 3600, user["email"])
    
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "user_id": user["id"],
        "role": user["role"],
    }


@router.post("/refresh")
async def refresh_token(req: RefreshRequest):
    """Refresh access token"""
    payload = decode_token(req.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")
    
    user = next((u for u in _users.values() if u["id"] == payload["sub"]), None)
    if not user:
        raise HTTPException(401, "User not found")
    
    return {
        "access_token": create_access_token(user["id"], user["role"]),
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
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    user = next((u for u in _users.values() if u["id"] == current_user["user_id"]), None)
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "user_id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
    }
