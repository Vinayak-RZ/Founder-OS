"""Google Calendar integration (official API).

Setup (once): run `python scripts/google_auth.py` after placing your OAuth client
secret at the path in GOOGLE_CREDENTIALS_PATH. That produces a token file at
GOOGLE_TOKEN_PATH. All heavy Google libs are imported lazily so the bot boots
fine even when the libraries or credentials are absent.
"""
import datetime
import os

from config import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def is_configured() -> bool:
    return os.path.exists(config.google_token_path)


def _service():
    """Build an authorized Calendar service, refreshing the token if needed."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not os.path.exists(config.google_token_path):
        raise RuntimeError(
            "Google Calendar not connected. Run `python scripts/google_auth.py` once."
        )
    creds = Credentials.from_authorized_user_file(config.google_token_path, SCOPES)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(config.google_token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def create_event(summary: str, start_iso: str, end_iso: str = None,
                 description: str = "", location: str = "", attendees: list = None) -> dict:
    svc = _service()
    if not end_iso:
        start_dt = datetime.datetime.fromisoformat(start_iso.replace("Z", ""))
        end_iso = (start_dt + datetime.timedelta(hours=1)).isoformat()
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if attendees:
        body["attendees"] = [{"email": a} for a in attendees]
    ev = svc.events().insert(calendarId="primary", body=body).execute()
    return {"id": ev.get("id"), "htmlLink": ev.get("htmlLink"), "summary": summary,
            "start": start_iso}


def list_events(max_results: int = 10, time_min_iso: str = None) -> list:
    svc = _service()
    time_min = time_min_iso or datetime.datetime.utcnow().isoformat() + "Z"
    res = svc.events().list(
        calendarId="primary", timeMin=time_min, maxResults=max_results,
        singleEvents=True, orderBy="startTime",
    ).execute()
    out = []
    for ev in res.get("items", []):
        start = ev.get("start", {})
        out.append({
            "id": ev.get("id"),
            "summary": ev.get("summary", "(no title)"),
            "start": start.get("dateTime", start.get("date")),
            "location": ev.get("location", ""),
        })
    return out


def delete_event(event_id: str) -> dict:
    svc = _service()
    svc.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"deleted": event_id}
