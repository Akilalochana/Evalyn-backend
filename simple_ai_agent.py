"""
Simple AI Agent for CV Screening
================================
Just 3 steps:
1. Get job post details
2. Screen all CVs with Gemini AI
3. Send emails to top 10

Run: python simple_ai_agent.py <job_id>
"""
import os
import json
import smtplib
import requests
import pdfplumber
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company")

# Initialize Gemini - try different models if quota exceeded
genai.configure(api_key=GEMINI_API_KEY)
# Use gemini-2.5-flash-lite for better free tier limits
model = genai.GenerativeModel('gemini-2.5-flash-lite')


def get_db_connection():
    """Connect to NeonDB PostgreSQL"""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def get_job_post(job_id: str) -> dict:
    """Get job post from database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get column names first
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'JobPost'
    """)
    columns = [row['column_name'] for row in cur.fetchall()]
    print(f"JobPost columns: {columns}")
    
    # Get job
    cur.execute('SELECT * FROM "JobPost" WHERE id = %s', (job_id,))
    job = cur.fetchone()
    
    cur.close()
    conn.close()
    return dict(job) if job else None


def get_applications(job_id: str = None) -> list:
    """Get applications from database, optionally filtered by job ID"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get column names first
    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'JobApplication'
    """)
    columns = [row['column_name'] for row in cur.fetchall()]
    print(f"JobApplication columns: {columns}")
    
    # Check which foreign key column exists
    fk_column = 'jobPostId' if 'jobPostId' in columns else 'jobId' if 'jobId' in columns else None
    
    # Get applications filtered by job if possible
    if job_id and fk_column:
        if 'status' in columns:
            cur.execute(f'SELECT * FROM "JobApplication" WHERE "{fk_column}" = %s AND (status = %s OR status IS NULL)', (job_id, 'pending'))
        else:
            cur.execute(f'SELECT * FROM "JobApplication" WHERE "{fk_column}" = %s', (job_id,))
    else:
        # Get all applications
        if 'status' in columns:
            cur.execute('SELECT * FROM "JobApplication" WHERE status = %s OR status IS NULL', ('pending',))
        else:
            cur.execute('SELECT * FROM "JobApplication"')
    
    applications = cur.fetchall()
    
    cur.close()
    conn.close()
    return [dict(app) for app in applications]


def download_pdf_text(pdf_url: str) -> str:
    """Download PDF from Vercel Blob and extract text"""
    try:
        print(f"  Downloading: {pdf_url[:50]}...")
        response = requests.get(pdf_url, timeout=30)
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
        print(f"  Error extracting PDF: {e}")
        return ""


def analyze_cv_with_ai(cv_text: str, job: dict) -> dict:
    """Analyze CV against job using Gemini AI with retry"""
    import time
    
    if not cv_text:
        return {"score": 0, "summary": "Could not read CV"}
    
    # Build job description from whatever columns exist
    job_info = f"Title: {job.get('title', 'N/A')}\n"
    job_info += f"Description: {job.get('description', 'N/A')}\n"
    
    # Add requirements if it exists (could be string or array)
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

    # Retry logic for quota limits
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean markdown if present
            if text.startswith("```"):
                lines = text.split('\n')
                text = '\n'.join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
            result = json.loads(text)
            return result
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                wait_time = 35 * (attempt + 1)  # 35s, 70s, 105s
                print(f"  Rate limited. Waiting {wait_time}s... (attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                print(f"  AI Error: {error_str[:100]}")
                return {"score": 0, "summary": error_str[:100]}
    
    return {"score": 0, "summary": "Rate limit exceeded after retries"}


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
        print(f"  Email Error: {e}")
        return False


def update_application_status(app_id: str, status: str):
    """Update application status in database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if status column exists
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
        print(f"  Status update error: {e}")


def run_ai_agent(job_id: str):
    """
    Main function - Run the AI screening workflow
    """
    print("\n" + "="*60)
    print("AI CV SCREENING AGENT")
    print("="*60)
    
    # Step 1: Get Job
    print(f"\n[1/4] Getting job post: {job_id}")
    job = get_job_post(job_id)
    
    if not job:
        print(f"ERROR: Job not found with ID: {job_id}")
        return
    
    print(f"  Job: {job.get('title', 'Unknown')}")
    
    # Step 2: Get Applications for this job
    print(f"\n[2/4] Getting applications for this job...")
    applications = get_applications(job_id)
    print(f"  Found {len(applications)} applications")
    
    if not applications:
        print("  No applications to process!")
        return
    
    # Step 3: Screen each CV with AI
    print(f"\n[3/4] AI Screening CVs...")
    results = []
    
    for idx, app in enumerate(applications, 1):
        # Get candidate info (column names may vary)
        name = app.get('name') or app.get('fullName') or app.get('full_name') or 'Unknown'
        email = app.get('email') or 'no-email'
        resume_url = app.get('resumeUrl') or app.get('resume_url') or app.get('cv_url') or ''
        
        print(f"\n  [{idx}/{len(applications)}] {name}")
        
        # Download and analyze CV
        cv_text = download_pdf_text(resume_url) if resume_url else ""
        analysis = analyze_cv_with_ai(cv_text, job)
        
        score = analysis.get('score', 0)
        print(f"    Score: {score}% - {analysis.get('summary', '')[:50]}")
        
        results.append({
            'id': app.get('id'),
            'name': name,
            'email': email,
            'score': score,
            'summary': analysis.get('summary', '')
        })
    
    # Step 4: Sort and get top 10
    print(f"\n[4/4] Selecting top 10 and sending emails...")
    results.sort(key=lambda x: x['score'], reverse=True)
    top_10 = results[:10]
    
    print("\n" + "-"*60)
    print("TOP 10 CANDIDATES:")
    print("-"*60)
    
    emails_sent = 0
    for rank, candidate in enumerate(top_10, 1):
        print(f"\n  #{rank}: {candidate['name']} - {candidate['score']}%")
        print(f"      {candidate['summary'][:60]}...")
        
        # Send email
        if candidate['email'] and candidate['email'] != 'no-email':
            if send_email(candidate['email'], candidate['name'], job.get('title', 'Position')):
                print(f"      Email sent to {candidate['email']}")
                emails_sent += 1
                # Update status
                update_application_status(candidate['id'], 'shortlisted')
            else:
                print(f"      Failed to send email")
        else:
            print(f"      No email address")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Total CVs screened: {len(applications)}")
    print(f"  Top 10 selected: {len(top_10)}")
    print(f"  Emails sent: {emails_sent}")
    print("="*60 + "\n")
    
    return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_ai_agent.py <job_id>")
        print("Example: python simple_ai_agent.py cmlc7d2mp000004l14bkotiko")
        sys.exit(1)
    
    job_id = sys.argv[1]
    run_ai_agent(job_id)
