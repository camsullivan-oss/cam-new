"""Gmail: fetch recent email threads with a customer."""
import base64
import os
from briefing.calendar_client import get_gmail_service


def get_recent_emails(contact_emails: list[str], max_threads: int = 5) -> list[dict]:
    """Return recent email threads with the given contacts."""
    service = get_gmail_service()
    results = []

    query_parts = [f"from:{e} OR to:{e}" for e in contact_emails]
    query = " OR ".join(query_parts)

    threads_result = (
        service.users()
        .threads()
        .list(userId="me", q=query, maxResults=max_threads)
        .execute()
    )

    for thread_stub in threads_result.get("threads", []):
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=thread_stub["id"], format="metadata")
            .execute()
        )
        messages = thread.get("messages", [])
        if not messages:
            continue

        last_msg = messages[-1]
        headers = {h["name"]: h["value"] for h in last_msg.get("payload", {}).get("headers", [])}
        results.append({
            "subject": headers.get("Subject", "(no subject)"),
            "from": headers.get("From", ""),
            "date": headers.get("Date", ""),
            "snippet": last_msg.get("snippet", ""),
            "message_count": len(messages),
        })

    return results
