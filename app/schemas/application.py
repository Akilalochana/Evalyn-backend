"""
Pydantic schemas for Application API
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class ApplicationBase(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    cover_letter: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    job_id: int


class ApplicationResponse(ApplicationBase):
    id: int
    job_id: int
    status: str
    applied_at: datetime
    
    class Config:
        from_attributes = True


class ApplicationDetailResponse(ApplicationResponse):
    """Full details including AI screening results"""
    cv_file_path: Optional[str]
    ai_score: Optional[float]
    ai_summary: Optional[str]
    ai_strengths: Optional[str]
    ai_weaknesses: Optional[str]
    skills_matched: Optional[str]
    screening_completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ApplicationScreeningResult(BaseModel):
    """Result from AI screening"""
    application_id: int
    candidate_name: str
    email: str
    ai_score: float
    ai_summary: str
    ai_strengths: str
    ai_weaknesses: str
    skills_matched: List[str]
    is_shortlisted: bool


class BulkScreeningResponse(BaseModel):
    """Response for bulk screening operation"""
    job_id: int
    total_applications: int
    screened_count: int
    shortlisted_candidates: List[ApplicationScreeningResult]
    message: str
