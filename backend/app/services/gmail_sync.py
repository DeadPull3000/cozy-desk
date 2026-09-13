import os
import base64
import json
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from googleapiclient.discovery import build
import google.generativeai as genai
from pydantic import BaseModel, Field
from typing import List, Optional

from dotenv import load_dotenv
from .google_auth import get_google_credentials
from ..models import Candidate, AuditLog, EventType, CandidateStatus

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 1. Define the Strict JSON Schema for Gemini (Concept #9)
class ExtractedEvent(BaseModel):
    title: str = Field(description="A short, clear title for the event or deadline.")
    course: Optional[str] = Field(default=None, description="The name of the course, if mentioned.")
    description: str = Field(description="A brief 1-2 sentence summary of what needs to be done.")
    event_type: EventType = Field(description="Must be DEADLINE, MEETING, TASK, or REMINDER.")
    date_str: Optional[str] = Field(default=None, description="The date of the event in YYYY-MM-DD format, if known.")
    time_str: Optional[str] = Field(default=None, description="The time in HH:MM format (24-hour), if known.")
    confidence: float = Field(description="A score from 0.0 to 1.0 on how likely this requires a calendar entry.")

class EmailExtractionResult(BaseModel):
    actionable: bool = Field(description="True if the email contains real academic tasks, deadlines, or meetings.")
    items: List[ExtractedEvent] = Field(description="List of extracted events, empty if actionable is false.")

# Initialize Gemini 3.1 Pro (gemini-2.5-pro) with structured output
model = genai.GenerativeModel('gemini-2.5-pro')

def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def parse_gmail_payload(payload) -> str:
    """Recursively extract plain text from Gmail payload."""
    text = ""
    if 'parts' in payload:
        for part in payload['parts']:
            text += parse_gmail_payload(part)
    elif payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            text += base64.urlsafe_b64decode(data).decode('utf-8')
    elif payload.get('mimeType') == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            html = base64.urlsafe_b64decode(data).decode('utf-8')
            text += clean_html(html)
    return text

def sync_gmail_events(db: Session):
    """
    Fetches recent emails, passes them to Gemini for semantic extraction,
    and saves actionable items to the Candidate database.
    """
    creds = get_google_credentials()
    service = build('gmail', 'v1', credentials=creds)

    # Fetch up to 10 recent unread emails in the primary inbox
    results = service.users().messages().list(
        userId='me',
        q="is:unread category:primary",
        maxResults=10
    ).execute()

    messages = results.get('messages', [])
    new_candidates_count = 0

    today_str = datetime.now().strftime("%Y-%m-%d")

    for msg in messages:
        msg_id = msg['id']
        source_id = f"gmail_{msg_id}"

        # Deduplication Check (Concept #7)
        if db.query(Candidate).filter(Candidate.source_id == source_id).first():
            continue

        # Fetch full email
        full_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        # Extract metadata
        headers = full_msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown Sender")

        body_text = parse_gmail_payload(full_msg.get('payload', {}))

        if not body_text.strip():
            continue

        # Construct prompt for LLM
        prompt = f"""
You are a highly intelligent academic personal assistant.
Read the following email. Determine if it contains any actionable academic deadlines, meetings, or tasks.
Today's date is {today_str}. Resolve all relative dates (like 'tomorrow' or 'next Friday') based on today.

Email Subject: {subject}
From: {sender}
Body:
{body_text[:3000]}
"""

        try:
            # Force JSON schema output
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=EmailExtractionResult,
                    temperature=0.1  # Low temperature for factual extraction
                )
            )

            result = EmailExtractionResult.model_validate_json(response.text)

            if result.actionable and result.items:
                for item in result.items:
                    # Ignore low confidence spam/newsletters
                    if item.confidence < 0.6:
                        continue

                    # Try to construct datetime
                    dt = None
                    if item.date_str:
                        dt_str = item.date_str
                        if item.time_str:
                            dt_str += f" {item.time_str}"
                        else:
                            dt_str += " 23:59"  # Default to end of day if no time

                        try:
                            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                        except ValueError:
                            pass  # If model hallucinates date format, leave it None

                    # Create Candidate
                    candidate = Candidate(
                        source="Gmail",
                        source_id=source_id,
                        course=item.course,
                        title=item.title,
                        description=f"{item.description}\n\nSender: {sender}",
                        event_type=item.event_type,
                        deadline=dt,
                        confidence=item.confidence,
                        status=CandidateStatus.NEW
                    )
                    db.add(candidate)
                    db.flush()

                    # Audit Trail
                    audit = AuditLog(
                        candidate_id=candidate.id,
                        action="AI Extracted from Email",
                        details=f"Extracted via Gemini 3.1 Pro. Original Subject: '{subject}'"
                    )
                    db.add(audit)
                    new_candidates_count += 1

        except Exception as e:
            print(f"Error processing email {msg_id} with AI: {e}")
            continue

    db.commit()
    return {"message": "Gmail sync complete", "new_items": new_candidates_count}