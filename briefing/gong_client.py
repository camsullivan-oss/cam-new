"""Gong: fetch recent call transcripts and AI summaries for an account."""
import os
import requests
from requests.auth import HTTPBasicAuth


GONG_BASE = "https://api.gong.io/v2"


def _auth():
    return HTTPBasicAuth(
        os.getenv("GONG_ACCESS_KEY"),
        os.getenv("GONG_ACCESS_KEY_SECRET"),
    )


def get_calls_for_account(company_name: str, contact_emails: list[str], max_calls: int = 5) -> list[dict]:
    """Return recent Gong calls matching the company, with AI summaries."""
    # Search calls by participant email
    calls = []
    seen_ids = set()

    for email in contact_emails:
        resp = requests.post(
            f"{GONG_BASE}/calls/extensive",
            auth=_auth(),
            json={
                "filter": {
                    "fromDateTime": _days_ago(180),
                    "toDateTime": _now(),
                    "primaryUserIds": [],
                },
                "contentSelector": {
                    "exposedFields": {
                        "parties": True,
                        "content": {
                            "topics": True,
                            "trackers": True,
                            "highlights": True,
                            "callOutcome": True,
                            "nextSteps": True,
                        },
                        "interaction": {"speakers": True},
                        "collaboration": {"publicComments": True},
                    }
                },
            },
            timeout=30,
        )
        if resp.status_code != 200:
            continue

        for call in resp.json().get("calls", []):
            call_id = call.get("metaData", {}).get("id")
            if call_id in seen_ids:
                continue
            # Filter by participant email
            parties = call.get("parties", [])
            participant_emails = [p.get("emailAddress", "").lower() for p in parties]
            if email.lower() in participant_emails or _domain_matches(email, company_name):
                seen_ids.add(call_id)
                calls.append(_summarize_call(call))
                if len(calls) >= max_calls:
                    return calls

    return calls


def _summarize_call(call: dict) -> dict:
    meta = call.get("metaData", {})
    content = call.get("content", {})
    return {
        "id": meta.get("id"),
        "title": meta.get("title", "Untitled Call"),
        "date": meta.get("started"),
        "duration_minutes": round(meta.get("duration", 0) / 60),
        "next_steps": content.get("nextSteps", []),
        "highlights": content.get("highlights", []),
        "topics": [t.get("name") for t in content.get("topics", [])],
        "outcome": content.get("callOutcome", {}).get("name"),
    }


def _domain_matches(email: str, company_name: str) -> bool:
    if "@" not in email:
        return False
    domain_root = email.split("@")[1].split(".")[0].lower()
    return company_name.lower().startswith(domain_root) or domain_root in company_name.lower()


def _days_ago(days: int) -> str:
    from datetime import datetime, timezone, timedelta
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
