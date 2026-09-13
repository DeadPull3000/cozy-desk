from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from datetime import timedelta
from .google_auth import get_google_credentials
from ..models import Candidate, AuditLog, CandidateStatus

def add_event_to_calendar(db: Session, candidate: Candidate):
    """
    Takes an APPROVED candidate and writes it to Google Calendar.
    Enforces Concept #24 (Safety Invariants).
    """
    # 1. Strict Authorization Check
    if candidate.status != CandidateStatus.APPROVED:
        raise ValueError(f"Safety Invariant Violated: Cannot write unapproved event to calendar. Current status: {candidate.status}")

    # 2. Authenticate
    creds = get_google_credentials()
    service = build('calendar', 'v3', credentials=creds)

    # 3. Time Reasoning (Concept #4C)
    # Since this is Phase 1/Classroom, these are Hard Deadlines.
    # Let's represent the deadline as a 1-hour block ending at the exact due time.
    if not candidate.deadline:
        raise ValueError("Cannot schedule an event without a deadline/time.")

    end_time = candidate.deadline
    start_time = candidate.deadline - timedelta(hours=1)

    # 4. Construct Calendar Payload
    title = f"DUE: {candidate.title}"
    if candidate.course:
        title = f"[{candidate.course}] {title}"

    event_body = {
        'summary': title,
        'description': f"{candidate.description}\n\n---\nCreated by Cozy Study Desk\nSource: {candidate.source}",
        'start': {
            'dateTime': start_time.isoformat(),
        },
        'end': {
            'dateTime': end_time.isoformat(),
        },
        'colorId': '2', # 2 = Sage Green in Google Calendar, fitting our aesthetic!
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': 24 * 60}, # 1 day before
                {'method': 'popup', 'minutes': 60},      # 1 hour before
            ],
        },
    }

    # 5. Execute Write
    created_event = service.events().insert(calendarId='primary', body=event_body).execute()
    calendar_event_id = created_event.get('id')

    # 6. Update State Machine & Audit Trail
    candidate.calendar_event_id = calendar_event_id
    candidate.status = CandidateStatus.CREATED

    audit = AuditLog(
        candidate_id=candidate.id,
        action="Created Calendar Event",
        details=f"Successfully written to Google Calendar. Event ID: {calendar_event_id}"
    )
    db.add(audit)
    db.commit()

    return calendar_event_id