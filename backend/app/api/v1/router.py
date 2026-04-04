from fastapi import APIRouter

from app.api.v1 import assessments, auth, chat, health, mood, profile, voice

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(voice.router)
api_router.include_router(assessments.router)
api_router.include_router(mood.router)
api_router.include_router(profile.router)
