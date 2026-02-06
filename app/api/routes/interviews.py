"""
Interview Scheduling API Endpoints
Handles scheduling Round 2 interviews with SSE
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview, InterviewStatus
from app.schemas.interview import (
    InterviewCreate, InterviewUpdate, InterviewResponse,
    BulkInterviewScheduleRequest, BulkInterviewScheduleResponse
)
from app.services.interview_scheduler import interview_scheduler

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("/", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def schedule_interview(
    interview_data: InterviewCreate,
    db: Session = Depends(get_db)
):
    """
    Schedule a single interview for a candidate
    """
    interview = interview_scheduler.schedule_single_interview(
        db=db,
        application_id=interview_data.application_id,
        interviewer_name=interview_data.interviewer_name,
        interviewer_email=interview_data.interviewer_email,
        scheduled_at=interview_data.scheduled_at,
        duration_minutes=interview_data.duration_minutes,
        meeting_link=interview_data.meeting_link,
        location=interview_data.location,
        round=interview_data.round
    )
    
    return interview


@router.post("/bulk-schedule", response_model=BulkInterviewScheduleResponse)
def schedule_bulk_interviews(
    request: BulkInterviewScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Schedule interviews for all shortlisted candidates (Round 1 passed)
    Automatically spaces interviews with gaps
    Sends invitation emails to all candidates
    """
    # Get candidates who passed round 1
    candidates = db.query(Application).filter(
        Application.job_id == request.job_id,
        Application.status.in_([
            ApplicationStatus.SHORTLISTED.value,
            ApplicationStatus.ROUND1_PASSED.value
        ])
    ).all()
    
    if not candidates:
        return BulkInterviewScheduleResponse(
            total_scheduled=0,
            interviews=[],
            message="No candidates ready for interview scheduling"
        )
    
    # Mark all as shortlisted first (in case they're at round1_passed)
    for c in candidates:
        if c.status == ApplicationStatus.ROUND1_PASSED.value:
            c.status = ApplicationStatus.SHORTLISTED.value
    db.commit()
    
    # Schedule interviews
    interviews = interview_scheduler.schedule_bulk_interviews(
        db=db,
        job_id=request.job_id,
        interviewer_name=request.interviewer_name,
        interviewer_email=request.interviewer_email,
        start_datetime=request.start_date,
        duration_minutes=request.duration_minutes,
        gap_minutes=request.gap_between_interviews_minutes,
        meeting_link_base=request.meeting_link_base
    )
    
    return BulkInterviewScheduleResponse(
        total_scheduled=len(interviews),
        interviews=[InterviewResponse.model_validate(i) for i in interviews],
        message=f"Scheduled {len(interviews)} interviews. Invitations sent."
    )


@router.get("/job/{job_id}", response_model=List[InterviewResponse])
def get_job_interviews(
    job_id: int,
    status_filter: str = None,
    db: Session = Depends(get_db)
):
    """Get all interviews for a job"""
    query = db.query(Interview).join(Application).filter(
        Application.job_id == job_id
    )
    
    if status_filter:
        query = query.filter(Interview.status == status_filter)
    
    return query.order_by(Interview.scheduled_at).all()


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    """Get interview details"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    return interview


@router.put("/{interview_id}", response_model=InterviewResponse)
def update_interview(
    interview_id: int,
    update_data: InterviewUpdate,
    db: Session = Depends(get_db)
):
    """Update interview details"""
    interview = db.query(Interview).filter(
        Interview.id == interview_id
    ).first()
    
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(interview, field, value)
    
    db.commit()
    db.refresh(interview)
    
    return interview


@router.post("/{interview_id}/reschedule", response_model=InterviewResponse)
def reschedule_interview(
    interview_id: int,
    new_datetime: datetime,
    new_meeting_link: str = None,
    db: Session = Depends(get_db)
):
    """Reschedule an interview"""
    interview = interview_scheduler.reschedule_interview(
        db=db,
        interview_id=interview_id,
        new_datetime=new_datetime,
        new_meeting_link=new_meeting_link
    )
    
    return interview


@router.post("/{interview_id}/complete")
def complete_interview(
    interview_id: int,
    feedback: str,
    rating: int,  # 1-5
    passed: bool,
    db: Session = Depends(get_db)
):
    """
    Mark interview as completed with feedback
    Also updates application status based on result
    """
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    interview = interview_scheduler.complete_interview(
        db=db,
        interview_id=interview_id,
        feedback=feedback,
        rating=rating,
        passed=passed
    )
    
    return {
        "message": "Interview completed",
        "interview_id": interview.id,
        "result": "passed" if passed else "rejected"
    }


@router.get("/sse/schedule")
def get_sse_schedule(
    interviewer_email: str,
    start_date: datetime,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """
    Get all scheduled interviews for an SSE in a date range
    Useful for calendar integration
    """
    if end_date is None:
        end_date = start_date + timedelta(days=7)
    
    interviews = interview_scheduler.get_sse_schedule(
        db=db,
        interviewer_email=interviewer_email,
        start_date=start_date,
        end_date=end_date
    )
    
    return {
        "interviewer_email": interviewer_email,
        "date_range": {"start": start_date, "end": end_date},
        "total_interviews": len(interviews),
        "interviews": [InterviewResponse.model_validate(i) for i in interviews]
    }
