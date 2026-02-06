"""
Interview scheduling database model
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
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    
    # Interview Details
    round = Column(String(20), default=InterviewRound.ROUND2.value)
    interviewer_name = Column(String(200))  # SSE or interviewer name
    interviewer_email = Column(String(200))
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60)
    meeting_link = Column(String(500))  # Video call link
    location = Column(String(200))  # For in-person interviews
    
    # Status
    status = Column(String(50), default=InterviewStatus.SCHEDULED.value)
    
    # Notes & Feedback
    notes = Column(Text)
    feedback = Column(Text)
    rating = Column(Integer, nullable=True)  # 1-5 rating
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    
    def __repr__(self):
        return f"<Interview {self.round} for Application #{self.application_id}>"
