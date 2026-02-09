"""
Evalyn AI Agent - Flask API for CV Screening
=============================================
Hosted on Render.com
Endpoints:
  POST /api/ai-review/run - Run AI CV screening for a job
  GET /health - Health check
"""
import os
import json
import smtplib
import requests
import pdfplumber
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company")

# Frontend URL for resolving relative paths (set this in Render environment)
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://evalyn.vercel.app")

# Initialize Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')


def get_db_connection():
    """Connect to NeonDB PostgreSQL"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_job_post(job_id: str) -> dict:
    """Get job post from database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('SELECT * FROM "JobPost" WHERE id = %s', (job_id,))
    job = cur.fetchone()
    
    cur.close()
    conn.close()
    return dict(job) if job else None


def get_applications(job_id: str) -> list:
    """Get applications for a job"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'JobApplication'
    """)
    columns = [row['column_name'] for row in cur.fetchall()]
    
    fk_column = 'jobPostId' if 'jobPostId' in columns else 'jobId' if 'jobId' in columns else None
    
    if job_id and fk_column:
        if 'status' in columns:
            cur.execute(f'SELECT * FROM "JobApplication" WHERE "{fk_column}" = %s AND (status = %s OR status IS NULL)', (job_id, 'pending'))
        else:
            cur.execute(f'SELECT * FROM "JobApplication" WHERE "{fk_column}" = %s', (job_id,))
    else:
        cur.execute('SELECT * FROM "JobApplication"')
    
    applications = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(app) for app in applications]


def resolve_url(url: str) -> str:
    """Resolve relative URLs to absolute URLs"""
    if not url:
        return ""
    
    # Already absolute URL
    if url.startswith("http://") or url.startswith("https://"):
        return url
    
    # Relative URL - prepend frontend URL
    if url.startswith("/"):
        return f"{FRONTEND_URL}{url}"
    
    return f"{FRONTEND_URL}/{url}"


def download_pdf_text(pdf_url: str) -> str:
    """Download PDF and extract text"""
    try:
        # Resolve relative URLs
        full_url = resolve_url(pdf_url)
        if not full_url:
            return ""
        
        print(f"  Downloading PDF: {full_url[:80]}...")
        response = requests.get(full_url, timeout=30)
        response.raise_for_status()
        
        pdf_bytes = BytesIO(response.content)
        text = ""
        
        with pdfplumber.open(pdf_bytes) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""


def analyze_cv_with_ai(cv_text: str, job: dict) -> dict:
    """Analyze CV against job using Gemini AI"""
    import time
    
    if not cv_text:
        return {"score": 0, "summary": "Could not read CV"}
    
    job_info = f"Title: {job.get('title', 'N/A')}\n"
    job_info += f"Description: {job.get('description', 'N/A')}\n"
    
    requirements = job.get('requirements', '')
    if isinstance(requirements, list):
        requirements = '\n'.join(requirements)
    job_info += f"Requirements: {requirements}\n"
    
    prompt = f"""You are an HR expert. Score this CV against the job requirements.

JOB:
{job_info}

CV:
{cv_text[:6000]}

Return ONLY a JSON object (no markdown, no explanation):
{{"score": <0-100>, "summary": "<one sentence why>"}}
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            if text.startswith("```"):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            result = json.loads(text)
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = 35 * (attempt + 1)
                time.sleep(wait_time)
                continue
            else:
                return {"score": 0, "summary": str(e)[:100]}
    
    return {"score": 0, "summary": "Rate limit exceeded"}


def send_email(to_email: str, candidate_name: str, job_title: str) -> bool:
    """Send congratulations email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"Congratulations! You've been shortlisted for {job_title}"
        
        body = f"""
Dear {candidate_name},

Congratulations! We are pleased to inform you that you have been shortlisted for the position of {job_title} at {COMPANY_NAME}.

Your application stood out among many candidates, and we would like to invite you for the next round of our selection process.

Our HR team will contact you shortly with further details about the interview schedule.

Best regards,
HR Team
{COMPANY_NAME}
"""
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False


def update_application_status(app_id: str, status: str):
    """Update application status in database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'JobApplication' AND column_name = 'status'
        """)
        
        if cur.fetchone():
            cur.execute('UPDATE "JobApplication" SET status = %s WHERE id = %s', (status, app_id))
            conn.commit()
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Status update error: {e}")


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "Evalyn AI Agent"})


@app.route('/api/ai-review/run', methods=['POST'])
def run_ai_review():
    """Run AI CV screening for a job"""
    try:
        data = request.get_json()
        job_id = data.get('jobId')
        
        if not job_id:
            return jsonify({"success": False, "message": "Job ID is required"}), 400
        
        # Step 1: Get Job
        job = get_job_post(job_id)
        if not job:
            return jsonify({"success": False, "message": f"Job not found: {job_id}"}), 404
        
        # Step 2: Get Applications
        applications = get_applications(job_id)
        if not applications:
            return jsonify({
                "success": True,
                "data": {
                    "totalScreened": 0,
                    "topSelected": 0,
                    "emailsSent": 0,
                    "topCandidates": []
                }
            })
        
        # Step 3: Screen each CV
        results = []
        for app in applications:
            name = app.get('name') or app.get('fullName') or 'Unknown'
            email = app.get('email') or 'no-email'
            resume_url = app.get('resumeUrl') or app.get('resume_url') or ''
            
            cv_text = download_pdf_text(resume_url) if resume_url else ""
            analysis = analyze_cv_with_ai(cv_text, job)
            
            results.append({
                'id': app.get('id'),
                'name': name,
                'email': email,
                'score': analysis.get('score', 0),
                'summary': analysis.get('summary', '')
            })
        
        # Step 4: Sort and get top 10
        results.sort(key=lambda x: x['score'], reverse=True)
        top_10 = results[:10]
        
        # Send emails
        emails_sent = 0
        for candidate in top_10:
            if candidate['email'] and candidate['email'] != 'no-email':
                if send_email(candidate['email'], candidate['name'], job.get('title', 'Position')):
                    emails_sent += 1
                    update_application_status(candidate['id'], 'shortlisted')
        
        return jsonify({
            "success": True,
            "message": "AI review completed",
            "data": {
                "totalScreened": len(applications),
                "topSelected": len(top_10),
                "emailsSent": emails_sent,
                "topCandidates": top_10
            }
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
