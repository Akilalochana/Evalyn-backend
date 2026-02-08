"""
Job vacancy database model
Matches NeonDB "JobPost" table schema
Only includes columns that exist in your NeonDB
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Job(Base):
    """
    Matches NeonDB "JobPost" table
    ONLY columns that exist in your actual NeonDB table
    """
    __tablename__ = "JobPost"  # Match NeonDB table name (PascalCase)
    
    # Only include columns that exist in NeonDB
    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow, nullable=True)
    
    # Relationships
    applications = relationship("Application", back_populates="job")
    
    # Properties for backwards compatibility (return defaults for missing columns)
    @property
    def job_type(self):
        return "Full-time"
    
    @property
    def jobType(self):
        return "Full-time"
    
    @property
    def experience_level(self):
        return "Mid-level"
    
    @property
    def experienceLevel(self):
        return "Mid-level"
    
    @property
    def min_experience_years(self):
        return 0
    
    @property
    def max_experience_years(self):
        return 10
    
    @property
    def is_active(self):
        return True
    
    @property
    def isActive(self):
        return True
    
    @property
    def is_published(self):
        return True
    
    @property
    def isPublished(self):
        return True
    
    @property
    def location(self):
        return "Remote"
    
    @property
    def created_at(self):
        return self.createdAt
    
    @property
    def updatedAt(self):
        return self.createdAt
    
    @property
    def department(self):
        return None
    
    @property
    def responsibilities(self):
        return self.description
    
    def __repr__(self):
        return f"<Job {self.title}>"
