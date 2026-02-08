"""
Application/Candidate database model
Matches NeonDB "JobApplication" table schema
Only includes columns that exist in your NeonDB
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
    """
    Matches NeonDB "JobApplication" table
    Based on actual NeonDB columns: id, name, email, phone, resumeUrl, coverLetter, status, createdAt
    """
    __tablename__ = "JobApplication"  # Match NeonDB table name (PascalCase)
    
    # Core columns from NeonDB
    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False)
    phone = Column(String(50), nullable=True)
    resumeUrl = Column(Text, nullable=True)  # URL to PDF in Vercel Blob storage
    coverLetter = Column(Text, nullable=True)
    status = Column(String(50), default=ApplicationStatus.PENDING.value)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=True)
    
    # Foreign key - may or may not exist in your NeonDB
    jobId = Column(String(50), ForeignKey("JobPost.id"), nullable=True)
    
    # AI Screening Results - we'll store these locally (add these columns to NeonDB if needed)
    # If these columns don't exist yet, the workflow will fail when trying to save
    # For now, we'll handle them as transient attributes
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application")
    
    # Transient attributes for AI results (not stored in DB until columns are added)
    _ai_score = None
    _ai_summary = None
    _ai_strengths = None
    _ai_weaknesses = None
    _skills_matched = None
    _cv_text = None
    
    @property
    def ai_score(self):
        return getattr(self, '_ai_score', None)
    
    @ai_score.setter
    def ai_score(self, value):
        self._ai_score = value
    
    @property
    def ai_summary(self):
        return getattr(self, '_ai_summary', None)
    
    @ai_summary.setter
    def ai_summary(self, value):
        self._ai_summary = value
    
    @property
    def ai_strengths(self):
        return getattr(self, '_ai_strengths', None)
    
    @ai_strengths.setter
    def ai_strengths(self, value):
        self._ai_strengths = value
    
    @property
    def ai_weaknesses(self):
        return getattr(self, '_ai_weaknesses', None)
    
    @ai_weaknesses.setter
    def ai_weaknesses(self, value):
        self._ai_weaknesses = value
    
    @property
    def skills_matched(self):
        return getattr(self, '_skills_matched', None)
    
    @skills_matched.setter
    def skills_matched(self, value):
        self._skills_matched = value
    
    @property
    def cv_text(self):
        return getattr(self, '_cv_text', None)
    
    @cv_text.setter
    def cv_text(self, value):
        self._cv_text = value
    
    @property
    def screening_completed_at(self):
        return None
    
    # Aliases for backward compatibility
    @property
    def full_name(self):
        return self.name
    
    @property
    def cv_file_path(self):
        return self.resumeUrl
    
    @property
    def cover_letter(self):
        return self.coverLetter
    
    @property
    def applied_at(self):
        return self.createdAt
    
    def __repr__(self):
        return f"<Application {self.name} for Job #{self.jobId}>"
