"""
Database connection and session management
Configured for NeonDB (PostgreSQL)
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For NeonDB PostgreSQL - handle connection pooling
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

# Create engine with appropriate settings for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,  # Helps with connection reliability for NeonDB
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=settings.DEBUG  # Log SQL in debug mode
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from app.models import job, application, interview
    Base.metadata.create_all(bind=engine)
