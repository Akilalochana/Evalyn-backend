"""
Pydantic schemas for Interview API
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class InterviewBase(BaseModel):
    interviewer_name: str
    interviewer_email: str
    scheduled_at: datetime
    duration_minutes: Optional[int] = 60
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class InterviewCreate(InterviewBase):
    application_id: int
    round: Optional[str] = "round2"


class InterviewUpdate(BaseModel):
    interviewer_name: Optional[str] = None
    interviewer_email: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[str] = None
    rating: Optional[int] = None


class InterviewResponse(InterviewBase):
    id: int
    application_id: int
    round: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class BulkInterviewScheduleRequest(BaseModel):
    """Schedule interviews for multiple candidates"""
    job_id: int
    interviewer_name: str
    interviewer_email: str
    start_date: datetime
    duration_minutes: Optional[int] = 60
    gap_between_interviews_minutes: Optional[int] = 30
    meeting_link_base: Optional[str] = None


class BulkInterviewScheduleResponse(BaseModel):
    total_scheduled: int
    interviews: list[InterviewResponse]
    message: str
