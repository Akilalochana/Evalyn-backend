"""
AI Agent for CV Screening and Candidate Evaluation
Uses Google Gemini Flash to analyze CVs against job requirements
Supports Vercel Blob storage for PDF resumes
"""
import json
import uuid
from typing import List, Tuple, Optional
import google.generativeai as genai
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.interview import Interview, InterviewRound, InterviewStatus
from app.services.vercel_blob_service import vercel_blob_service
from datetime import datetime, timedelta


class AIScreeningAgent:
    """
    AI Agent that:
    1. Downloads CVs from Vercel Blob storage
    2. Analyzes CVs against job requirements using Google Gemini Flash
    3. Scores candidates based on match percentage
    4. Identifies strengths and gaps
    5. Shortlists candidates with 75% or above scores (Top 10)
    6. Sends emails to shortlisted candidates
    7. Schedules Round 2 interviews with SSE
    """
    
    def __init__(self):
        # Configure Gemini API with Flash model (free tier)
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,  # gemini-1.5-flash
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
            }
        )
    
    def extract_cv_text(self, file_path_or_url: str) -> str:
        """
        Extract text from CV file
        Supports:
        - Vercel Blob URLs (https://...)
        - Local file paths (for backward compatibility)
        - Relative API paths (/api/uploads/...)
        """
        import os
        
        if not file_path_or_url:
            return ""
        
        # Skip NULL values
        if file_path_or_url.upper() == "NULL":
            return ""
        
        # Check if it's a Vercel Blob URL or any HTTP URL
        if file_path_or_url.startswith('http') or file_path_or_url.startswith('/api/'):
            # Use Vercel Blob service to download and extract
            return vercel_blob_service.get_cv_text_from_url(file_path_or_url)
        
        # Local file handling (backward compatibility)
        if not os.path.exists(file_path_or_url):
            return ""
        
        ext = os.path.splitext(file_path_or_url)[1].lower()
        
        try:
            if ext == ".pdf":
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path_or_url) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                return text
            
            elif ext in [".docx", ".doc"]:
                from docx import Document
                doc = Document(file_path_or_url)
                return "\n".join([para.text for para in doc.paragraphs])
            
            elif ext == ".txt":
                with open(file_path_or_url, "r", encoding="utf-8") as f:
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
        job_id: str, 
        top_n: int = None
    ) -> List[Application]:
        """
        Screen all pending applications for a job using Gemini AI
        - Downloads CVs from Vercel Blob storage
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
            Application.jobId == job_id,
            Application.status == ApplicationStatus.PENDING.value
        ).all()
        
        if not applications:
            return []
        
        print(f"[INFO] Starting AI screening for {len(applications)} applications...")
        
        # Store screening results in memory (NeonDB may not have these columns)
        screening_results = {}
        
        # Screen each application
        for idx, app in enumerate(applications, 1):
            print(f"  [{idx}/{len(applications)}] Analyzing {app.name}...")
            
            # Extract CV text from Vercel Blob URL
            cv_text = ""
            if app.resumeUrl:
                cv_text = self.extract_cv_text(app.resumeUrl)
            
            # Analyze with Gemini AI
            analysis = self.analyze_cv(cv_text, job)
            
            # Store results in memory (not in DB - columns may not exist)
            score = analysis.get("score", 0)
            screening_results[app.id] = {
                "score": score,
                "summary": analysis.get("summary", ""),
                "strengths": analysis.get("strengths", ""),
                "weaknesses": analysis.get("weaknesses", ""),
                "skills_matched": analysis.get("skills_matched", []),
                "cv_text": cv_text
            }
            
            # Set transient attributes for later use
            app._ai_score = score
            app._ai_summary = analysis.get("summary", "")
            app._ai_strengths = analysis.get("strengths", "")
            app._ai_weaknesses = analysis.get("weaknesses", "")
            app._skills_matched = json.dumps(analysis.get("skills_matched", []))
            app._cv_text = cv_text
            
            print(f"     [OK] Score: {score}%")
        
        # Sort by score and get top N
        sorted_apps = sorted(applications, key=lambda x: screening_results.get(x.id, {}).get("score", 0), reverse=True)
        top_candidates = sorted_apps[:top_n]
        
        # IMPORTANT: Mark candidates with 75% or above as SHORTLISTED
        # Only update the 'status' column which exists in NeonDB
        shortlisted_count = 0
        for app in top_candidates:
            score = screening_results.get(app.id, {}).get("score", 0)
            if score >= settings.MINIMUM_MATCH_SCORE:
                app.status = ApplicationStatus.SHORTLISTED.value
                shortlisted_count += 1
                print(f"  [+] {app.name}: {score}% - SELECTED (>=75%)")
            else:
                print(f"  [-] {app.name}: {score}% - Not selected (<75%)")
        
        # Mark others as rejected  
        for app in sorted_apps[top_n:]:
            score = screening_results.get(app.id, {}).get("score", 0)
            app.status = ApplicationStatus.REJECTED.value
            print(f"  [-] {app.name}: {score}% - REJECTED (not in top {top_n})")
        
        db.commit()
        
        print(f"\n[DONE] Screening complete: {shortlisted_count}/{len(top_candidates)} top candidates selected (>=75%)")
        
        return top_candidates
    
    def get_candidate_summary(self, application: Application) -> str:
        """Generate a brief summary for interview preparation"""
        score = getattr(application, '_ai_score', 0)
        summary = getattr(application, '_ai_summary', 'N/A')
        strengths = getattr(application, '_ai_strengths', 'N/A')
        weaknesses = getattr(application, '_ai_weaknesses', 'N/A')
        skills = getattr(application, '_skills_matched', '[]')
        
        return f"""
