"""Claude-powered analyst: generate the pre-meeting briefing."""
import os
import json
from pathlib import Path
import anthropic


def generate_briefing(
    meeting: dict,
    company_name: str,
    sfdc_data: dict,
    gong_calls: list[dict],
    emails: list[dict],
    news: list[dict],
) -> str:
    """Call Claude to produce a structured pre-meeting briefing."""
    icp_text = _load_icp()
    context = _build_context(meeting, company_name, sfdc_data, gong_calls, emails, news)

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    system_prompt = f"""You are a senior sales intelligence analyst at Applitools.
Your job is to prepare concise, actionable pre-meeting briefings for account executives.
Be direct and specific. Flag gaps clearly. Do not pad with filler.

Our Ideal Customer Profile (ICP):
{icp_text}

MEDPICC Framework definitions:
- Metrics: Quantified business impact the customer cares about
- Economic Buyer: The person who can authorize budget
- Decision Criteria: How they will evaluate and choose a solution
- Decision Process: Steps and timeline to reach a decision
- Identify Pain: Core business/technical pain driving this purchase
- Champion: Internal advocate who will sell for us internally
- Competition: Other vendors being evaluated"""

    user_prompt = f"""Generate a pre-meeting briefing for the following meeting and customer data.

{context}

Produce the briefing in this exact format:

## 🗓 Meeting: {{meeting_title}} — {{meeting_time}}
**Attendees:** {{external attendees and their titles if known}}

---

## 📌 Use Case & Deal Summary
*(Based on Gong calls, SFDC, and emails — 3–5 bullet points)*

---

## 📰 Recent Company News
*(Last 90 days — flag anything relevant to our pitch)*

---

## ✅ ICP Fit Assessment
**Verdict:** [Strong Fit / Partial Fit / Poor Fit]
*(3–4 bullet points explaining why, citing specific data)*

---

## 🔴 MEDPICC Gaps
For each MEDPICC element, note: what we know (if anything) and whether it's a gap.
Format each as: **[M/E/D/P/I/C/C]**: Known: ... | Gap: ...

---

## 🕸 Multi-Threading Assessment
*(Who have we talked to? Who are we missing? Recommend specific titles to engage)*

---

## 💡 Recommended Talk Tracks
*(2–3 specific angles to take in this meeting based on the gaps and news)*"""

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    return response.content[0].text


def _load_icp() -> str:
    icp_file = os.getenv("ICP_DEFINITION_FILE", "icp.txt")
    path = Path(icp_file)
    if path.exists():
        return path.read_text()
    return "ICP definition not found. Update icp.txt with your criteria."


def _build_context(
    meeting: dict,
    company_name: str,
    sfdc_data: dict,
    gong_calls: list[dict],
    emails: list[dict],
    news: list[dict],
) -> str:
    parts = []

    # Meeting info
    parts.append(f"## Meeting\nTitle: {meeting['title']}\nStart: {meeting['start']}")
    attendees_str = ", ".join(
        f"{a.get('displayName', a.get('email', 'Unknown'))} <{a.get('email', '')}>"
        for a in meeting.get("external_attendees", [])
    )
    parts.append(f"External Attendees: {attendees_str}")

    # SFDC
    if sfdc_data.get("found"):
        acct = sfdc_data.get("account", {})
        opp = sfdc_data.get("opportunity")
        parts.append(f"\n## Salesforce Account\n"
                     f"Name: {acct.get('Name')}\n"
                     f"Industry: {acct.get('Industry')}\n"
                     f"Employees: {acct.get('NumberOfEmployees')}\n"
                     f"Annual Revenue: {acct.get('AnnualRevenue')}\n"
                     f"Type: {acct.get('Type')}")
        if opp:
            parts.append(f"\n## Open Opportunity\n"
                         f"Name: {opp.get('Name')}\n"
                         f"Stage: {opp.get('StageName')}\n"
                         f"Amount: ${opp.get('Amount', 0):,.0f}\n"
                         f"Close Date: {opp.get('CloseDate')}\n"
                         f"Probability: {opp.get('Probability')}%")
        medpicc = sfdc_data.get("medpicc_fields", {})
        if any(medpicc.values()):
            parts.append("\n## MEDPICC Fields (from SFDC)")
            for k, v in medpicc.items():
                if v:
                    parts.append(f"- {k}: {v}")
        contacts = sfdc_data.get("contacts", [])
        if contacts:
            parts.append("\n## Known Contacts in SFDC")
            for c in contacts:
                parts.append(f"- {c.get('Name')} | {c.get('Title')} | {c.get('Email')}")
    else:
        parts.append(f"\n## Salesforce\nNo account found for '{company_name}'. This may be a new prospect.")

    # Gong
    if gong_calls:
        parts.append("\n## Recent Gong Calls")
        for call in gong_calls:
            parts.append(f"\n### {call['title']} ({call['date']}, {call['duration_minutes']} min)")
            if call.get("topics"):
                parts.append(f"Topics: {', '.join(call['topics'])}")
            if call.get("next_steps"):
                parts.append("Next Steps: " + "; ".join(call["next_steps"]))
            if call.get("outcome"):
                parts.append(f"Outcome: {call['outcome']}")
    else:
        parts.append("\n## Gong Calls\nNo recent calls found.")

    # Emails
    if emails:
        parts.append("\n## Recent Email Threads")
        for e in emails:
            parts.append(f"- [{e['date']}] {e['subject']} ({e['message_count']} messages) — {e['snippet'][:120]}")
    else:
        parts.append("\n## Emails\nNo recent email threads found.")

    # News
    if news:
        parts.append("\n## Recent Company News")
        for n in news:
            parts.append(f"- [{n.get('date', '')}] {n['title']}: {n['snippet'][:150]}")
    else:
        parts.append("\n## Company News\nNo news found.")

    return "\n".join(parts)
