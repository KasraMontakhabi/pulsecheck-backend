from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import auth_backend, fastapi_users, UserManager, get_user_manager
from app.schemas.user import UserRead, UserCreate, UserUpdate

router = APIRouter()

# Include authentication routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)

# Include registration route
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Include user management routes
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserRead
