# Pre-Meeting Briefing Bot — Setup Guide

## What it does
Every 15 minutes this script checks your Google Calendar for customer meetings starting in ~30 minutes. For each one it:
1. Pulls account + opportunity data from Salesforce
2. Fetches recent Gong call summaries
3. Pulls recent Gmail threads with the customer
4. Searches for recent company news
5. Runs everything through Claude to produce a MEDPICC-aware briefing
6. Posts the briefing to your Slack channel

---

## 1. Install Python dependencies

```bash
cd cam-new
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in each value. Details below.

### Google Calendar + Gmail
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Calendar API** and **Gmail API**
4. Go to **Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the JSON → save as `credentials.json` in this folder
7. First run will open a browser to authorize — after that it auto-refreshes

### Salesforce
- `SFDC_USERNAME` / `SFDC_PASSWORD`: your login
- `SFDC_SECURITY_TOKEN`: found in Salesforce → Settings → My Personal Information → Reset My Security Token
- If your MEDPICC fields have different API names than `Metrics__c`, `Economic_Buyer__c`, etc., update `briefing/sfdc_client.py` lines 52–60

### Gong
1. Gong Settings → API → Create API Key
2. Copy Access Key and Secret into `.env`

### Slack
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create App → From Scratch
2. **OAuth & Permissions** → Add scopes: `chat:write`, `chat:write.public`
3. Install to workspace → copy Bot Token (`xoxb-...`) into `.env`
4. Invite the bot to your channel: `/invite @YourBotName`

### News search (pick one)
**Option A — Google Custom Search (free tier: 100 queries/day)**
1. Enable Custom Search API in Google Cloud Console
2. Create a Custom Search Engine at [programmablesearchengine.google.com](https://programmablesearchengine.google.com)
3. Set to search the entire web
4. Add `GOOGLE_CSE_API_KEY` and `GOOGLE_CSE_ID` to `.env`

**Option B — SerpAPI ($50/mo, easier)**
1. Sign up at [serpapi.com](https://serpapi.com)
2. Add `SERPAPI_KEY` to `.env`

### Anthropic (Claude)
Get your API key from [console.anthropic.com](https://console.anthropic.com)

---

## 3. Update your ICP

Edit `icp.txt` with your actual ICP criteria. The AI reads this file to evaluate fit.

---

## 4. Test it manually

```bash
source venv/bin/activate
python main.py
```

On first run, a browser window opens for Google OAuth. After authorizing, `token.json` is saved and future runs are silent.

---

## 5. Schedule with cron (Mac/Linux)

```bash
crontab -e
```

Add this line (update paths to match your actual location):

```
*/15 * * * * cd /Users/yourname/cam-new && /Users/yourname/cam-new/venv/bin/python main.py >> /Users/yourname/cam-new/briefing.log 2>&1
```

### Windows (Task Scheduler)
1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, repeat every 15 minutes
3. Action: Start a program
   - Program: `C:\Users\yourname\cam-new\venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\Users\yourname\cam-new`

---

## 6. Optional: MEDPICC custom field mapping

If your Salesforce opportunity fields have different API names, edit the query in `briefing/sfdc_client.py` around line 52.

Common Salesforce MEDPICC field names:
- `MEDPICC_Metrics__c`
- `MEDPICC_Economic_Buyer__c`
- `Champion__c`

Ask your Salesforce admin for the exact API names.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Google auth loop | Delete `token.json` and re-run |
| No meetings found | Check `INTERNAL_DOMAINS` in `.env` — make sure your company domain is listed |
| Salesforce login error | Confirm security token is current (it resets when you change your password) |
| Slack `not_in_channel` | `/invite @YourBotName` in the target channel |
