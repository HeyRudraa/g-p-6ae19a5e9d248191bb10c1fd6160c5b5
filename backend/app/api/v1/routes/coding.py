from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser
from app.schemas.tools import CodeRunRequest, CodeRunResponse
from app.services.python_practice import PracticeError, run_practice

router = APIRouter()


@router.post("/run", response_model=CodeRunResponse)
async def run_code(payload: CodeRunRequest, _user: CurrentUser):
    try:
        return CodeRunResponse(output=run_practice(payload.source))
    except PracticeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
