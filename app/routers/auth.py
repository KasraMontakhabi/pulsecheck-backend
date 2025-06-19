from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import auth_backend, fastapi_users, UserManager, get_user_manager
from app.schemas.user import UserRead, UserCreate, UserUpdate

router = APIRouter()

# Include registration route
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

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


@router.post("/auth/login", response_model=LoginResponse)
async def login(
        login_data: LoginRequest,
        user_manager: UserManager = Depends(get_user_manager)
):
    user = await user_manager.get_by_email(login_data.username)

    if user is None:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Verify password
    valid_password = user_manager.password_helper.verify_and_update(
        login_data.password, user.hashed_password
    )

    if not valid_password[0] or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate token
    from app.deps import get_jwt_strategy
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )