"""
Job vacancy database model
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    department = Column(String(100))
    location = Column(String(100))
    job_type = Column(String(50))  # Full-time, Part-time, Contract
    experience_level = Column(String(50))  # Junior, Mid, Senior
    min_experience_years = Column(Integer, default=0)
    max_experience_years = Column(Integer, default=10)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)  # Required skills & qualifications
    responsibilities = Column(Text)
    benefits = Column(Text)
    is_active = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)  # Published on careers page
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deadline = Column(DateTime, nullable=True)
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    
    def __repr__(self):
        return f"<Job {self.title}>"
