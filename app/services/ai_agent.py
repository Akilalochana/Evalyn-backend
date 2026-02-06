"""
AI Agent for CV Screening and Candidate Evaluation
Uses Google Gemini to analyze CVs against job requirements
"""
import json
from typing import List, Tuple
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from datetime import datetime


class AIScreeningAgent:
    """
    AI Agent that:
    1. Analyzes CVs against job requirements using Google Gemini
    2. Scores candidates based on match percentage
    3. Identifies strengths and gaps
    4. Shortlists candidates with 75% or above scores
    """
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
    
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
        Analyze CV against job requirements using Gemini AI
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
        
        prompt = f"""You are an expert HR recruiter AI. Analyze this candidate's CV against the job requirements and provide a detailed assessment.

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

Analyze the candidate and provide a comprehensive evaluation:

1. MATCH SCORE (0-100): Calculate how well this candidate matches the job requirements. Be objective and precise.
   - 90-100: Exceptional match, exceeds all requirements
   - 75-89: Strong match, meets or exceeds most requirements
   - 60-74: Good match, meets basic requirements with some gaps
   - 40-59: Partial match, has some relevant skills but significant gaps
   - 0-39: Poor match, lacks key requirements

2. SUMMARY: A brief 2-3 sentence summary of the candidate's profile and overall fit

3. STRENGTHS: Key matching qualifications and skills (provide as bullet points, be specific)

4. WEAKNESSES/GAPS: What's missing or concerning (provide as bullet points, be specific)

5. SKILLS MATCHED: List of specific technical skills, tools, or qualifications from the job requirements that the candidate has

**IMPORTANT**: Candidates scoring 75% or above are considered qualified and will be automatically selected for the next round.

Respond in this exact JSON format (no markdown, just pure JSON):
{{
    "score": <number 0-100>,
    "summary": "<summary text>",
    "strengths": "<bullet points of strengths>",
    "weaknesses": "<bullet points of weaknesses/gaps>",
    "skills_matched": ["skill1", "skill2", "skill3"]
}}

Be objective, thorough, and fair in your assessment. Focus on technical skills, experience level, and relevant background."""

        try:
            # Generate response using Gemini
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                # Remove ```json or ``` at start and ``` at end
                lines = response_text.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].strip() == "```":
                    lines = lines[:-1]
                response_text = '\n'.join(lines)
            
            # Parse JSON
            result = json.loads(response_text)
            
            # Validate and ensure all required fields are present
            required_fields = ["score", "summary", "strengths", "weaknesses", "skills_matched"]
            for field in required_fields:
                if field not in result:
                    result[field] = "" if field != "skills_matched" else []
            
            # Ensure score is a number
            result["score"] = float(result.get("score", 0))
            
            return result
        
        except Exception as e:
            print(f"AI analysis error: {e}")
            print(f"Response text: {response.text if 'response' in locals() else 'No response'}")
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
        Screen all pending applications for a job using Gemini AI
        - Analyzes each CV against job requirements
        - Scores candidates (0-100)
        - Automatically selects candidates with 75% or above
        - Returns top N candidates sorted by AI score
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
        
        print(f"📝 Starting AI screening for {len(applications)} applications...")
        
        # Screen each application
        for idx, app in enumerate(applications, 1):
            print(f"  [{idx}/{len(applications)}] Analyzing {app.full_name}...")
            
            # Extract CV text if not already done
            if not app.cv_text and app.cv_file_path:
                app.cv_text = self.extract_cv_text(app.cv_file_path)
            
            # Analyze with Gemini AI
            analysis = self.analyze_cv(app.cv_text or "", job)
            
            # Update application with results
            app.ai_score = analysis.get("score", 0)
            app.ai_summary = analysis.get("summary", "")
            app.ai_strengths = analysis.get("strengths", "")
            app.ai_weaknesses = analysis.get("weaknesses", "")
            app.skills_matched = json.dumps(analysis.get("skills_matched", []))
            app.status = ApplicationStatus.SCREENING.value
            app.screening_completed_at = datetime.utcnow()
            
            print(f"     ✓ Score: {app.ai_score}%")
        
        db.commit()
        
        # Sort by score and get top N
        sorted_apps = sorted(applications, key=lambda x: x.ai_score or 0, reverse=True)
        top_candidates = sorted_apps[:top_n]
        
        # IMPORTANT: Mark candidates with 75% or above as SHORTLISTED
        shortlisted_count = 0
        for app in top_candidates:
            if app.ai_score >= settings.MINIMUM_MATCH_SCORE:
                app.status = ApplicationStatus.SHORTLISTED.value
                shortlisted_count += 1
                print(f"  ✓ {app.full_name}: {app.ai_score}% - SELECTED (≥75%)")
            else:
                print(f"  ✗ {app.full_name}: {app.ai_score}% - Not selected (<75%)")
        
        # Mark others as rejected
        for app in sorted_apps[top_n:]:
            app.status = ApplicationStatus.REJECTED.value
            print(f"  ✗ {app.full_name}: {app.ai_score}% - REJECTED (not in top {top_n})")
        
        db.commit()
        
        print(f"\n✅ Screening complete: {shortlisted_count}/{len(top_candidates)} top candidates selected (≥75%)")
        
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
