"""
Application/Candidate API Endpoints
Handles candidate applications, CV uploads, and AI screening
"""
import os
import json
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.schemas.application import (
    ApplicationCreate, ApplicationResponse, ApplicationDetailResponse,
    ApplicationScreeningResult, BulkScreeningResponse
)
from app.services.ai_agent import ai_agent
from app.services.email_service import email_service

router = APIRouter(prefix="/applications", tags=["Applications"])

# Upload directory for CVs
UPLOAD_DIR = "uploads/cvs"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============== PUBLIC ENDPOINTS (Career Apply) ==============

@router.post("/apply", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    job_id: int = Form(...),
    full_name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    linkedin_url: Optional[str] = Form(None),
    portfolio_url: Optional[str] = Form(None),
    cover_letter: Optional[str] = Form(None),
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Submit a job application (Public endpoint for careers page)
    Candidates use this to apply with their CV
    """
    # Verify job exists and is published
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.is_published == True,
        Job.is_active == True
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not accepting applications")
    
    # Check if already applied
    existing = db.query(Application).filter(
        Application.job_id == job_id,
        Application.email == email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this position")
    
    # Save CV file
    file_ext = os.path.splitext(cv_file.filename)[1].lower()
    if file_ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(status_code=400, detail="CV must be PDF or Word document")
    
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in full_name if c.isalnum() or c == " ").replace(" ", "_")
    filename = f"{safe_name}_{job_id}_{timestamp}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(cv_file.file, buffer)
    
    # Extract CV text
    cv_text = ai_agent.extract_cv_text(file_path)
    
    # Create application
    application = Application(
        job_id=job_id,
        full_name=full_name,
        email=email,
        phone=phone,
        linkedin_url=linkedin_url,
        portfolio_url=portfolio_url,
        cover_letter=cover_letter,
        cv_file_path=file_path,
        cv_text=cv_text,
        status=ApplicationStatus.PENDING.value
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application


# ============== HR DASHBOARD ENDPOINTS ==============

@router.get("/job/{job_id}", response_model=List[ApplicationDetailResponse])
def get_job_applications(
    job_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all applications for a job (HR Dashboard)
    Includes AI screening results
    """
    query = db.query(Application).filter(Application.job_id == job_id)
    
    if status_filter:
        query = query.filter(Application.status == status_filter)
    
    applications = query.order_by(Application.ai_score.desc()).all()
    return applications


@router.get("/{application_id}", response_model=ApplicationDetailResponse)
def get_application(application_id: int, db: Session = Depends(get_db)):
    """Get detailed application information"""
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return application


@router.post("/job/{job_id}/screen", response_model=BulkScreeningResponse)
async def screen_applications(
    job_id: int,
    top_n: Optional[int] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Run AI screening on all pending applications for a job
    - Analyzes CVs against job requirements
    - Scores candidates (0-100)
    - Shortlists top N candidates (default: 10)
    - Updates application statuses
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Count pending applications
    pending_count = db.query(Application).filter(
        Application.job_id == job_id,
        Application.status == ApplicationStatus.PENDING.value
    ).count()
    
    if pending_count == 0:
        return BulkScreeningResponse(
            job_id=job_id,
            total_applications=0,
            screened_count=0,
            shortlisted_candidates=[],
            message="No pending applications to screen"
        )
    
    # Run AI screening
    if top_n is None:
        top_n = settings.CV_SCREENING_TOP_CANDIDATES
    
    shortlisted = ai_agent.screen_applications(db, job_id, top_n)
    
    # Prepare response
    shortlisted_results = []
    for app in shortlisted:
        skills = json.loads(app.skills_matched) if app.skills_matched else []
        shortlisted_results.append(ApplicationScreeningResult(
            application_id=app.id,
            candidate_name=app.full_name,
            email=app.email,
            ai_score=app.ai_score or 0,
            ai_summary=app.ai_summary or "",
            ai_strengths=app.ai_strengths or "",
            ai_weaknesses=app.ai_weaknesses or "",
            skills_matched=skills,
            is_shortlisted=app.status == ApplicationStatus.SHORTLISTED.value
        ))
    
    return BulkScreeningResponse(
        job_id=job_id,
        total_applications=pending_count,
        screened_count=pending_count,
        shortlisted_candidates=shortlisted_results,
        message=f"Screened {pending_count} applications. Top {len(shortlisted_results)} shortlisted."
    )


@router.post("/job/{job_id}/notify-shortlisted")
async def notify_shortlisted_candidates(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Send emails to all shortlisted candidates
    Notifies them they passed Round 1 and are selected for Round 2
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get shortlisted applications
    shortlisted = db.query(Application).filter(
        Application.job_id == job_id,
        Application.status == ApplicationStatus.SHORTLISTED.value
    ).all()
    
    if not shortlisted:
        return {"message": "No shortlisted candidates to notify", "sent": 0}
    
    # Send emails
    results = email_service.send_bulk_shortlist_notifications(shortlisted, job)
    
    # Update status to round1_passed
    for app in shortlisted:
        app.status = ApplicationStatus.ROUND1_PASSED.value
    db.commit()
    
    return {
        "message": f"Sent {results['success']} notification emails",
        "sent": results['success'],
        "failed": results['failed'],
        "details": results['emails']
    }


@router.put("/{application_id}/status")
def update_application_status(
    application_id: int,
    new_status: str,
    db: Session = Depends(get_db)
):
    """Manually update application status"""
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Validate status
    valid_statuses = [s.value for s in ApplicationStatus]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    application.status = new_status
    db.commit()
    
    return {"message": f"Status updated to {new_status}"}


@router.get("/job/{job_id}/statistics")
def get_job_application_statistics(job_id: int, db: Session = Depends(get_db)):
    """Get application statistics for a job"""
    from sqlalchemy import func
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Count by status
    status_counts = db.query(
        Application.status,
        func.count(Application.id)
    ).filter(
        Application.job_id == job_id
    ).group_by(Application.status).all()
    
    stats = {status: count for status, count in status_counts}
    
    # Get average score
    avg_score = db.query(func.avg(Application.ai_score)).filter(
        Application.job_id == job_id,
        Application.ai_score.isnot(None)
    ).scalar()
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_applications": sum(stats.values()),
        "by_status": stats,
        "average_ai_score": round(avg_score or 0, 2)
    }
