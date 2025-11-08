"""
Mobile Authentication Router.

Endpoints:
- POST /register - Register new user account
- POST /login - Login with credentials
- POST /refresh - Refresh access token
- POST /logout - Logout and invalidate tokens
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import jwt
import hashlib
from passlib.context import CryptContext

from ...database import get_db
from ...config import get_settings
from ...models.user import User, UserRole, AccountStatus
from ...models.mobile import MobileDevice, RefreshToken
from .schemas import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    AuthResponse,
    TokenResponse,
    UserMobileResponse
)
from .responses import create_success_response, create_error_response, ErrorCode

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

auth_router = APIRouter()


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int) -> tuple[str, int]:
    """
    Create JWT access token.

    Args:
        user_id: User ID

    Returns:
        Tuple of (token, expires_in_seconds)
    """
    expires_in = 900  # 15 minutes
    expire = datetime.utcnow() + timedelta(seconds=expires_in)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def create_refresh_token_pair(user_id: int, device_id: str, db: Session) -> str:
    """
    Create refresh token and store in database.

    Args:
        user_id: User ID
        device_id: Device ID
        db: Database session

    Returns:
        Refresh token string
    """
    expires_in_days = 30
    expire = datetime.utcnow() + timedelta(days=expires_in_days)

    payload = {
        "sub": str(user_id),
        "device_id": device_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # Hash token for storage
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Store in database
    refresh_token = RefreshToken(
        user_id=user_id,
        device_id=device_id,
        token_hash=token_hash,
        expires_at=expire
    )
    db.add(refresh_token)
    db.commit()

    return token


def register_or_update_device(user_id: int, device_info: dict, db: Session) -> MobileDevice:
    """
    Register or update mobile device.

    Args:
        user_id: User ID
        device_info: Device information dictionary
        db: Database session

    Returns:
        MobileDevice object
    """
    # Check if device already exists
    device = db.query(MobileDevice).filter(
        MobileDevice.device_id == device_info["device_id"]
    ).first()

    if device:
        # Update existing device
        device.user_id = user_id
        device.platform = device_info["platform"]
        device.push_token = device_info.get("push_token")
        device.app_version = device_info.get("app_version")
        device.os_version = device_info.get("os_version")
        device.is_active = True
        device.last_active = datetime.utcnow()
        device.updated_at = datetime.utcnow()
    else:
        # Create new device
        device = MobileDevice(
            user_id=user_id,
            device_id=device_info["device_id"],
            platform=device_info["platform"],
            push_token=device_info.get("push_token"),
            app_version=device_info.get("app_version"),
            os_version=device_info.get("os_version"),
            is_active=True,
            last_active=datetime.utcnow()
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return device


@auth_router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register new user account.

    Creates user, registers device, and returns tokens.
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=create_error_response(
                code=ErrorCode.ALREADY_EXISTS,
                message="User with this email already exists"
            )
        )

    # Validate role
    try:
        user_role = UserRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=create_error_response(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"Invalid role: {request.role}"
            )
        )

    # Create user
    hashed_password = hash_password(request.password)
    user = User(
        email=request.email,
        password_hash=hashed_password,
        full_name=request.full_name,
        role=user_role,
        status=AccountStatus.ACTIVE,
        created_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Register device
    device = register_or_update_device(
        user_id=user.id,
        device_info=request.device.model_dump(),
        db=db
    )

    # Create tokens
    access_token, expires_in = create_access_token(user.id)
    refresh_token = create_refresh_token_pair(user.id, device.device_id, db)

    # Build response
    user_response = UserMobileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        avatar_url=None,
        created_at=user.created_at
    )

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

    auth_response = AuthResponse(
        user=user_response,
        tokens=token_response
    )

    return create_success_response(
        data=auth_response.model_dump(),
        self_link="/api/v1/mobile/auth/register"
    )


@auth_router.post("/login", response_model=dict)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.

    Returns user info and tokens.
    """
    # Find user
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid email or password"
            )
        )

    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid email or password"
            )
        )

    # Check if account is active
    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=create_error_response(
                code=ErrorCode.FORBIDDEN,
                message=f"Account is {user.status.value}. Please contact support."
            )
        )

    # Register/update device
    device = register_or_update_device(
        user_id=user.id,
        device_info=request.device.model_dump(),
        db=db
    )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Create tokens
    access_token, expires_in = create_access_token(user.id)
    refresh_token = create_refresh_token_pair(user.id, device.device_id, db)

    # Build response
    user_response = UserMobileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        avatar_url=None,
        created_at=user.created_at
    )

    token_response = TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in
    )

    auth_response = AuthResponse(
        user=user_response,
        tokens=token_response
    )

    return create_success_response(
        data=auth_response.model_dump(),
        self_link="/api/v1/mobile/auth/login"
    )


@auth_router.post("/refresh", response_model=dict)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.

    Returns new access token.
    """
    # Decode refresh token
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=create_error_response(
                    code=ErrorCode.INVALID_TOKEN,
                    message="Invalid token type"
                )
            )

        user_id = int(payload.get("sub"))
        device_id = payload.get("device_id")

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.TOKEN_EXPIRED,
                message="Refresh token has expired. Please login again."
            )
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.INVALID_TOKEN,
                message=f"Invalid refresh token: {str(e)}"
            )
        )

    # Hash token and verify in database
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    stored_token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.user_id == user_id
    ).first()

    if not stored_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.INVALID_TOKEN,
                message="Refresh token not found"
            )
        )

    if stored_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.INVALID_TOKEN,
                message="Refresh token has been revoked"
            )
        )

    if not stored_token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                code=ErrorCode.TOKEN_EXPIRED,
                message="Refresh token has expired. Please login again."
            )
        )

    # Create new access token
    access_token, expires_in = create_access_token(user_id)

    token_response = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in
    )

    return create_success_response(
        data=token_response.model_dump(),
        self_link="/api/v1/mobile/auth/refresh"
    )


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest,
    db: Session = Depends(get_db),
    user: User = Depends(lambda: None)  # Will be replaced with actual auth dependency
):
    """
    Logout user and revoke refresh tokens.

    If device_id provided, only logout that device.
    Otherwise, logout all devices.
    """
    # TODO: Add actual authentication dependency once implemented
    # For now, this is a placeholder

    if request.device_id:
        # Revoke tokens for specific device
        tokens = db.query(RefreshToken).filter(
            RefreshToken.device_id == request.device_id,
            RefreshToken.is_revoked == False
        ).all()

        for token in tokens:
            token.is_revoked = True
            token.revoked_at = datetime.utcnow()

        # Mark device as inactive
        device = db.query(MobileDevice).filter(
            MobileDevice.device_id == request.device_id
        ).first()
        if device:
            device.is_active = False

    else:
        # Revoke all tokens for user (logout all devices)
        # This requires user authentication to get user_id
        # TODO: Implement when auth dependency is added
        pass

    db.commit()
    return None  # 204 No Content
