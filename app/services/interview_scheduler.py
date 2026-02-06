"""
Interview Scheduling Service
Handles scheduling interviews with SSE for shortlisted candidates
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.application import Application, ApplicationStatus
from app.models.interview import Interview, InterviewRound, InterviewStatus
from app.models.job import Job
from app.services.email_service import email_service


class InterviewScheduler:
    """
    Service for scheduling interviews with shortlisted candidates
    Integrates with SSE calendar and sends invitations
    """
    
    def schedule_single_interview(
        self,
        db: Session,
        application_id: int,
        interviewer_name: str,
        interviewer_email: str,
        scheduled_at: datetime,
        duration_minutes: int = 60,
        meeting_link: Optional[str] = None,
        location: Optional[str] = None,
        round: str = InterviewRound.ROUND2.value
    ) -> Interview:
        """Schedule a single interview for a candidate"""
        
        # Get application
        application = db.query(Application).filter(
            Application.id == application_id
        ).first()
        
        if not application:
            raise ValueError(f"Application {application_id} not found")
        
        # Create interview record
        interview = Interview(
            application_id=application_id,
            round=round,
            interviewer_name=interviewer_name,
            interviewer_email=interviewer_email,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            meeting_link=meeting_link,
            location=location,
            status=InterviewStatus.SCHEDULED.value
        )
        
        db.add(interview)
        
        # Update application status
        application.status = ApplicationStatus.ROUND2_SCHEDULED.value
        
        db.commit()
        db.refresh(interview)
        
        # Send interview invitation email
        job = db.query(Job).filter(Job.id == application.job_id).first()
        if job:
            email_service.send_interview_invitation(application, interview, job)
        
        return interview
    
    def schedule_bulk_interviews(
        self,
        db: Session,
        job_id: int,
        interviewer_name: str,
        interviewer_email: str,
        start_datetime: datetime,
        duration_minutes: int = 60,
        gap_minutes: int = 30,
        meeting_link_base: Optional[str] = None
    ) -> List[Interview]:
        """
        Schedule interviews for all shortlisted candidates of a job
        Interviews are scheduled sequentially with gaps between them
        """
        
        # Get job
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Get all shortlisted applications
        applications = db.query(Application).filter(
            Application.job_id == job_id,
            Application.status == ApplicationStatus.SHORTLISTED.value
        ).order_by(Application.ai_score.desc()).all()
        
        if not applications:
            return []
        
        interviews = []
        current_time = start_datetime
        
        for i, app in enumerate(applications):
            # Generate unique meeting link if base provided
            meeting_link = None
            if meeting_link_base:
                meeting_link = f"{meeting_link_base}?candidate={app.id}"
            
            # Create interview
            interview = Interview(
                application_id=app.id,
                round=InterviewRound.ROUND2.value,
                interviewer_name=interviewer_name,
                interviewer_email=interviewer_email,
                scheduled_at=current_time,
                duration_minutes=duration_minutes,
                meeting_link=meeting_link,
                status=InterviewStatus.SCHEDULED.value
            )
            
            db.add(interview)
            
            # Update application status
            app.status = ApplicationStatus.ROUND2_SCHEDULED.value
            
            interviews.append(interview)
            
            # Move to next time slot
            current_time += timedelta(minutes=duration_minutes + gap_minutes)
        
        db.commit()
        
        # Refresh all interviews and send emails
        for interview in interviews:
            db.refresh(interview)
            app = db.query(Application).filter(
                Application.id == interview.application_id
            ).first()
            if app:
                email_service.send_interview_invitation(app, interview, job)
        
        return interviews
    
    def reschedule_interview(
        self,
        db: Session,
        interview_id: int,
        new_datetime: datetime,
        new_meeting_link: Optional[str] = None
    ) -> Interview:
        """Reschedule an existing interview"""
        
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()
        
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        interview.scheduled_at = new_datetime
        if new_meeting_link:
            interview.meeting_link = new_meeting_link
        interview.status = InterviewStatus.RESCHEDULED.value
        
        db.commit()
        db.refresh(interview)
        
        # Send updated invitation
        application = db.query(Application).filter(
            Application.id == interview.application_id
        ).first()
        
        if application:
            job = db.query(Job).filter(Job.id == application.job_id).first()
            if job:
                email_service.send_interview_invitation(application, interview, job)
        
        return interview
    
    def complete_interview(
        self,
        db: Session,
        interview_id: int,
        feedback: str,
        rating: int,  # 1-5
        passed: bool
    ) -> Interview:
        """Mark interview as completed with feedback"""
        
        interview = db.query(Interview).filter(
            Interview.id == interview_id
        ).first()
        
        if not interview:
            raise ValueError(f"Interview {interview_id} not found")
        
        interview.status = InterviewStatus.COMPLETED.value
        interview.feedback = feedback
        interview.rating = rating
        
        db.commit()
        
        # Update application status
        application = db.query(Application).filter(
            Application.id == interview.application_id
        ).first()
        
        if application:
            if passed:
                application.status = ApplicationStatus.ROUND2_COMPLETED.value
            else:
                application.status = ApplicationStatus.REJECTED.value
            db.commit()
        
        db.refresh(interview)
        return interview
    
    def get_sse_schedule(
        self,
        db: Session,
        interviewer_email: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Interview]:
        """Get all scheduled interviews for an SSE in a date range"""
        
        return db.query(Interview).filter(
            Interview.interviewer_email == interviewer_email,
            Interview.scheduled_at >= start_date,
            Interview.scheduled_at <= end_date,
            Interview.status.in_([
                InterviewStatus.SCHEDULED.value,
                InterviewStatus.CONFIRMED.value,
                InterviewStatus.RESCHEDULED.value
            ])
        ).order_by(Interview.scheduled_at).all()


# Singleton instance
interview_scheduler = InterviewScheduler()
