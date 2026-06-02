"""Send the briefing to Slack."""
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def send_briefing(briefing_markdown: str, meeting_title: str, company_name: str):
    """Post the briefing to the configured Slack channel."""
    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    channel = os.getenv("SLACK_CHANNEL", "#sales-briefings")

    # Slack doesn't render markdown headers well in plain text blocks,
    # so we post as a single markdown block with mrkdwn.
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Pre-Meeting Brief: {company_name}",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Meeting:* {meeting_title}",
            },
        },
        {"type": "divider"},
    ]

    # Split briefing into chunks (Slack block limit: 3000 chars per section)
    chunk_size = 2900
    text = briefing_markdown
    while text:
        chunk = text[:chunk_size]
        text = text[chunk_size:]
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": chunk},
        })

    try:
        client.chat_postMessage(
            channel=channel,
            text=f"Pre-Meeting Brief: {company_name} — {meeting_title}",
            blocks=blocks,
        )
        print(f"Briefing sent to {channel} for {company_name}")
    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")
        raise
