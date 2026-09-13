from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Candidate, AuditLog, CandidateStatus
from ..schemas import CandidateResponse, CandidateStatusUpdate
from ..services.calendar_writer import add_event_to_calendar

router = APIRouter(prefix="/api/candidates", tags=["candidates"])

@router.get("/pending", response_model=List[CandidateResponse])
def get_pending_candidates(db: Session = Depends(get_db)):
    """Fetch all candidates waiting for human approval."""
    return db.query(Candidate).filter(
        Candidate.status.in_([CandidateStatus.NEW, CandidateStatus.NEEDS_REVIEW])
    ).all()

@router.put("/{candidate_id}/status", response_model=CandidateResponse)
def update_candidate_status(
    candidate_id: int, 
    update_data: CandidateStatusUpdate, 
    db: Session = Depends(get_db)
):
    """Update status (Approve/Reject), write to Calendar if approved, and maintain audit trail."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    old_status = candidate.status
    candidate.status = update_data.status

    # 1. Write the status change to Audit Trail
    audit_entry = AuditLog(
        candidate_id=candidate.id,
        action=f"User changed status from {old_status.value} to {update_data.status.value}",
        details=f"Status update triggered via UI"
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(candidate)

    # 2. Trigger Execution Layer if APPROVED
    if update_data.status == CandidateStatus.APPROVED:
        try:
            add_event_to_calendar(db, candidate)
            # add_event_to_calendar updates the status to CREATED, so we refresh again
            db.refresh(candidate)
        except Exception as e:
            print(f"Failed to write to calendar: {e}")
            # Revert the status if calendar write fails so the user can try again
            candidate.status = old_status
            db.commit()
            raise HTTPException(status_code=500, detail=f"Failed to add to Google Calendar: {str(e)}")

    return candidate

from ..services.classroom_sync import sync_classroom_assignments
from ..services.gmail_sync import sync_gmail_events

@router.post("/sync/classroom")
def trigger_classroom_sync(db: Session = Depends(get_db)):
    """Trigger a sync with Google Classroom."""
    try:
        result = sync_classroom_assignments(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/gmail")
def trigger_gmail_sync(db: Session = Depends(get_db)):
    """Trigger AI extraction from unread Gmails."""
    try:
        result = sync_gmail_events(db)
        return result
    except Exception as e:
        print(f"Gmail Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
