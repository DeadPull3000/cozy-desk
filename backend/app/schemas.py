from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from .models import CandidateStatus, EventType

# Audit Log Schema
class AuditLogResponse(BaseModel):
    id: int
    action: str
    details: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

# Candidate Schemas
class CandidateBase(BaseModel):
    title: str
    source: str
    course: Optional[str] = None
    description: Optional[str] = None
    event_type: EventType
    deadline: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    confidence: float

class CandidateResponse(CandidateBase):
    id: int
    status: CandidateStatus
    created_at: datetime
    audit_logs: List[AuditLogResponse] = []

    model_config = ConfigDict(from_attributes=True)

class CandidateStatusUpdate(BaseModel):
    status: CandidateStatus
