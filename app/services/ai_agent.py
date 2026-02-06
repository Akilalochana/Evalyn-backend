"""
AI Agent for CV Screening and Candidate Evaluation
Uses OpenAI to analyze CVs against job requirements
"""
import json
from typing import List, Tuple
from openai import OpenAI
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from datetime import datetime


class AIScreeningAgent:
    """
    AI Agent that:
    1. Analyzes CVs against job requirements
    2. Scores candidates based on match percentage
    3. Identifies strengths and gaps
    4. Shortlists top candidates
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # Use GPT-4o for better analysis
    
    def extract_cv_text(self, file_path: str) -> str:
        """Extract text from CV file (PDF or DOCX)"""
        import os
        
        if not file_path or not os.path.exists(file_path):
            return ""
        
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".pdf":
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            
            elif ext in [".docx", ".doc"]:
                from docx import Document
                doc = Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            
            elif ext == ".txt":
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            
            else:
                return ""
        except Exception as e:
            print(f"Error extracting CV text: {e}")
            return ""
    
    def analyze_cv(self, cv_text: str, job: Job) -> dict:
        """
        Analyze CV against job requirements using AI
        Returns: dict with score, summary, strengths, weaknesses, matched skills
        """
        if not cv_text:
            return {
                "score": 0,
                "summary": "Could not extract CV content",
                "strengths": "",
                "weaknesses": "No CV content available",
                "skills_matched": []
            }
        
        prompt = f"""You are an expert HR recruiter AI. Analyze this candidate's CV against the job requirements.

JOB DETAILS:
Title: {job.title}
Department: {job.department or 'Not specified'}
Experience Required: {job.min_experience_years}-{job.max_experience_years} years
Level: {job.experience_level or 'Not specified'}

JOB DESCRIPTION:
{job.description}

REQUIREMENTS:
{job.requirements}

RESPONSIBILITIES:
{job.responsibilities or 'Not specified'}

---

CANDIDATE CV:
{cv_text[:8000]}  # Limit to avoid token limits

---

Analyze the candidate and provide:
1. MATCH SCORE (0-100): How well does this candidate match the job requirements?
2. SUMMARY: A brief 2-3 sentence summary of the candidate's profile
3. STRENGTHS: Key matching qualifications and skills (bullet points)
4. WEAKNESSES/GAPS: What's missing or concerning (bullet points)
5. SKILLS MATCHED: List of specific skills from job requirements that candidate has

Respond in this exact JSON format:
{{
    "score": <number 0-100>,
    "summary": "<summary text>",
    "strengths": "<bullet points of strengths>",
    "weaknesses": "<bullet points of weaknesses/gaps>",
    "skills_matched": ["skill1", "skill2", "skill3"]
}}

Be objective and thorough. Focus on technical skills, experience level, and relevant background."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert HR recruiter AI assistant. Analyze candidates objectively and provide structured evaluations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
        
        except Exception as e:
            print(f"AI analysis error: {e}")
            return {
                "score": 0,
                "summary": f"Error during AI analysis: {str(e)}",
                "strengths": "",
                "weaknesses": "",
                "skills_matched": []
            }
    
    def screen_applications(
        self, 
        db: Session, 
        job_id: int, 
        top_n: int = None
    ) -> List[Application]:
        """
        Screen all pending applications for a job
        Returns top N candidates sorted by AI score
        """
        if top_n is None:
            top_n = settings.CV_SCREENING_TOP_CANDIDATES
        
        # Get job details
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job with id {job_id} not found")
        
        # Get all pending applications
        applications = db.query(Application).filter(
            Application.job_id == job_id,
            Application.status == ApplicationStatus.PENDING.value
        ).all()
        
        if not applications:
            return []
        
        # Screen each application
        for app in applications:
            # Extract CV text if not already done
            if not app.cv_text and app.cv_file_path:
                app.cv_text = self.extract_cv_text(app.cv_file_path)
            
            # Analyze with AI
            analysis = self.analyze_cv(app.cv_text or "", job)
            
            # Update application with results
            app.ai_score = analysis.get("score", 0)
            app.ai_summary = analysis.get("summary", "")
            app.ai_strengths = analysis.get("strengths", "")
            app.ai_weaknesses = analysis.get("weaknesses", "")
            app.skills_matched = json.dumps(analysis.get("skills_matched", []))
            app.status = ApplicationStatus.SCREENING.value
            app.screening_completed_at = datetime.utcnow()
        
        db.commit()
        
        # Sort by score and get top N
        sorted_apps = sorted(applications, key=lambda x: x.ai_score or 0, reverse=True)
        top_candidates = sorted_apps[:top_n]
        
        # Mark top candidates as shortlisted
        for app in top_candidates:
            if app.ai_score >= settings.MINIMUM_MATCH_SCORE:
                app.status = ApplicationStatus.SHORTLISTED.value
        
        # Mark others as rejected
        for app in sorted_apps[top_n:]:
            app.status = ApplicationStatus.REJECTED.value
        
        db.commit()
        
        return top_candidates
    
    def get_candidate_summary(self, application: Application) -> str:
        """Generate a brief summary for interview preparation"""
        return f"""
Candidate: {application.full_name}
Email: {application.email}
Phone: {application.phone or 'N/A'}
Match Score: {application.ai_score}%

AI Summary: {application.ai_summary}

Strengths:
{application.ai_strengths}

Areas to Probe:
{application.ai_weaknesses}

Skills Matched: {application.skills_matched}
"""


# Singleton instance
ai_agent = AIScreeningAgent()
