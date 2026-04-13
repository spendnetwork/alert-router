# Open Opportunities Alert Router

Fetch today's government procurement opportunities, classify them with an LLM against your plain-English rules, and post matches to Microsoft Teams or Slack.

Each alert includes a relevance score (1-10), a plain-English summary, and direct links to both the original notice and Open Opportunities.

## What you need

- **Open Opportunities API credentials** - [Expert tier](https://openopps.com/api)
- **Google Gemini API key** - [Get one at aistudio.google.com](https://aistudio.google.com/apikey)
- **A Microsoft Teams or Slack webhook URL** (see setup instructions below)

## Install

```bash
git clone https://github.com/spendnetwork/alert-router
cd alert-router
pip install -r requirements.txt
```

## Configure

```bash
cp config.yaml.example config.yaml
```

Open `config.yaml` and fill in:

1. Your Spend Network API credentials (email + password)
2. Your Gemini API key
3. Your webhook URLs
4. Your routing rules (plain English descriptions of what each channel should receive)
5. Optionally, a relevance gate to filter out false positives

## Run

```bash
python run.py                              # live run
python run.py --dry-run                    # classify but don't post
python run.py --limit 5                    # fetch only 5 records
python run.py --lookback 7                 # look back 7 days
python run.py --config /path/to/config.yaml  # custom config path
```

### Important: API usage limits

**The procurement database updates twice a day.** Making repeated requests (e.g. every few minutes) is pointless — the data won't have changed. Running the router once or twice a day is all you need.

Excessive API usage will trigger rate limits and **your account may be suspended**. Please be respectful:

- **Run once or twice a day** — a morning and evening run catches everything
- **Don't poll in a loop** — there's no new data between updates
- **Use search filters** — always filter by keyword, category, or buyer. Don't fetch unfiltered data
- **Use `max_records`** — cap the number of records per run while testing
- **Test with `--dry-run`** — saves webhook quota and is easier to iterate on

### Example dry-run output

```
[DRY RUN] Would post to: bd-south (teams)
  Title:     Cyber Security Services 3 (DPS) Stage 1 Capability Assessment
  Buyer:     METROPOLITAN POLICE SERVICE
  Value:     Not published
  Rule:      bd-south
  Relevance: 9/10
  Summary:   The Metropolitan Police Service is conducting a capability
             assessment for their Cyber Security Services 3 DPS...
```

### Run summary

Every run prints a summary:

```
--- Run complete ---
Records fetched:    42
Already processed:  12
Classified:         30
Matched:            8
Posted:             8
Unmatched:          22
Errors:             0
Duration:           43s
```

## Automate (run every morning at 7am)

```bash
crontab -e
```

Add this line:

```
0 7 * * * cd /path/to/alert-router && python run.py >> logs/run.log 2>&1
```

Create the logs directory first: `mkdir -p logs`

## How to get a Teams webhook URL

Microsoft Teams now uses **Power Automate Workflows** for webhooks:

1. In Microsoft Teams, go to the channel where you want alerts
2. Click the **...** menu next to the channel name
3. Click **Manage channel** or **Workflows**
4. Choose **"Post to a channel when a webhook request is received"**
5. Follow the setup — it gives you a URL
6. Copy the webhook URL — paste it into your `config.yaml`

The router automatically detects Power Automate Workflows URLs and formats the payload accordingly.

## How to get a Slack webhook URL

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** > **From scratch**
3. Name it "Procurement Alerts", select your workspace
4. Go to **Incoming Webhooks** > toggle it **On**
5. Click **Add New Webhook to Workspace**
6. Select the channel for alerts
7. Copy the webhook URL — paste it into your `config.yaml`

## Relevance gate

The relevance gate is an optional first-pass filter that runs before any routing rules. If a record fails the gate, it scores 0 and isn't routed anywhere — regardless of the routing rules.

This is useful when your search keywords are broad and pull in false positives. For example, searching for "security" will match both cyber security and physical security (guards, CCTV, patrols). The gate lets the LLM filter out the false positives before routing.

```yaml
relevance_gate: >
  This opportunity must be genuinely related to CYBER SECURITY.
  Physical security (guards, CCTV, patrols, keyholding) should FAIL.
```

Remove or leave blank to disable the gate.

## Relevance scoring

Every classified record gets a relevance score from 1-10:

| Score | Meaning |
|-------|---------|
| 9-10 | Excellent match — directly on topic |
| 7-8 | Good match — clearly relevant |
| 4-6 | Partial match — some relevance |
| 1-3 | Marginal — keyword appeared but weak fit |
| 0 | Failed the relevance gate |

The score appears on every Teams and Slack card with colour coding (green/amber/red).

## Multi-destination routing

A single record can match multiple routing rules and will be posted to all matched destinations. For example, an NHS cyber security tender in Manchester would match:

- `bd-north` (buyer in North of England)
- `consulting` (professional services)
- `health-opps` (NHS buyer)

## Writing effective routing rules

### Match by subject matter
```yaml
- description: >
    All cyber security consulting, penetration testing, SOC services,
    security architecture, threat intelligence, and red team exercises
  destination: cyber-team
```

### Match by buyer geography
```yaml
- description: >
    The buying organisation is located in London, South East England,
    South West England, or East of England.
    Also includes UK-wide central government departments based in London.
  destination: bd-south
```

### Match by buyer organisation type
```yaml
- description: >
    The BUYER ORGANISATION NAME is a health sector body.
    Match ONLY if the buyer name contains NHS, Health, ICB, UKHSA, etc.
    DO NOT match based on the subject — only the buyer name matters.
  destination: health-opps
```

### Match by value threshold
```yaml
- description: >
    Any IT services or software development contract worth more than
    £500,000 from any UK public sector buyer
  destination: large-it-deals
```

**Tips:**
- Be specific — include synonyms, alternative names, and examples
- Clarify what should NOT match (e.g., "physical security" vs "cyber security")
- For buyer-based rules, say explicitly "match on the buyer name, not the subject"
- Test with `--dry-run` to refine your rules before going live

## How it works

```
┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│ Spend Network    │────>│   Gemini      │────>│ Teams/Slack  │
│ Procurement API  │     │   (classify)  │     │  (webhooks)  │
└──────────────────┘     └──────────────┘     └──────────────┘
  Fetch daily records     Relevance gate       Post formatted
  with your filters       + routing rules      alert cards
                          + relevance score
```

1. **Fetch** — Queries the Spend Network API for recent opportunities matching your filters
2. **Deduplicate** — Skips records already posted in previous runs (14-day rolling window)
3. **Gate** — Checks each record against the relevance gate (if configured)
4. **Classify** — Sends each record to Gemini with your routing rules; returns matched destinations, relevance score, summary, and reason
5. **Route** — Posts branded alert cards to the matched Teams or Slack channels

## Don't want to run this yourself?

This script demonstrates what's possible with the Open Opportunities API. If you'd rather have managed alerts without running code:

**[Open Opportunities](https://openopps.com)** includes API access, daily alerts, and more — so your team can focus on winning contracts, not maintaining scripts.

## A note on this code

This entire project — every line of Python, the config structure, the routing logic, and this README — was built using [Claude Code](https://claude.ai/claude-code) to demonstrate how quickly you can build useful tools on top of the Open Opportunities API. It works, we use it internally, and we're sharing it as a starting point.

That said: this is AI-generated code shared as a practical example, not a production-grade product. Please review it, test it in your own environment, and adapt it to your needs before relying on it. We welcome contributions and feedback.

## License

MIT
