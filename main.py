#!/usr/bin/env python3
"""
Pre-meeting briefing bot.
Run every 15 minutes via cron. Sends a Slack briefing 30 min before customer meetings.

Cron entry (edit with `crontab -e`):
  */15 * * * * cd /path/to/cam-new && /path/to/venv/bin/python main.py >> briefing.log 2>&1
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from briefing.calendar_client import get_upcoming_customer_meetings, extract_company_from_attendees
from briefing.sfdc_client import get_account_data
from briefing.gong_client import get_calls_for_account
from briefing.gmail_client import get_recent_emails
from briefing.news_client import get_company_news
from briefing.analyst import generate_briefing
from briefing.slack_sender import send_briefing
from briefing.dedup import already_sent, mark_sent


def process_meeting(meeting: dict):
    external = meeting["external_attendees"]
    contact_emails = [a["email"] for a in external if "email" in a]
    company_name = extract_company_from_attendees(external)

    print(f"Processing: {meeting['title']} | Company: {company_name}")

    sfdc_data = get_account_data(company_name, contact_emails)
    gong_calls = get_calls_for_account(company_name, contact_emails)
    emails = get_recent_emails(contact_emails)
    news = get_company_news(company_name)

    briefing = generate_briefing(
        meeting=meeting,
        company_name=company_name,
        sfdc_data=sfdc_data,
        gong_calls=gong_calls,
        emails=emails,
        news=news,
    )

    send_briefing(briefing, meeting["title"], company_name)
    mark_sent(meeting["id"])
    print(f"Done: {meeting['title']}")


def main():
    lead_minutes = int(os.getenv("BRIEFING_LEAD_TIME_MINUTES", "30"))
    print(f"Checking for meetings starting in ~{lead_minutes} minutes...")

    meetings = get_upcoming_customer_meetings(lead_minutes=lead_minutes)
    print(f"Found {len(meetings)} customer meeting(s) in window.")

    for meeting in meetings:
        if already_sent(meeting["id"]):
            print(f"Skipping (already briefed): {meeting['title']}")
            continue
        try:
            process_meeting(meeting)
        except Exception as e:
            print(f"ERROR processing {meeting['title']}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
