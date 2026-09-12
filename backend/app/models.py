from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class CandidateStatus(str, enum.Enum):
    NEW = "NEW"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"
    CREATED = "CREATED"          # Successfully pushed to Google Calendar
    SUPERSEDED = "SUPERSEDED"    # Replaced by a newer update (e.g., deadline changed)

class EventType(str, enum.Enum):
    DEADLINE = "DEADLINE"
    MEETING = "MEETING"
    TASK = "TASK"
    REMINDER = "REMINDER"

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True) # e.g., "gmail", "classroom"
    source_id = Column(String, index=True, nullable=True) # To prevent duplication
    course = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(Enum(EventType), nullable=False)
    
    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.NEW, nullable=False)
    
    calendar_event_id = Column(String, nullable=True) # Filled when successfully written to Google Cal
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationship to audit logs
    audit_logs = relationship("AuditLog", back_populates="candidate", cascade="all, delete-orphan")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    """
    Maintains the exact provenance and history of every event as requested in Concept #19.
    """
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    action = Column(String, nullable=False) # e.g., "Detected assignment", "User approved", "Classroom deadline changed"
    details = Column(Text, nullable=True) # JSON string or extra context
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    candidate = relationship("Candidate", back_populates="audit_logs")
