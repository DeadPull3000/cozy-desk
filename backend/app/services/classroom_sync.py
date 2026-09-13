from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from .google_auth import get_google_credentials
from ..models import Candidate, AuditLog, EventType, CandidateStatus

def sync_classroom_assignments(db: Session):
    """
    Fetches coursework from Classroom and creates Candidates.
    Implements Concept #7: Deduplication via source_id.
    """
    creds = get_google_credentials()
    service = build('classroom', 'v1', credentials=creds)

    # 1. Get active courses
    courses_result = service.courses().list(courseStates=['ACTIVE']).execute()
    courses = courses_result.get('courses', [])

    new_candidates_count = 0

    for course in courses:
        course_name = course.get('name')
        course_id = course.get('id')

        # 2. Get coursework for each course
        coursework_result = service.courses().courseWork().list(courseId=course_id).execute()
        assignments = coursework_result.get('courseWork', [])

        for item in assignments:
            source_id = f"classroom_{item.get('id')}"
            
            # Deduplication Check
            existing = db.query(Candidate).filter(Candidate.source_id == source_id).first()
            if existing:
                continue # Skip already tracked assignments (Phase 1 logic)

            # Parse Due Date safely
            due_date = item.get('dueDate')
            due_time = item.get('dueTime')
            
            if due_date:
                # Classroom API splits date and time
                year, month, day = due_date.get('year'), due_date.get('month'), due_date.get('day')
                hours = due_time.get('hours', 23) if due_time else 23
                minutes = due_time.get('minutes', 59) if due_time else 59
                
                dt = datetime(year, month, day, hours, minutes, tzinfo=timezone.utc)
            else:
                dt = None

            # Only add things with actual deadlines for now
            if not dt:
                continue

            # Create Candidate
            candidate = Candidate(
                source="Google Classroom",
                source_id=source_id,
                course=course_name,
                title=item.get('title'),
                description=item.get('description', '')[:500], # truncate long descriptions
                event_type=EventType.DEADLINE,
                deadline=dt,
                confidence=1.0, # Deterministic source = 100% confidence
                status=CandidateStatus.NEW
            )
            db.add(candidate)
            db.flush() # Get ID before commit for audit log

            # Audit Trail
            audit = AuditLog(
                candidate_id=candidate.id,
                action="Detected assignment",
                details="Ingested via Google Classroom API."
            )
            db.add(audit)
            new_candidates_count += 1

    db.commit()
    return {"message": "Sync complete", "new_items": new_candidates_count}