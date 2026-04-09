"""
Webhook posting for Teams and Slack.

Posts formatted alert cards to Microsoft Teams (Adaptive Card)
or Slack (Block Kit) incoming webhooks.
"""

from datetime import datetime
import requests


def _format_value(value: int) -> str:
    """Format a GBP value for display. Returns 'Not published' if 0."""
    if not value or value == 0:
        return "Not published"
    return f"\u00a3{value:,.0f}"


def _format_date(date_str) -> str:
    """Format an ISO date for display. Returns 'Not specified' if None."""
    if not date_str:
        return "Not specified"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except (ValueError, AttributeError):
        return date_str


def _get_date_fields(record: dict) -> tuple[str, str]:
    """
    Select the right date label and value based on release_tags.

    Returns:
        (date_label, date_value) tuple
    """
    tags = record.get("release_tags", "")

    if "award" in tags.lower():
        start = _format_date(record.get("award_start_date_first"))
        end = _format_date(record.get("award_end_date_first"))
        if start != "Not specified" and end != "Not specified":
            return "Contract period", f"{start} to {end}"
        return "Contract period", start

    if "planning" in tags.lower():
        start = record.get("start_date") or record.get("date_created")
        return "Earliest start", _format_date(start)

    # Default: tender or anything else
    return "Closing date", _format_date(record.get("closing_date"))


def post_to_teams(webhook_url: str, record: dict, matched_rule_name: str,
                  summary: str, reason: str) -> bool:
    """
    Post Adaptive Card to Teams webhook.

    Args:
        webhook_url: Teams incoming webhook URL
        record: Procurement record dict
        matched_rule_name: Name of the matched routing rule
        summary: LLM-generated summary
        reason: LLM-generated reason for match

    Returns:
        True on success, False on failure. Never raises.
    """
    value_display = _format_value(record.get("tender_gbp_value", 0))
    date_label, date_value = _get_date_fields(record)
    release_date = _format_date(record.get("release_date"))

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "New Opportunity",
                            "weight": "Bolder",
                            "size": "Medium",
                            "color": "Accent",
                        },
                        {
                            "type": "TextBlock",
                            "text": record.get("tender_title", "Untitled"),
                            "weight": "Bolder",
                            "size": "Large",
                            "wrap": True,
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Buyer", "value": record.get("buyer_name", "N/A")},
                                {"title": "Region", "value": f"{record.get('buyer_address_region', 'N/A')}, {record.get('buyer_address_country_name', 'N/A')}"},
                                {"title": "Document type", "value": record.get("release_tags", "N/A")},
                                {"title": "Status", "value": record.get("tag_status", "N/A")},
                                {"title": "Estimated value (GBP)", "value": value_display},
                                {"title": date_label, "value": date_value},
                                {"title": "Published", "value": release_date},
                                {"title": "Matched rule", "value": matched_rule_name},
                                {"title": "Why matched", "value": reason},
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": "Summary",
                            "weight": "Bolder",
                            "separator": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": summary,
                            "wrap": True,
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View full notice",
                            "url": record.get("tender_url", ""),
                        }
                    ],
                },
            }
        ],
    }

    try:
        response = requests.post(webhook_url, json=card, timeout=30)
        if response.status_code in (200, 202):
            return True
        print(f"[ERROR] Teams webhook failed (HTTP {response.status_code}): {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[ERROR] Teams webhook network error: {e}")
        return False


def post_to_slack(webhook_url: str, record: dict, matched_rule_name: str,
                  summary: str, reason: str) -> bool:
    """
    Post Block Kit message to Slack webhook.

    Args:
        webhook_url: Slack incoming webhook URL
        record: Procurement record dict
        matched_rule_name: Name of the matched routing rule
        summary: LLM-generated summary
        reason: LLM-generated reason for match

    Returns:
        True on success, False on failure. Never raises.
    """
    value_display = _format_value(record.get("tender_gbp_value", 0))
    date_label, date_value = _get_date_fields(record)

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "New Opportunity"},
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{record.get('tender_title', 'Untitled')}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Buyer*\n{record.get('buyer_name', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Region*\n{record.get('buyer_address_region', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Type*\n{record.get('release_tags', 'N/A')}"},
                    {"type": "mrkdwn", "text": f"*Value*\n{value_display}"},
                    {"type": "mrkdwn", "text": f"*{date_label}*\n{date_value}"},
                    {"type": "mrkdwn", "text": f"*Matched rule*\n{matched_rule_name}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary*\n{summary}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View full notice"},
                        "url": record.get("tender_url", ""),
                    }
                ],
            },
            {"type": "divider"},
        ],
    }

    try:
        response = requests.post(webhook_url, json=message, timeout=30)
        if response.status_code == 200:
            return True
        print(f"[ERROR] Slack webhook failed (HTTP {response.status_code}): {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[ERROR] Slack webhook network error: {e}")
        return False


def post_alert(destination: dict, record: dict, matched_rule_name: str,
               summary: str, reason: str) -> bool:
    """
    Route to correct poster based on destination type.

    Args:
        destination: Dict with keys: name, type, webhook
        record: Procurement record dict
        matched_rule_name: Name of the matched routing rule
        summary: LLM-generated summary
        reason: LLM-generated reason for match

    Returns:
        True on success, False on failure.
    """
    dest_type = destination.get("type", "").lower()
    webhook_url = destination.get("webhook", "")

    if dest_type == "teams":
        return post_to_teams(webhook_url, record, matched_rule_name, summary, reason)
    elif dest_type == "slack":
        return post_to_slack(webhook_url, record, matched_rule_name, summary, reason)
    else:
        print(f"[ERROR] Unknown destination type: {dest_type}")
        return False
