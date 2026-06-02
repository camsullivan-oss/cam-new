"""Google Calendar: find upcoming customer meetings."""
import os
import pickle
from datetime import datetime, timezone, timedelta
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def _get_google_creds():
    token_file = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    creds_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    creds = None

    if Path(token_file).exists():
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return creds


def get_calendar_service():
    return build("calendar", "v3", credentials=_get_google_creds())


def get_gmail_service():
    return build("gmail", "v1", credentials=_get_google_creds())


def get_upcoming_customer_meetings(lead_minutes: int = 30) -> list[dict]:
    """Return meetings starting within the next `lead_minutes` minutes that have external attendees."""
    internal_domains = set(
        d.strip().lower()
        for d in os.getenv("INTERNAL_DOMAINS", "applitools.com").split(",")
        if d.strip()
    )

    service = get_calendar_service()
    now = datetime.now(timezone.utc)
    window_start = now + timedelta(minutes=lead_minutes - 5)
    window_end = now + timedelta(minutes=lead_minutes + 5)

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=window_start.isoformat(),
            timeMax=window_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    meetings = []
    for event in events_result.get("items", []):
        attendees = event.get("attendees", [])
        external = [
            a for a in attendees
            if not any(a.get("email", "").lower().endswith(d) for d in internal_domains)
            and not a.get("self", False)
        ]
        if not external:
            continue

        start = event["start"].get("dateTime", event["start"].get("date"))
        meetings.append({
            "id": event["id"],
            "title": event.get("summary", "Untitled Meeting"),
            "start": start,
            "attendees": attendees,
            "external_attendees": external,
            "description": event.get("description", ""),
            "organizer": event.get("organizer", {}),
        })

    return meetings


def extract_company_from_attendees(external_attendees: list[dict]) -> str:
    """Best-guess company name from external attendee email domains."""
    domains = []
    for a in external_attendees:
        email = a.get("email", "")
        if "@" in email:
            domain = email.split("@")[1].lower()
            # strip common TLDs to get company slug
            company = domain.split(".")[0]
            domains.append(company)
    # Return most common domain root
    if not domains:
        return "Unknown"
    return max(set(domains), key=domains.count).title()
