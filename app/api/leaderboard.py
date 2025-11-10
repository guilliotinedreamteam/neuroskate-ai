"""Leaderboard endpoints"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db, TrickAnalysis, User

router = APIRouter()


@router.get("/global")
async def get_global_leaderboard(
    trick_name: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get global leaderboard
    
    Args:
        trick_name: Optional filter by specific trick
        limit: Number of entries to return
    """
    query = (
        db.query(
            User.username,
            TrickAnalysis.trick_name,
            func.max(TrickAnalysis.score).label("best_score"),
            func.count(TrickAnalysis.id).label("attempt_count")
        )
        .join(User)
        .group_by(User.username, TrickAnalysis.trick_name)
    )
    
    if trick_name:
        query = query.filter(TrickAnalysis.trick_name == trick_name)
    
    results = query.order_by(func.max(TrickAnalysis.score).desc()).limit(limit).all()
    
    return {
        "leaderboard": [
            {
                "rank": idx + 1,
                "username": r.username,
                "trick_name": r.trick_name,
                "best_score": r.best_score,
                "attempts": r.attempt_count
            }
            for idx, r in enumerate(results)
        ]
    }


@router.get("/tricks")
async def get_popular_tricks(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get most popular tricks
    """
    results = (
        db.query(
            TrickAnalysis.trick_name,
            func.count(TrickAnalysis.id).label("count"),
            func.avg(TrickAnalysis.score).label("avg_score")
        )
        .group_by(TrickAnalysis.trick_name)
        .order_by(func.count(TrickAnalysis.id).desc())
        .limit(limit)
        .all()
    )
    
    return {
        "tricks": [
            {
                "name": r.trick_name,
                "attempts": r.count,
                "average_score": round(r.avg_score, 2) if r.avg_score else 0
            }
            for r in results
        ]
    }