Candidate: {application.name}
Email: {application.email}
Phone: {application.phone or 'N/A'}
Match Score: {score}%

AI Summary: {summary}

Strengths:
{strengths}

Areas to Probe:
{weaknesses}

Skills Matched: {skills}
"""
    
    def run_full_hr_workflow(
        self,
        db: Session,
        job_id: str,
        sse_name: str = None,
        sse_email: str = None,
        interview_start_datetime: datetime = None
    ) -> dict:
        """
        Run the complete HR automation workflow:
        1. Screen all pending applications with AI
        2. Shortlist top 10 candidates (≥75% score)
        3. Send emails to shortlisted candidates (Round 1 passed)
        4. Schedule Round 2 interviews with SSE
        5. Send interview invitations
        
        Returns: Summary of actions taken
        """
        from app.services.email_service import email_service
        
        # Use defaults if not provided
        sse_name = sse_name or settings.DEFAULT_SSE_NAME
        sse_email = sse_email or settings.DEFAULT_SSE_EMAIL
        
        # Default interview time: next business day at 9 AM
        if interview_start_datetime is None:
            tomorrow = datetime.now() + timedelta(days=1)
            # Skip to Monday if weekend
            while tomorrow.weekday() >= 5:  # 5=Saturday, 6=Sunday
                tomorrow += timedelta(days=1)
            interview_start_datetime = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        
        result = {
            "job_id": job_id,
            "workflow_started_at": datetime.utcnow().isoformat(),
            "steps": []
        }
        
        # Step 1: Screen applications
        print("\n[STEP 1] AI Screening of Applications")
        print("=" * 50)
        
        try:
            shortlisted = self.screen_applications(db, job_id)
            result["steps"].append({
                "step": 1,
                "action": "AI Screening",
                "status": "completed",
                "candidates_screened": len(shortlisted),
                "shortlisted": len([a for a in shortlisted if a.status == ApplicationStatus.SHORTLISTED.value])
            })
        except Exception as e:
            result["steps"].append({
                "step": 1,
                "action": "AI Screening",
                "status": "failed",
                "error": str(e)
            })
            return result
        
        # Get shortlisted candidates (no order_by since ai_score is not in DB)
        shortlisted_apps = db.query(Application).filter(
            Application.jobId == job_id,
            Application.status == ApplicationStatus.SHORTLISTED.value
        ).all()
        
        if not shortlisted_apps:
            result["message"] = "No candidates met the minimum score threshold (75%)"
            return result
        
        # Step 2: Send shortlist notification emails
        print("\n[STEP 2] Sending Shortlist Notifications")
        print("=" * 50)
        
        job = db.query(Job).filter(Job.id == job_id).first()
        email_results = email_service.send_bulk_shortlist_notifications(shortlisted_apps, job)
        
        # Update status to round1_passed
        for app in shortlisted_apps:
            app.status = ApplicationStatus.ROUND1_PASSED.value
        db.commit()
        
        result["steps"].append({
            "step": 2,
            "action": "Send Shortlist Emails",
            "status": "completed",
            "emails_sent": email_results["success"],
            "emails_failed": email_results["failed"]
        })
        
        # Step 3: Schedule Round 2 interviews
        print("\n[STEP 3] Scheduling Round 2 Interviews with SSE")
        print("=" * 50)
        
        interviews_scheduled = []
        current_time = interview_start_datetime
        
        for app in shortlisted_apps:
            # Generate unique interview ID
            interview_id = str(uuid.uuid4())[:25]
            
            # Create interview
            interview = Interview(
                id=interview_id,
                applicationId=app.id,
                round=InterviewRound.ROUND2.value,
                interviewerName=sse_name,
                interviewerEmail=sse_email,
                scheduledAt=current_time,
                durationMinutes=settings.INTERVIEW_DURATION_MINUTES,
                meetingLink=f"https://meet.google.com/ai-hr-{interview_id[:8]}",  # Placeholder
                status=InterviewStatus.SCHEDULED.value
            )
            
            db.add(interview)
            
            # Update application status
            app.status = ApplicationStatus.ROUND2_SCHEDULED.value
            
            # Send interview invitation email
            email_service.send_interview_invitation(app, interview, job)
            
            interviews_scheduled.append({
                "candidate": app.name,
                "email": app.email,
                "scheduled_at": current_time.isoformat(),
                "interviewer": sse_name
            })
            
            print(f"  [+] Scheduled: {app.name} at {current_time}")
            
            # Move to next time slot
            current_time += timedelta(
                minutes=settings.INTERVIEW_DURATION_MINUTES + settings.INTERVIEW_GAP_MINUTES
            )
        
        db.commit()
        
        result["steps"].append({
            "step": 3,
            "action": "Schedule Interviews",
            "status": "completed",
            "interviews_scheduled": len(interviews_scheduled),
            "details": interviews_scheduled
        })
        
        result["workflow_completed_at"] = datetime.utcnow().isoformat()
        result["message"] = f"Successfully processed {len(shortlisted_apps)} candidates"
        
        print("\n" + "=" * 50)
        print("[DONE] HR AUTOMATION WORKFLOW COMPLETED!")
        print(f"   - Candidates screened and shortlisted: {len(shortlisted_apps)}")
        print(f"   - Notification emails sent: {email_results['success']}")
        print(f"   - Interviews scheduled: {len(interviews_scheduled)}")
        print("=" * 50)
        
        return result


# Singleton instance
ai_agent = AIScreeningAgent()
