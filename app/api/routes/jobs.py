"""
Job Vacancy API Endpoints
HR Dashboard uses these to create and manage job postings
Updated for NeonDB JobPost table compatibility
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobPublicResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ============== HR DASHBOARD ENDPOINTS ==============

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new job vacancy
    Used by HR Dashboard to create new positions
    """
    job = Job(**job_data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    is_published: bool = None,
    db: Session = Depends(get_db)
):
    """
    List all jobs (HR Dashboard view)
    Includes all jobs with application counts
    """
    query = db.query(Job)
    
    if is_active is not None:
        query = query.filter(Job.isActive == is_active)  # NeonDB field name
    if is_published is not None:
        query = query.filter(Job.isPublished == is_published)  # NeonDB field name
    
    jobs = query.offset(skip).limit(limit).all()
    
    # Add application counts
    result = []
    for job in jobs:
        job_dict = JobResponse.model_validate(job)
        job_dict.application_count = db.query(func.count(Application.id)).filter(
            Application.jobId == job.id  # NeonDB field name
        ).scalar()
        result.append(job_dict)
    
    return result


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):  # Changed to string for NeonDB
    """Get a specific job by ID"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_response = JobResponse.model_validate(job)
    job_response.application_count = db.query(func.count(Application.id)).filter(
        Application.jobId == job.id  # NeonDB field name
    ).scalar()
    
    return job_response


@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, job_data: JobUpdate, db: Session = Depends(get_db)):  # Changed to string
    """Update a job vacancy"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)
    
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, db: Session = Depends(get_db)):  # Changed to string
    """Delete a job vacancy"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    db.delete(job)
    db.commit()
    return None


@router.post("/{job_id}/publish", response_model=JobResponse)
def publish_job(job_id: str, db: Session = Depends(get_db)):  # Changed to string
    """
    Publish a job to the careers page
    Makes it visible on the public careers page
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.isPublished = True  # NeonDB field name
    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/unpublish", response_model=JobResponse)
def unpublish_job(job_id: str, db: Session = Depends(get_db)):  # Changed to string
    """Remove a job from the careers page"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.isPublished = False  # NeonDB field name
    db.commit()
    db.refresh(job)
    return job


# ============== PUBLIC CAREERS PAGE ENDPOINTS ==============

@router.get("/public/careers", response_model=List[JobPublicResponse])
def get_careers_page_jobs(db: Session = Depends(get_db)):
    """
    Get all published jobs for the public careers page
    This endpoint is for your company website's careers page
    """
    jobs = db.query(Job).filter(
        Job.isPublished == True,  # NeonDB field name
        Job.isActive == True  # NeonDB field name
    ).order_by(Job.createdAt.desc()).all()
    
    return jobs


@router.get("/public/careers/{job_id}", response_model=JobPublicResponse)
def get_public_job_details(job_id: str, db: Session = Depends(get_db)):  # Changed to string
    """Get public job details for careers page"""
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.isPublished == True,  # NeonDB field name
        Job.isActive == True  # NeonDB field name
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job
