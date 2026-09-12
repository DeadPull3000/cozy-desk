from app.database import SessionLocal
from app.models import Candidate, AuditLog, EventType, CandidateStatus
from datetime import datetime, timedelta, timezone

db = SessionLocal()

# Clear existing test data
db.query(AuditLog).delete()
db.query(Candidate).delete()
db.commit()

# Create a sample Google Classroom candidate
due_date = datetime.now(timezone.utc) + timedelta(days=3)
candidate = Candidate(
    source="Google Classroom",
    course="Machine Learning",
    title="Assignment 3",
    description="Implement a neural network.",
    event_type=EventType.DEADLINE,
    deadline=due_date,
    confidence=0.98,
    status=CandidateStatus.NEW
)

db.add(candidate)
db.commit()
db.refresh(candidate)

# Add creation audit log
audit = AuditLog(
    candidate_id=candidate.id,
    action="Detected assignment",
    details="Parsed structured data from Google Classroom API mock."
)
db.add(audit)
db.commit()

print("🌱 Seeded database with cozy study desk dummy data!")
db.close()
