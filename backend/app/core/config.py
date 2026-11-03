import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "IndusPilot"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "induspilot-super-secure-production-secret-key-tech4bharat-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Database (Canonical absolute path so alembic and app always share the exact same DB)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../induspilot.db')).replace('\\', '/')}"
    )
    
    # Multi-tenancy default
    DEFAULT_ORGANIZATION_ID: str = "org_tech4bharat_induspilot_demo"
    DEFAULT_FACTORY_NAME: str = "Apex Precision Fabrication Works"
    
    # Storage & Uploads
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/uploads")))
    SAMPLE_DIR: str = os.getenv("SAMPLE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data/sample_quotations")))
    
    # AI & Simulation configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    SIMULATION_MODE: bool = True  # Safeguard: External email and purchasing simulate responses by default
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.SAMPLE_DIR, exist_ok=True)

