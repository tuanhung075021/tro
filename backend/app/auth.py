# Copyright (c) 2026 tro. Contributors
# SPDX-License-Identifier: MIT
"""FastAPI authentication, role-based access control, and room invite code lifecycle router."""

from typing import Optional
from .compat import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    OAuth2PasswordBearer,
    Session,
    select,
    status,
)
from .database import get_session
from .models import Property, Room, User
from .schemas import RoomOut, TokenResponse, UserLogin, UserOut, UserRegister
from .security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    session: Session = Depends(get_session),
) -> User:
    """Dependency extracting and verifying the JWT token to return the current User."""
    raw_token = None
    if isinstance(token, str) and token:
        raw_token = token
    elif isinstance(authorization, str) and authorization:
        auth_str = authorization.strip()
        if auth_str.lower().startswith("bearer "):
            raw_token = auth_str[7:].strip()
        else:
            raw_token = auth_str

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: Optional[str] = payload.get("sub") or payload.get("username")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: sub missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_landlord(current_user: User = Depends(get_current_user)) -> User:
    """Dependency ensuring the authenticated user has the 'landlord' role."""
    if not current_user.is_landlord:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: landlord privileges required",
        )
    return current_user


def require_tenant(current_user: User = Depends(get_current_user)) -> User:
    """Dependency ensuring the authenticated user has the 'tenant' role."""
    if not current_user.is_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: tenant privileges required",
        )
    return current_user


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister,
    session: Session = Depends(get_session),
) -> UserOut:
    """Register a new user account (Landlord or Tenant).

    If the user is a tenant and provides a valid invite_code, they are automatically
    assigned to the corresponding room, setting its status to 'active'.
    """
    # Check username collision
    existing = session.exec(select(User).where(User.username == user_data.username)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' is already registered",
        )

    # If tenant with invite code, validate room existence and occupancy upfront
    room: Optional[Room] = None
    cleaned_code = user_data.invite_code.strip() if user_data.invite_code else None
    if user_data.role == "tenant" and cleaned_code:
        room = session.exec(select(Room).where(Room.invite_code == cleaned_code)).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invalid invite code: '{cleaned_code}'. Room not found.",
            )
        if room.tenant_id is not None or room.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Room with invite code '{cleaned_code}' is already occupied.",
            )

    # Hash password and persist user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
    )
    try:
        session.add(user)
        session.commit()
        session.refresh(user)

        # Link tenant to room if invite code was validated
        if room is not None:
            room.assign_tenant(user.id)
            session.add(room)
            session.commit()
            session.refresh(room)
    except Exception:
        session.rollback()
        raise

    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: UserLogin,
    session: Session = Depends(get_session),
) -> TokenResponse:
    """Authenticate user credentials and issue a JWT access token."""
    user = session.exec(select(User).where(User.username == login_data.username)).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
        full_name=user.full_name,
    )


@router.get("/me", response_model=UserOut)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """Return profile details for the currently authenticated user."""
    return UserOut.model_validate(current_user)


@router.post("/rooms/{room_id}/remove-tenant", response_model=RoomOut)
def remove_tenant_from_room(
    room_id: int,
    current_user: User = Depends(require_landlord),
    session: Session = Depends(get_session),
) -> RoomOut:
    """Landlord-only endpoint to remove a tenant from a room, set status to 'empty',
    and regenerate the room invite_code for subsequent tenants.
    """
    require_landlord(current_user)
    room = session.get(Room, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room with id {room_id} not found",
        )

    # If room is part of a property, verify landlord ownership
    if room.property_id is not None:
        prop = session.get(Property, room.property_id)
        if prop is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property with id {room.property_id} not found",
            )
        if prop.landlord_id is not None and prop.landlord_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to manage rooms in this property",
            )

    room.remove_tenant()
    session.add(room)
    session.commit()
    session.refresh(room)
    return RoomOut.model_validate(room)
