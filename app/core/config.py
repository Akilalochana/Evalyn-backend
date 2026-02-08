"""
Configuration settings for HR Automation Agent
Supports NeonDB (PostgreSQL) and Vercel Blob Storage
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Evalyn HR Automation Agent"
    DEBUG: bool = True
    
    # Database (NeonDB PostgreSQL)
    DATABASE_URL: str = "postgresql://user:password@host/database"
    
    # Google Gemini AI (using Gemini Flash)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"  # Free tier model
    
    # Vercel Blob Storage (for PDF/Resume storage)
    VERCEL_BLOB_READ_WRITE_TOKEN: str = ""
    VERCEL_BLOB_STORE_ID: str = ""
    VERCEL_BLOB_BASE_URL: str = "https://u8y5z64xjxmqlcdt.public.blob.vercel-storage.com"
    
    # Email Configuration (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "hr@yourcompany.com"
    
    # Company Info
    COMPANY_NAME: str = "Your Company"
    CAREERS_PAGE_URL: str = "https://yourcompany.com/careers"
    
    # AI Agent Settings
    CV_SCREENING_TOP_CANDIDATES: int = 10
    MINIMUM_MATCH_SCORE: float = 75.0  # Candidates with 75% or above are automatically selected
    
    # SSE (Senior Software Engineer) Default Settings for Interviews
    DEFAULT_SSE_NAME: str = "Senior Software Engineer"
    DEFAULT_SSE_EMAIL: str = "sse@yourcompany.com"
    INTERVIEW_DURATION_MINUTES: int = 60
    INTERVIEW_GAP_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
