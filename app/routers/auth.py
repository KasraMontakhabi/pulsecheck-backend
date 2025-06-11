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


@router.post("/auth/jwt/login-json", response_model=LoginResponse)
async def login_json(
        login_data: LoginRequest,
        user_manager: UserManager = Depends(get_user_manager)
):
    user = await user_manager.authenticate(
        credentials={"email": login_data.username, "password": login_data.password}
    )

    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Generate token
    from app.deps import get_jwt_strategy
    strategy = get_jwt_strategy()
    token = await strategy.write_token(user)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.from_orm(user)
    )