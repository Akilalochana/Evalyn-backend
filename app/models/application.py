"""
Application/Candidate database model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"              # Just applied
    SCREENING = "screening"          # AI is screening
    SHORTLISTED = "shortlisted"      # Passed AI screening (Top 10)
    ROUND1_PASSED = "round1_passed"  # Passed first round
    ROUND2_SCHEDULED = "round2_scheduled"  # Interview scheduled
    ROUND2_COMPLETED = "round2_completed"  # Interview done
    HIRED = "hired"
    REJECTED = "rejected"


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Candidate Info
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    phone = Column(String(50))
    linkedin_url = Column(String(500))
    portfolio_url = Column(String(500))
    
    # CV Data
    cv_file_path = Column(String(500))  # Path to uploaded CV
    cv_text = Column(Text)  # Extracted text from CV
    
    # Cover Letter
    cover_letter = Column(Text)
    
    # AI Screening Results
    ai_score = Column(Float, default=0.0)  # Match percentage (0-100)
    ai_summary = Column(Text)  # AI generated summary
    ai_strengths = Column(Text)  # Matching strengths
    ai_weaknesses = Column(Text)  # Gaps or concerns
    skills_matched = Column(Text)  # JSON list of matched skills
    
    # Status Tracking
    status = Column(String(50), default=ApplicationStatus.PENDING.value)
    screening_completed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    applied_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application")
    
    def __repr__(self):
        return f"<Application {self.full_name} for Job #{self.job_id}>"
