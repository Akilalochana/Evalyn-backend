from fastapi import APIRouter
from app.api.routes import jobs, applications, interviews, enhanced_screening, hr_automation

api_router = APIRouter()

# Include all route modules
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(interviews.router)
api_router.include_router(enhanced_screening.router)  # Enhanced screening features
api_router.include_router(hr_automation.router)  # Complete HR Automation Workflow


