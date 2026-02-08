"""
Pydantic schemas for Application API
Updated for NeonDB schema compatibility
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class ApplicationBase(BaseModel):
    """Base application schema - matches NeonDB JobApplication table"""
    name: str  # NeonDB uses 'name' not 'full_name'
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    coverLetter: Optional[str] = None  # NeonDB uses camelCase


class ApplicationCreate(ApplicationBase):
    jobId: str  # NeonDB uses string IDs


class ApplicationResponse(BaseModel):
    """Response schema for applications"""
    id: str
    jobId: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    status: str
    createdAt: Optional[datetime] = None
    
    # Aliases for backward compatibility
    @property
    def full_name(self):
        return self.name
    
    @property
    def job_id(self):
        return self.jobId
    
    @property
    def applied_at(self):
        return self.createdAt
    
    class Config:
        from_attributes = True


class ApplicationDetailResponse(ApplicationResponse):
    """Full details including AI screening results"""
    resumeUrl: Optional[str] = None
    coverLetter: Optional[str] = None
    ai_score: Optional[float] = None
    ai_summary: Optional[str] = None
    ai_strengths: Optional[str] = None
    ai_weaknesses: Optional[str] = None
    skills_matched: Optional[str] = None
    screening_completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ApplicationScreeningResult(BaseModel):
    """Result from AI screening"""
    application_id: str
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
    job_id: str
    total_applications: int
    screened_count: int
    shortlisted_candidates: List[ApplicationScreeningResult]
    message: str
