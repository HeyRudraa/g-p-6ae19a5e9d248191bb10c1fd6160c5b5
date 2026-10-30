import httpx
from fastapi import HTTPException

from app.core.config import get_settings
from app.schemas.tools import StudyPrompt


SYSTEM_PROMPT = (
    "You are Orbit, a patient learning coach. Explain ideas clearly, use age-appropriate language, "
    "ask guiding questions, and support the learner's own reasoning. For assessed work, give a hint "
    "or a worked example on a related problem instead of completing the submission. Do not infer "
    "a student's identity, ability, or integrity from appearance or writing style."
)


async def create_study_response(request: StudyPrompt) -> str:
    settings = get_settings()
    if not (settings.orbit_ai_base_url and settings.orbit_ai_api_key and settings.orbit_ai_model):
        raise HTTPException(status_code=503, detail="The Orbit study assistant is not configured yet.")
    mode = {
        "explain": "Explain this topic in small steps and finish with one check-for-understanding question.",
        "hint": "Give one helpful hint, not a full solution.",
        "example": "Give a short example that teaches the idea without answering an assessed prompt.",
        "quiz": "Create three practice questions and put the answer key after them.",
    }[request.mode]
    body = {
        "model": settings.orbit_ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Level: {request.level}\nTask: {mode}\nTopic: {request.prompt}"},
        ],
        "temperature": 0.4,
        "max_tokens": 900,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(25.0, connect=5.0)) as client:
            response = await client.post(
                settings.orbit_ai_base_url,
                headers={"Authorization": f"Bearer {settings.orbit_ai_api_key}"},
                json=body,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("The study provider returned an empty response.")
            return content[:12000]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="The study assistant could not answer just now.") from exc
