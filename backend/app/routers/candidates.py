from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Candidate, AuditLog, CandidateStatus
from ..schemas import CandidateResponse, CandidateStatusUpdate

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
    """Update status (Approve/Reject) and maintain audit trail."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    old_status = candidate.status
    candidate.status = update_data.status
    
    # Write to Audit Trail
    audit_entry = AuditLog(
        candidate_id=candidate.id,
        action=f"User changed status from {old_status.value} to {update_data.status.value}",
        details=f"Status update triggered via UI"
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(candidate)
    
    return candidate
