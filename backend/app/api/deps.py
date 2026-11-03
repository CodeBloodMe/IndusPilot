from typing import Generator
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.core.config import settings

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_org_id(
    x_org_id: str = Header(default=settings.DEFAULT_ORGANIZATION_ID, alias="X-Organization-ID")
) -> str:
    """
    Retrieves the tenant organization context from request headers,
    falling back to the demonstration organization ID.
    Enforces multi-tenant scoping.
    """
    if not x_org_id or len(x_org_id.strip()) == 0:
        return settings.DEFAULT_ORGANIZATION_ID
    return x_org_id.strip()

