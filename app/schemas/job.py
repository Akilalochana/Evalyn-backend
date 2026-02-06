"""
Pydantic schemas for Job API
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobBase(BaseModel):
    title: str
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = "Full-time"
    experience_level: Optional[str] = None
    min_experience_years: Optional[int] = 0
    max_experience_years: Optional[int] = 10
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: str
    requirements: str
    responsibilities: Optional[str] = None
    benefits: Optional[str] = None
    deadline: Optional[datetime] = None


class JobCreate(JobBase):
    pass


class JobUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    min_experience_years: Optional[int] = None
    max_experience_years: Optional[int] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    benefits: Optional[str] = None
    is_active: Optional[bool] = None
    is_published: Optional[bool] = None
    deadline: Optional[datetime] = None


class JobResponse(JobBase):
    id: int
    is_active: bool
    is_published: bool
    created_at: datetime
    updated_at: datetime
    application_count: Optional[int] = 0
    
    class Config:
        from_attributes = True


class JobPublicResponse(BaseModel):
    """For public careers page - limited info"""
    id: int
    title: str
    department: Optional[str]
    location: Optional[str]
    job_type: Optional[str]
    experience_level: Optional[str]
    description: str
    requirements: str
    responsibilities: Optional[str]
    benefits: Optional[str]
    deadline: Optional[datetime]
    
    class Config:
        from_attributes = True
