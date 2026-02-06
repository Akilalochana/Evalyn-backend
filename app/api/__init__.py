from fastapi import APIRouter
from app.api.routes import jobs, applications, interviews

api_router = APIRouter()

# Include all route modules
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(interviews.router)
