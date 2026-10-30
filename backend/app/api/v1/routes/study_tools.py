from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.tools import StudyPrompt, StudyResponse
from app.services.study_ai import create_study_response

router = APIRouter()


@router.post("/assistant", response_model=StudyResponse)
async def study_assistant(payload: StudyPrompt, _user: CurrentUser):
    return StudyResponse(response=await create_study_response(payload))
