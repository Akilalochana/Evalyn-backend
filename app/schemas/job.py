"""
Pydantic schemas for Job API
Updated for NeonDB JobPost table compatibility
"""
import uuid
from pydantic import BaseModel, field_validator
from typing import Optional, List, Union
from datetime import datetime


class JobBase(BaseModel):
    """Base job schema - compatible with NeonDB JobPost table"""
    title: str
    description: Optional[str] = None
    requirements: Optional[Union[str, List[str]]] = None
    
    @field_validator('requirements', mode='before')
    @classmethod
    def convert_requirements(cls, v):
        """Convert list to string if needed"""
        if isinstance(v, list):
            return '\n'.join(v)
        return v


class JobCreate(JobBase):
    """Schema for creating a new job"""
    id: Optional[str] = None  # Will be auto-generated if not provided
    
    @field_validator('id', mode='before')
    @classmethod
    def generate_id(cls, v):
        if v is None:
            return str(uuid.uuid4())[:25]
        return v


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    title: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    jobType: Optional[str] = None
    experienceLevel: Optional[str] = None
    minExperienceYears: Optional[int] = None
    maxExperienceYears: Optional[int] = None
    salaryMin: Optional[float] = None
    salaryMax: Optional[float] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    responsibilities: Optional[str] = None
    benefits: Optional[str] = None
    isActive: Optional[bool] = None
    isPublished: Optional[bool] = None
    deadline: Optional[datetime] = None


class JobResponse(BaseModel):
    """Response schema for job details - minimal to match NeonDB"""
    id: str
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    createdAt: Optional[datetime] = None
    
    # Optional fields with defaults for backwards compatibility
    department: Optional[str] = None
    location: Optional[str] = "Remote"
    jobType: Optional[str] = "Full-time"
    experienceLevel: Optional[str] = "Mid-level"
    minExperienceYears: Optional[int] = 0
    maxExperienceYears: Optional[int] = 10
    salaryMin: Optional[float] = None
    salaryMax: Optional[float] = None
    responsibilities: Optional[str] = None
    benefits: Optional[str] = None
    isActive: Optional[bool] = True
    isPublished: Optional[bool] = True
    updatedAt: Optional[datetime] = None
    deadline: Optional[datetime] = None
    application_count: Optional[int] = 0
    
    @field_validator('requirements', mode='before')
    @classmethod
    def convert_requirements(cls, v):
        """Convert list to string if needed"""
        if isinstance(v, list):
            return '\n'.join(v)
        return v
    
    class Config:
        from_attributes = True


class JobPublicResponse(BaseModel):
    """For public careers page - limited info"""
    id: str
    title: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = "Remote"
    jobType: Optional[str] = "Full-time"
    experienceLevel: Optional[str] = "Mid-level"
    responsibilities: Optional[str] = None
    benefits: Optional[str] = None
    deadline: Optional[datetime] = None
    createdAt: Optional[datetime] = None
    
    @field_validator('requirements', mode='before')
    @classmethod
    def convert_requirements(cls, v):
        """Convert list to string if needed"""
        if isinstance(v, list):
            return '\n'.join(v)
        return v
    
    class Config:
        from_attributes = True
