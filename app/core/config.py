"""
Configuration settings for HR Automation Agent
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Evalyn HR Automation Agent"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./evalyn_hr.db"
    
    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    
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
    
    class Config:
        env_file = ".env"


settings = Settings()
