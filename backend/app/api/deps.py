from typing import Generator, Optional, Tuple
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.session import SessionLocal
from app.core.config import settings
from app.models.entities import User, Organization


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_and_org(
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_org_id: Optional[str] = Header(None, alias="X-Organization-ID")
) -> Tuple[User, str]:
    """
    Authenticates caller and validates organization membership.
    
    Identity resolution precedence:
    1. Authorization: Bearer <token_or_user_id>
    2. X-User-ID: <user_id>
    3. Demo mode default: User 'user_rajesh_sharma' for 'org-induspilot-demo'.
    
    Security Enforcements:
    - Caller cannot spoof X-Organization-ID unless they are an active member.
    - Invalid or unknown credentials return 401 Unauthorized.
    - Cross-tenant requests return 403 Forbidden.
    """
    user: Optional[User] = None

    # 1. Resolve identity from credentials
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
        else:
            token = authorization.strip()

        # Search user by ID or email
        user = db.query(User).filter(
            or_(User.id == token, User.email == token)
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials or token expired.",
                headers={"WWW-Authenticate": "Bearer"}
            )
    elif x_user_id:
        user = db.query(User).filter(User.id == x_user_id.strip()).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"User '{x_user_id}' not found.",
                headers={"WWW-Authenticate": "Bearer"}
            )
    else:
        # No credentials provided
        if x_org_id and x_org_id.strip() != settings.DEFAULT_ORGANIZATION_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication credentials required to access tenant organization.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        # Default demo user
        user = db.query(User).filter(User.id == "user_rajesh_sharma").first()
        if not user:
            user = db.query(User).filter(User.organization_id == settings.DEFAULT_ORGANIZATION_ID).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account '{user.id}' is inactive."
        )

    # 2. Validate tenant membership
    requested_org_id = x_org_id.strip() if (x_org_id and len(x_org_id.strip()) > 0) else user.organization_id

    if requested_org_id != user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: User '{user.id}' is not an authorized member of organization '{requested_org_id}'."
        )

    return user, requested_org_id


def get_current_org_id(
    user_and_org: Tuple[User, str] = Depends(get_current_user_and_org)
) -> str:
    """Retrieves verified tenant organization context."""
    return user_and_org[1]


def get_current_user(
    user_and_org: Tuple[User, str] = Depends(get_current_user_and_org)
) -> User:
    """Retrieves authenticated active user."""
    return user_and_org[0]
