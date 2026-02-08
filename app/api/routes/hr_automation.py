"""
HR Automation Workflow API
Complete AI-powered HR automation for job applications
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
import traceback

from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application, ApplicationStatus
from app.services.ai_agent import ai_agent


router = APIRouter(prefix="/hr-automation", tags=["HR Automation"])


# Request/Response Models
class WorkflowRequest(BaseModel):
    """Request model for running the HR automation workflow"""
    job_id: str
    sse_name: Optional[str] = None
    sse_email: Optional[str] = None
    interview_start_datetime: Optional[datetime] = None


class WorkflowResponse(BaseModel):
    """Response model for workflow results"""
    job_id: str
    workflow_started_at: str
    workflow_completed_at: Optional[str] = None
    message: str
    steps: list


# ============== MAIN WORKFLOW ENDPOINT ==============

@router.post("/run-workflow", response_model=WorkflowResponse)
def run_hr_automation_workflow(
    request: WorkflowRequest,
    db: Session = Depends(get_db)
):
    """
    🤖 Run the complete HR AI Automation Workflow
    
    This endpoint automates the entire HR recruitment process:
    
    1. **AI CV Screening**: Analyze all pending applications using Gemini AI
       - Downloads CVs from Vercel Blob storage
       - Compares CVs against job requirements
       - Scores each candidate (0-100%)
    
    2. **Shortlist Top 10**: Select best candidates
       - Candidates with ≥75% score are shortlisted
       - Maximum 10 candidates per job
    
    3. **Send Notifications**: Email all shortlisted candidates
       - Congratulations on passing Round 1
       - Information about Round 2 interview
    
    4. **Schedule Interviews**: Book Round 2 with SSE
       - Auto-schedule interviews with gaps
       - Send calendar invitations
    
    **Required**: Job ID
    **Optional**: SSE details, interview start time
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {request.job_id}")
    
    # Check for pending applications
    pending_count = db.query(Application).filter(
        Application.jobId == request.job_id,
        Application.status == ApplicationStatus.PENDING.value
    ).count()
    
    if pending_count == 0:
        return WorkflowResponse(
            job_id=request.job_id,
            workflow_started_at=datetime.utcnow().isoformat(),
            message="No pending applications to process",
            steps=[]
        )
    
    # Run the full workflow
    try:
        result = ai_agent.run_full_hr_workflow(
            db=db,
            job_id=request.job_id,
            sse_name=request.sse_name,
            sse_email=request.sse_email,
            interview_start_datetime=request.interview_start_datetime
        )
        
        return WorkflowResponse(
            job_id=result["job_id"],
            workflow_started_at=result["workflow_started_at"],
            workflow_completed_at=result.get("workflow_completed_at"),
            message=result.get("message", "Workflow completed"),
            steps=result.get("steps", [])
        )
    except Exception as e:
        print(f"[ERROR] WORKFLOW ERROR: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")


# ============== INDIVIDUAL STEP ENDPOINTS ==============

@router.post("/screen/{job_id}")
def screen_applications_only(
    job_id: str,
    top_n: Optional[int] = 10,
    db: Session = Depends(get_db)
):
    """
    Step 1 Only: AI Screen all pending applications
    
    - Downloads CVs from Vercel Blob
    - Analyzes with Gemini AI
    - Scores and ranks candidates
    - Shortlists top N candidates (≥75% score)
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    shortlisted = ai_agent.screen_applications(db, job_id, top_n)
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_screened": len(shortlisted),
        "shortlisted": [
            {
                "id": app.id,
                "name": app.name,
                "email": app.email,
                "score": getattr(app, '_ai_score', 0),
                "status": app.status,
                "summary": getattr(app, '_ai_summary', '')
            }
            for app in shortlisted
        ]
    }


@router.get("/status/{job_id}")
def get_workflow_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the current status of applications for a job
    
    Shows count of applications in each status:
    - pending, screening, shortlisted, round1_passed, 
    - round2_scheduled, round2_completed, hired, rejected
    """
    from sqlalchemy import func
    
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Count by status
    status_counts = db.query(
        Application.status,
        func.count(Application.id)
    ).filter(
        Application.jobId == job_id
    ).group_by(Application.status).all()
    
    counts = {status: count for status, count in status_counts}
    
    # Get shortlisted candidates
    shortlisted = db.query(Application).filter(
        Application.jobId == job_id,
        Application.status.in_([
            ApplicationStatus.SHORTLISTED.value,
            ApplicationStatus.ROUND1_PASSED.value,
            ApplicationStatus.ROUND2_SCHEDULED.value
        ])
    ).order_by(Application.ai_score.desc()).all()
    
    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_applications": sum(counts.values()),
        "status_breakdown": counts,
        "top_candidates": [
            {
                "id": app.id,
                "name": app.name,
                "email": app.email,
                "score": app.ai_score,
                "status": app.status
            }
            for app in shortlisted[:10]
        ]
    }


@router.get("/candidate/{application_id}/summary")
def get_candidate_ai_summary(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed AI analysis summary for a candidate
    
    Includes:
    - AI Score
    - Strengths
    - Weaknesses/Gaps
    - Matched Skills
    - Interview preparation notes
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    import json
    skills = []
    if app.skills_matched:
        try:
            skills = json.loads(app.skills_matched)
        except:
            skills = []
    
    return {
        "application_id": app.id,
        "candidate_name": app.name,
        "email": app.email,
        "phone": app.phone,
        "status": app.status,
        "ai_analysis": {
            "score": app.ai_score,
            "summary": app.ai_summary,
            "strengths": app.ai_strengths,
            "weaknesses": app.ai_weaknesses,
            "skills_matched": skills
        },
        "resume_url": app.resumeUrl,
        "applied_at": app.createdAt.isoformat() if app.createdAt else None,
        "interview_prep_notes": ai_agent.get_candidate_summary(app)
    }
