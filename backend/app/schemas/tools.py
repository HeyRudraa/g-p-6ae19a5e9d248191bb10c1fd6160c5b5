from typing import Literal

from pydantic import BaseModel, Field


class CodeRunRequest(BaseModel):
    source: str = Field(min_length=1, max_length=8000)


class CodeRunResponse(BaseModel):
    output: str
    language: Literal["python"] = "python"


class StudyPrompt(BaseModel):
    prompt: str = Field(min_length=2, max_length=4000)
    mode: Literal["explain", "hint", "example", "quiz"] = "explain"
    level: Literal["beginner", "intermediate", "advanced"] = "beginner"


class StudyResponse(BaseModel):
    response: str
