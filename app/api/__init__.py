"""API routes"""

from fastapi import APIRouter

from app.api import analyze, auth, leaderboard

router = APIRouter()

# Include sub-routers
router.include_router(analyze.router, prefix="/analyze", tags=["analyze"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])