"""
Enhanced Screening API Endpoints
Provides bias-aware screening, skill-gap analysis, and project evaluation
"""
import os
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.job import Job
from app.models.application import Application
from app.services.bias_detection_service import bias_detection_service
from app.services.skill_gap_analyzer import skill_gap_analyzer
from app.services.project_evaluator import project_evaluator


router = APIRouter(prefix="/enhanced-screening", tags=["Enhanced Screening"])


# ============== BIAS-AWARE SCREENING ==============

@router.post("/bias-analysis/{application_id}")
def perform_bias_analysis(
    application_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform bias-aware screening on an application
    - Masks personal data (name, age, gender, university)
    - Performs blind evaluation
    - Performs full evaluation
    - Calculates bias delta
    - Stores results
    
    Returns detailed bias analysis
    """
    # Get application
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    print(f"\n🔍 BIAS-AWARE SCREENING: {application.full_name}")
    print("=" * 60)
    
    # Perform bias analysis
    result = bias_detection_service.perform_bias_analysis(
        cv_text=application.cv_text or "",
        job=job,
        candidate_name=application.full_name
    )
    
    # Store results in database
    application.blind_score = result["blind_score"]
    application.full_score = result["full_score"]
    application.bias_delta = result["bias_delta"]
    application.blind_evaluation = json.dumps(result["blind_evaluation"])
    application.full_evaluation = json.dumps(result["full_evaluation"])
    application.bias_analysis = json.dumps(result["bias_analysis"])
    
    db.commit()
    
    return {
        "application_id": application_id,
        "candidate_name": application.full_name,
        "blind_score": result["blind_score"],
        "full_score": result["full_score"],
        "bias_delta": result["bias_delta"],
        "bias_analysis": result["bias_analysis"],
        "recommendation": result["bias_analysis"]["recommendation"]
    }


@router.post("/bulk-bias-analysis/job/{job_id}")
def bulk_bias_analysis(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform bias-aware screening on all shortlisted candidates for a job
    
    Returns summary of bias analysis for all candidates
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get all shortlisted or screened applications
    applications = db.query(Application).filter(
        Application.job_id == job_id,
        Application.status.in_(["shortlisted", "screening"])
    ).all()
    
    if not applications:
        return {"message": "No applications to analyze", "results": []}
    
    results = []
    
    for app in applications:
        print(f"\n🔍 Analyzing: {app.full_name}")
        
        result = bias_detection_service.perform_bias_analysis(
            cv_text=app.cv_text or "",
            job=job,
            candidate_name=app.full_name
        )
        
        # Store in database
        app.blind_score = result["blind_score"]
        app.full_score = result["full_score"]
        app.bias_delta = result["bias_delta"]
        app.blind_evaluation = json.dumps(result["blind_evaluation"])
        app.full_evaluation = json.dumps(result["full_evaluation"])
        app.bias_analysis = json.dumps(result["bias_analysis"])
        
        results.append({
            "application_id": app.id,
            "candidate_name": app.full_name,
            "blind_score": result["blind_score"],
            "full_score": result["full_score"],
            "bias_delta": result["bias_delta"],
            "bias_detected": result["bias_analysis"]["bias_detected"],
            "bias_severity": result["bias_analysis"]["bias_severity"]
        })
    
    db.commit()
    
    return {
        "job_id": job_id,
        "total_analyzed": len(results),
        "results": results,
        "summary": {
            "high_bias_detected": sum(1 for r in results if abs(r["bias_delta"]) >= 12),
            "moderate_bias_detected": sum(1 for r in results if 7 <= abs(r["bias_delta"]) < 12),
            "low_bias": sum(1 for r in results if abs(r["bias_delta"]) < 7)
        }
    }


# ============== SKILL-GAP ANALYSIS ==============

@router.post("/skill-gap-analysis/{application_id}")
def perform_skill_gap_analysis(
    application_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform skill-gap analysis on an application
    - Extracts required skills from job
    - Extracts candidate skills from CV
    - Identifies matched, missing, and weak skills
    - Generates personalized feedback
    - Stores results
    
    Returns detailed skill-gap analysis and feedback
    """
    # Get application
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    print(f"\n📊 SKILL-GAP ANALYSIS: {application.full_name}")
    print("=" * 60)
    
    # Perform analysis
    result = skill_gap_analyzer.perform_complete_analysis(
        cv_text=application.cv_text or "",
        job=job,
        candidate_name=application.full_name
    )
    
    # Store results in database
    application.required_skills = json.dumps(result["required_skills"])
    application.candidate_skills = json.dumps(result["candidate_skills"])
    application.missing_skills = json.dumps(result["missing_skills"])
    application.weak_skills = json.dumps(result["weak_skills"])
    application.skill_gap_feedback = result["feedback"]
    application.skill_match_percentage = result["skill_match_percentage"]
    
    db.commit()
    
    return {
        "application_id": application_id,
        "candidate_name": application.full_name,
        "skill_match_percentage": result["skill_match_percentage"],
        "matched_skills": result["matched_skills"],
        "missing_skills": result["missing_skills"],
        "weak_skills": result["weak_skills"],
        "extra_skills": result["extra_skills"],
        "feedback": result["feedback"]
    }


@router.post("/bulk-skill-gap-analysis/job/{job_id}")
def bulk_skill_gap_analysis(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform skill-gap analysis on all candidates for a job
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    applications = db.query(Application).filter(
        Application.job_id == job_id
    ).all()
    
    if not applications:
        return {"message": "No applications to analyze", "results": []}
    
    results = []
    
    for app in applications:
        print(f"\n📊 Analyzing: {app.full_name}")
        
        result = skill_gap_analyzer.perform_complete_analysis(
            cv_text=app.cv_text or "",
            job=job,
            candidate_name=app.full_name
        )
        
        # Store in database
        app.required_skills = json.dumps(result["required_skills"])
        app.candidate_skills = json.dumps(result["candidate_skills"])
        app.missing_skills = json.dumps(result["missing_skills"])
        app.weak_skills = json.dumps(result["weak_skills"])
        app.skill_gap_feedback = result["feedback"]
        app.skill_match_percentage = result["skill_match_percentage"]
        
        results.append({
            "application_id": app.id,
            "candidate_name": app.full_name,
            "skill_match_percentage": result["skill_match_percentage"],
            "total_required": len(result["required_skills"]),
            "total_matched": len(result["matched_skills"]),
            "total_missing": len(result["missing_skills"])
        })
    
    db.commit()
    
    return {
        "job_id": job_id,
        "total_analyzed": len(results),
        "results": sorted(results, key=lambda x: x["skill_match_percentage"], reverse=True)
    }


# ============== PROJECT EVALUATION ==============

@router.post("/project-evaluation/{application_id}")
def evaluate_project(
    application_id: int,
    github_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Evaluate candidate's project (GitHub repository)
    - Clones repository
    - Analyzes code structure
    - Evaluates code quality
    - Generates project score
    - Calculates composite score (CV + Project)
    
    Returns project evaluation and updated composite score
    """
    # Get application
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Use provided GitHub URL or the one stored in application
    project_url = github_url or application.github_url
    
    if not project_url:
        raise HTTPException(
            status_code=400,
            detail="GitHub URL not provided. Include github_url in form data."
        )
    
    print(f"\n🚀 PROJECT EVALUATION: {application.full_name}")
    print(f"Repository: {project_url}")
    print("=" * 60)
    
    # Evaluate project
    result = project_evaluator.evaluate_github_project(
        github_url=project_url,
        job_title=job.title,
        application_id=application_id
    )
    
    # Store results
    application.github_url = project_url
    application.project_file_path = result.get("project_path")
    application.project_score = result["project_score"]
    application.code_quality_score = result["code_quality_score"]
    application.project_feedback = result["project_feedback"]
    application.project_analysis = json.dumps(result.get("project_analysis", {}))
    
    # Calculate composite score
    cv_score = application.ai_score or 0
    composite_score = project_evaluator.calculate_composite_score(
        cv_score=cv_score,
        project_score=result["project_score"]
    )
    application.final_composite_score = composite_score
    
    db.commit()
    
    print(f"\n✅ RESULTS:")
    print(f"   CV Score: {cv_score:.1f}%")
    print(f"   Project Score: {result['project_score']:.1f}%")
    print(f"   Composite Score: {composite_score:.1f}%")
    
    return {
        "application_id": application_id,
        "candidate_name": application.full_name,
        "cv_score": cv_score,
        "project_score": result["project_score"],
        "code_quality_score": result["code_quality_score"],
        "composite_score": composite_score,
        "project_feedback": result["project_feedback"],
        "project_analysis": result.get("project_analysis", {})
    }


@router.get("/enhanced-results/{application_id}")
def get_enhanced_results(
    application_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all enhanced screening results for an application
    - Bias analysis
    - Skill-gap analysis
    - Project evaluation
    - Composite scores
    """
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Parse JSON fields
    def safe_json_parse(text):
        try:
            return json.loads(text) if text else None
        except:
            return None
    
    return {
        "application_id": application_id,
        "candidate_name": application.full_name,
        "email": application.email,
        
        # Original screening
        "ai_score": application.ai_score,
        "ai_summary": application.ai_summary,
        
        # Bias-aware screening
        "bias_analysis": {
            "blind_score": application.blind_score,
            "full_score": application.full_score,
            "bias_delta": application.bias_delta,
            "bias_analysis": safe_json_parse(application.bias_analysis)
        } if application.blind_score else None,
        
        # Skill-gap analysis
        "skill_gap_analysis": {
            "skill_match_percentage": application.skill_match_percentage,
            "matched_skills": safe_json_parse(application.skills_matched),
            "missing_skills": safe_json_parse(application.missing_skills),
            "weak_skills": safe_json_parse(application.weak_skills),
            "feedback": application.skill_gap_feedback
        } if application.skill_match_percentage else None,
        
        # Project evaluation
        "project_evaluation": {
            "github_url": application.github_url,
            "project_score": application.project_score,
            "code_quality_score": application.code_quality_score,
            "feedback": application.project_feedback,
            "analysis": safe_json_parse(application.project_analysis)
        } if application.project_score else None,
        
        # Final composite score
        "final_composite_score": application.final_composite_score
    }


@router.post("/complete-enhanced-screening/{application_id}")
def complete_enhanced_screening(
    application_id: int,
    github_url: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Perform ALL enhanced screening analyses at once:
    1. Bias-aware screening
    2. Skill-gap analysis
    3. Project evaluation (if GitHub URL provided)
    
    Returns complete enhanced screening report
    """
    application = db.query(Application).filter(
        Application.id == application_id
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    print(f"\n🚀 COMPLETE ENHANCED SCREENING: {application.full_name}")
    print("=" * 70)
    
    results = {}
    
    # 1. Bias-aware screening
    print("\n1️⃣ BIAS-AWARE SCREENING")
    bias_result = bias_detection_service.perform_bias_analysis(
        cv_text=application.cv_text or "",
        job=job,
        candidate_name=application.full_name
    )
    application.blind_score = bias_result["blind_score"]
    application.full_score = bias_result["full_score"]
    application.bias_delta = bias_result["bias_delta"]
    application.blind_evaluation = json.dumps(bias_result["blind_evaluation"])
    application.full_evaluation = json.dumps(bias_result["full_evaluation"])
    application.bias_analysis = json.dumps(bias_result["bias_analysis"])
    results["bias_analysis"] = bias_result["bias_analysis"]
    
    # 2. Skill-gap analysis
    print("\n2️⃣ SKILL-GAP ANALYSIS")
    skill_result = skill_gap_analyzer.perform_complete_analysis(
        cv_text=application.cv_text or "",
        job=job,
        candidate_name=application.full_name
    )
    application.required_skills = json.dumps(skill_result["required_skills"])
    application.candidate_skills = json.dumps(skill_result["candidate_skills"])
    application.missing_skills = json.dumps(skill_result["missing_skills"])
    application.weak_skills = json.dumps(skill_result["weak_skills"])
    application.skill_gap_feedback = skill_result["feedback"]
    application.skill_match_percentage = skill_result["skill_match_percentage"]
    results["skill_gap"] = {
        "match_percentage": skill_result["skill_match_percentage"],
        "matched": len(skill_result["matched_skills"]),
        "missing": len(skill_result["missing_skills"])
    }
    
    # 3. Project evaluation (if GitHub URL provided)
    if github_url or application.github_url:
        print("\n3️⃣ PROJECT EVALUATION")
        project_url = github_url or application.github_url
        project_result = project_evaluator.evaluate_github_project(
            github_url=project_url,
            job_title=job.title,
            application_id=application_id
        )
        application.github_url = project_url
        application.project_file_path = project_result.get("project_path")
        application.project_score = project_result["project_score"]
        application.code_quality_score = project_result["code_quality_score"]
        application.project_feedback = project_result["project_feedback"]
        application.project_analysis = json.dumps(project_result.get("project_analysis", {}))
        
        # Calculate composite score
        composite = project_evaluator.calculate_composite_score(
            cv_score=application.ai_score or 0,
            project_score=project_result["project_score"]
        )
        application.final_composite_score = composite
        results["project"] = {
            "score": project_result["project_score"],
            "composite_score": composite
        }
    
    db.commit()
    
    print("\n" + "=" * 70)
    print("✅ COMPLETE ENHANCED SCREENING FINISHED")
    
    return {
        "application_id": application_id,
        "candidate_name": application.full_name,
        "results": results,
        "final_composite_score": application.final_composite_score
    }
