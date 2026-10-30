from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IdModel(ORMModel):
    id: UUID


class TimestampModel(ORMModel):
    created_at: datetime
