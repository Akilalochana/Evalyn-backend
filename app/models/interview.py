"""
Interview scheduling database model
NeonDB compatible
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class InterviewRound(str, enum.Enum):
    ROUND1 = "round1"  # Initial screening
    ROUND2 = "round2"  # Technical with SSE
    ROUND3 = "round3"  # Final/HR round


class InterviewStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class Interview(Base):
    """Interview scheduling - NeonDB compatible"""
    __tablename__ = "Interview"  # Match NeonDB PascalCase naming
    
    id = Column(String(50), primary_key=True, index=True)  # NeonDB uses string IDs
    applicationId = Column(String(50), ForeignKey("JobApplication.id"), nullable=False)
    
    # Interview Details
    round = Column(String(20), default=InterviewRound.ROUND2.value)
    interviewerName = Column(String(200))  # SSE or interviewer name
    interviewerEmail = Column(String(200))
    
    # Scheduling
    scheduledAt = Column(DateTime, nullable=False)
    durationMinutes = Column(Integer, default=60)
    meetingLink = Column(String(500))  # Video call link
    location = Column(String(200))  # For in-person interviews
    
    # Status
    status = Column(String(50), default=InterviewStatus.SCHEDULED.value)
    
    # Notes & Feedback
    notes = Column(Text)
    feedback = Column(Text)
    rating = Column(Integer, nullable=True)  # 1-5 rating
    
    # Timestamps
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    
    # Aliases for backward compatibility
    @property
    def application_id(self):
        return self.applicationId
    
    @property
    def interviewer_name(self):
        return self.interviewerName
    
    @property
    def interviewer_email(self):
        return self.interviewerEmail
    
    @property
    def scheduled_at(self):
        return self.scheduledAt
    
    @property
    def duration_minutes(self):
        return self.durationMinutes
    
    @property
    def meeting_link(self):
        return self.meetingLink
    
    def __repr__(self):
        return f"<Interview {self.round} for Application #{self.applicationId}>"
