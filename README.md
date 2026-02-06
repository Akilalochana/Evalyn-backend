# Evalyn HR Automation Agent

AI-powered HR automation system for streamlining the recruitment process.

## 🎯 Features

- **Job Management**: Create and manage job vacancies from HR dashboard
- **Careers Page API**: Public endpoints for company careers page integration
- **CV Processing**: Upload and parse CVs (PDF/DOCX)
- **AI Screening**: Automatically screen CVs against job requirements
- **Candidate Shortlisting**: AI selects top 10 candidates
- **Email Notifications**: Automated emails to shortlisted candidates
- **Interview Scheduling**: Schedule Round 2 interviews with SSE

## 📋 Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HR AUTOMATION WORKFLOW                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. HR Dashboard                    2. Careers Page                     │
│  ┌─────────────────┐               ┌─────────────────┐                  │
│  │ Create Job      │──────────────▶│ Job Published   │                  │
│  │ Vacancy         │   Publish     │ on Website      │                  │
│  └─────────────────┘               └────────┬────────┘                  │
│                                             │                           │
│                                             ▼                           │
│                                    ┌─────────────────┐                  │
│                                    │ Candidates      │                  │
│                                    │ Apply + CV      │                  │
│                                    └────────┬────────┘                  │
│                                             │                           │
│                                             ▼                           │
│  3. AI Screening                   ┌─────────────────┐                  │
│  ┌─────────────────┐               │ Applications    │                  │
│  │ Analyze CVs     │◀──────────────│ in Database     │                  │
│  │ Score & Match   │               └─────────────────┘                  │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐               ┌─────────────────┐                  │
│  │ Shortlist       │──────────────▶│ Top 10 Selected │                  │
│  │ Top 10          │               │ (Finalists)     │                  │
│  └─────────────────┘               └────────┬────────┘                  │
│                                             │                           │
│                                             ▼                           │
│  4. Notifications                  ┌─────────────────┐                  │
│  ┌─────────────────┐               │ Email: Round 1  │                  │
│  │ Send Emails     │◀──────────────│ Passed!         │                  │
│  └─────────────────┘               └────────┬────────┘                  │
│                                             │                           │
│                                             ▼                           │
│  5. Interview Scheduling           ┌─────────────────┐                  │
│  ┌─────────────────┐               │ Round 2 with    │                  │
│  │ Schedule with   │──────────────▶│ SSE Scheduled   │                  │
│  │ SSE             │               └────────┬────────┘                  │
│  └─────────────────┘                        │                           │
│                                             ▼                           │
│                                    ┌─────────────────┐                  │
│                                    │ Interview       │                  │
│                                    │ Invitation Sent │                  │
│                                    └─────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🏗️ Project Structure

```
Evalyn-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── jobs.py         # Job vacancy CRUD endpoints
│   │       ├── applications.py # Application & CV processing
│   │       └── interviews.py   # Interview scheduling
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application settings
│   │   └── database.py         # Database connection
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── job.py              # Job model
│   │   ├── application.py      # Application/Candidate model
│   │   └── interview.py        # Interview model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── job.py              # Job Pydantic schemas
│   │   ├── application.py      # Application schemas
│   │   └── interview.py        # Interview schemas
│   │
│   └── services/
│       ├── __init__.py
│       ├── ai_agent.py         # AI CV screening agent
│       ├── email_service.py    # Email notifications
│       └── interview_scheduler.py  # Interview scheduling
│
├── uploads/
│   └── cvs/                    # Uploaded CV files
│
├── .env.example                # Environment variables template
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings:
# - OPENAI_API_KEY (required for AI screening)
# - SMTP settings (for email notifications)
```

### 3. Run the Server

```bash
# Development mode
uvicorn app.main:app --reload --port 8000

# Or using Python
python -m app.main
```

### 4. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📚 API Endpoints

### Jobs (HR Dashboard)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs/` | Create new job vacancy |
| GET | `/api/v1/jobs/` | List all jobs |
| GET | `/api/v1/jobs/{id}` | Get job details |
| PUT | `/api/v1/jobs/{id}` | Update job |
| DELETE | `/api/v1/jobs/{id}` | Delete job |
| POST | `/api/v1/jobs/{id}/publish` | Publish to careers page |
| POST | `/api/v1/jobs/{id}/unpublish` | Remove from careers page |

### Careers Page (Public)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/jobs/public/careers` | List published jobs |
| GET | `/api/v1/jobs/public/careers/{id}` | Get public job details |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/applications/apply` | Submit application (with CV) |
| GET | `/api/v1/applications/job/{id}` | Get job applications |
| POST | `/api/v1/applications/job/{id}/screen` | Run AI screening |
| POST | `/api/v1/applications/job/{id}/notify-shortlisted` | Send emails to finalists |

### Interviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/interviews/` | Schedule single interview |
| POST | `/api/v1/interviews/bulk-schedule` | Schedule all shortlisted |
| GET | `/api/v1/interviews/job/{id}` | Get job interviews |
| POST | `/api/v1/interviews/{id}/complete` | Mark interview complete |

## 🤖 AI Agent

The AI screening agent uses OpenAI GPT-4o to:

1. **Parse CVs**: Extract text from PDF/DOCX files
2. **Analyze Match**: Compare CV against job requirements
3. **Score Candidates**: Calculate match percentage (0-100)
4. **Identify Strengths**: List matching qualifications
5. **Find Gaps**: Highlight missing requirements
6. **Shortlist**: Select top 10 candidates automatically

## 📧 Email Templates

The system sends automated emails for:
- **Shortlist Notification**: Congratulating candidates who passed Round 1
- **Interview Invitation**: Scheduling details for Round 2
- **Rejection**: Polite notification for unsuccessful candidates

## 🔧 Configuration

Key settings in `.env`:

```env
# AI Settings
CV_SCREENING_TOP_CANDIDATES=10    # Number of finalists
MINIMUM_MATCH_SCORE=60.0          # Minimum score to shortlist

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_app_password
```

## 📝 Example Usage

### 1. Create a Job

```python
import requests

job_data = {
    "title": "Senior Software Engineer",
    "department": "Engineering",
    "location": "Colombo, Sri Lanka",
    "job_type": "Full-time",
    "experience_level": "Senior",
    "min_experience_years": 5,
    "description": "Build scalable systems...",
    "requirements": "Python, FastAPI, PostgreSQL..."
}

response = requests.post(
    "http://localhost:8000/api/v1/jobs/",
    json=job_data
)
```

### 2. Publish Job

```python
requests.post("http://localhost:8000/api/v1/jobs/1/publish")
```

### 3. Screen Applications

```python
response = requests.post(
    "http://localhost:8000/api/v1/applications/job/1/screen",
    params={"top_n": 10}
)
print(response.json()["shortlisted_candidates"])
```

### 4. Schedule Interviews

```python
schedule_data = {
    "job_id": 1,
    "interviewer_name": "John SSE",
    "interviewer_email": "john.sse@company.com",
    "start_date": "2026-02-15T09:00:00",
    "duration_minutes": 60,
    "gap_between_interviews_minutes": 30
}

requests.post(
    "http://localhost:8000/api/v1/interviews/bulk-schedule",
    json=schedule_data
)
```

## 🛡️ Security Notes

- Configure CORS properly for production
- Use environment variables for secrets
- Add authentication for HR dashboard endpoints
- Use HTTPS in production

## 📄 License

MIT License - Your Company
#   E v a l y n - b a c k e n d  
 