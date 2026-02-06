"""
Evalyn HR Automation Agent
==========================
AI-powered HR automation system for recruitment process

Flow:
1. HR creates job vacancies via dashboard
2. Jobs are published to company careers page
3. Candidates apply with their CVs
4. AI Agent screens CVs and shortlists top 10 candidates
5. Shortlisted candidates receive email (passed Round 1)
6. Round 2 interviews are scheduled with SSE
7. Interview invitations sent automatically

Author: Your Company
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    print("🚀 Starting Evalyn HR Automation Agent...")
    init_db()
    print("✅ Database initialized")
    yield
    print("👋 Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
## Evalyn HR Automation Agent API

An AI-powered HR automation system that streamlines the recruitment process.

### Features:
- **Job Management**: Create, publish, and manage job vacancies
- **Careers Page API**: Public endpoints for company careers page
- **Application Processing**: Handle candidate applications with CV uploads
- **AI Screening**: Automatically screen CVs and shortlist top candidates
- **Email Notifications**: Send automated emails to candidates
- **Interview Scheduling**: Schedule and manage Round 2 interviews with SSE

### Workflow:
1. HR creates job → publishes to careers page
2. Candidates apply via careers page
3. AI Agent screens all applications
4. Top 10 candidates shortlisted
5. Shortlisted candidates notified (Round 1 passed)
6. Round 2 interviews scheduled with SSE
7. Interview invitations sent automatically
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}


@app.get("/")
def root():
    """Root endpoint with API info"""
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "jobs": "/api/v1/jobs",
            "careers": "/api/v1/jobs/public/careers",
            "applications": "/api/v1/applications",
            "interviews": "/api/v1/interviews"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
