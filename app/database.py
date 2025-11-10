"""Database configuration and models"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from app.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    analyses = relationship("TrickAnalysis", back_populates="user")
    

class TrickAnalysis(Base):
    """Trick analysis results"""
    __tablename__ = "trick_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    video_url = Column(String, nullable=False)
    
    # Trick information
    trick_name = Column(String, nullable=False)
    trick_category = Column(String)  # flip, grind, grab, etc.
    confidence = Column(Float, nullable=False)
    
    # Performance metrics
    score = Column(Float)  # Overall score 0-100
    rotation_degrees = Column(Float)  # Board rotation
    height_inches = Column(Float)  # Jump height
    landing_stability = Column(Float)  # 0-1 score
    style_points = Column(Float)  # AI-evaluated style
    
    # Analysis details
    frame_count = Column(Integer)
    duration_seconds = Column(Float)
    pose_landmarks = Column(JSON)  # Serialized landmark data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="analyses")


class Leaderboard(Base):
    """Global leaderboard entries"""
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trick_analysis_id = Column(Integer, ForeignKey("trick_analyses.id"), nullable=False)
    
    trick_name = Column(String, index=True, nullable=False)
    score = Column(Float, nullable=False)
    rank = Column(Integer)
    
    created_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()