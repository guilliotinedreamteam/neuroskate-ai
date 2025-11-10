"""Video analysis endpoints"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
import aiofiles
import uuid
from datetime import datetime
import os

from app.database import get_db, TrickAnalysis
from app.cv.analyzer import analyze_video
from app.config import settings

router = APIRouter()


@router.post("/video")
async def analyze_video_endpoint(
    video: UploadFile = File(...),
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Analyze a skateboarding video
    
    Args:
        video: Video file (mp4, mov, avi)
        user_id: User ID from authentication
        
    Returns:
        Trick analysis results including:
        - trick_name: Detected trick
        - confidence: Detection confidence (0-1)
        - score: Overall performance score (0-100)
        - metrics: Detailed performance metrics
    """
    
    # Validate file format
    file_ext = video.filename.split(".")[-1].lower()
    if file_ext not in settings.ALLOWED_VIDEO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {settings.ALLOWED_VIDEO_FORMATS}"
        )
    
    # Save uploaded file
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.{file_ext}")
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await video.read()
        await f.write(content)
    
    try:
        # Analyze video
        analysis_result = await analyze_video(file_path)
        
        # Save to database
        db_analysis = TrickAnalysis(
            user_id=user_id,
            video_url=file_path,
            trick_name=analysis_result["trick_name"],
            trick_category=analysis_result["category"],
            confidence=analysis_result["confidence"],
            score=analysis_result["score"],
            rotation_degrees=analysis_result["metrics"]["rotation"],
            height_inches=analysis_result["metrics"]["height"],
            landing_stability=analysis_result["metrics"]["landing_stability"],
            style_points=analysis_result["metrics"]["style"],
            frame_count=analysis_result["frame_count"],
            duration_seconds=analysis_result["duration"],
            pose_landmarks=analysis_result["landmarks"],
            processed_at=datetime.utcnow()
        )
        
        db.add(db_analysis)
        db.commit()
        db.refresh(db_analysis)
        
        return {
            "analysis_id": db_analysis.id,
            "trick_name": db_analysis.trick_name,
            "confidence": db_analysis.confidence,
            "score": db_analysis.score,
            "metrics": {
                "rotation": db_analysis.rotation_degrees,
                "height": db_analysis.height_inches,
                "landing_stability": db_analysis.landing_stability,
                "style": db_analysis.style_points
            },
            "feedback": analysis_result.get("feedback", []),
            "processed_at": db_analysis.processed_at.isoformat()
        }
        
    except Exception as e:
        # Clean up file on error
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/history/{user_id}")
async def get_analysis_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get user's analysis history
    """
    analyses = (
        db.query(TrickAnalysis)
        .filter(TrickAnalysis.user_id == user_id)
        .order_by(TrickAnalysis.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    
    return {
        "count": len(analyses),
        "analyses": [
            {
                "id": a.id,
                "trick_name": a.trick_name,
                "score": a.score,
                "confidence": a.confidence,
                "created_at": a.created_at.isoformat()
            }
            for a in analyses
        ]
    }