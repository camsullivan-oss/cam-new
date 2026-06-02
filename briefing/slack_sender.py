"""Send the briefing to the deal owner via Slack DM."""
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def send_briefing(briefing_markdown: str, meeting_title: str, company_name: str, owner_email: str = None):
    """Send briefing as a DM to the deal owner, falling back to a channel if not found."""
    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
    fallback_channel = os.getenv("SLACK_CHANNEL", "#sales-briefings")

    channel = _resolve_dm_channel(client, owner_email, fallback_channel)

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


def _resolve_dm_channel(client: WebClient, owner_email: str, fallback: str) -> str:
    """Look up the Slack user by email and return their DM channel ID."""
    if not owner_email:
        print(f"No owner email — sending to fallback channel {fallback}")
        return fallback

    try:
        result = client.users_lookupByEmail(email=owner_email)
        user_id = result["user"]["id"]
        # Open a DM channel with that user
        dm = client.conversations_open(users=user_id)
        channel_id = dm["channel"]["id"]
        print(f"Sending DM to {owner_email} (Slack user {user_id})")
        return channel_id
    except SlackApiError as e:
        print(f"Could not find Slack user for {owner_email} ({e.response['error']}) — falling back to {fallback}")
        return fallback
