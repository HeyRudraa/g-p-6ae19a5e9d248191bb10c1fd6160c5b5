from fastapi import APIRouter

from app.api.v1.routes import assignments, auth, classrooms, coding, grades, study_tools

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(classrooms.router, prefix="/classrooms", tags=["classrooms"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(grades.router, prefix="/grades", tags=["grades"])
api_router.include_router(coding.router, prefix="/coding", tags=["coding"])
api_router.include_router(study_tools.router, prefix="/study-tools", tags=["study-tools"])
