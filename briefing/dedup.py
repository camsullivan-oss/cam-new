"""Simple file-based deduplication so we don't send the same briefing twice."""
import json
from pathlib import Path

SENT_FILE = Path(".briefings_sent.json")


def already_sent(meeting_id: str) -> bool:
    if not SENT_FILE.exists():
        return False
    sent = json.loads(SENT_FILE.read_text())
    return meeting_id in sent


def mark_sent(meeting_id: str):
    sent = {}
    if SENT_FILE.exists():
        sent = json.loads(SENT_FILE.read_text())
    sent[meeting_id] = True
    # Keep only last 500 entries to prevent unbounded growth
    if len(sent) > 500:
        keys = list(sent.keys())
        sent = {k: sent[k] for k in keys[-500:]}
    SENT_FILE.write_text(json.dumps(sent, indent=2))
