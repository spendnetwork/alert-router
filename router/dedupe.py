"""
Deduplication for processed records.

Prevents the same record from being posted twice across consecutive
daily runs. Uses a local JSON file to track processed OCIDs.
"""

import json
import os
from datetime import datetime, timedelta


DEFAULT_FILE = ".processed_ocids.json"
PRUNE_AFTER_DAYS = 14


def load_processed(filepath: str = DEFAULT_FILE) -> set:
    """
    Load set of already-processed OCIDs.

    Args:
        filepath: Path to the processed OCIDs JSON file.

    Returns:
        Set of OCID strings that have been previously processed.
    """
    if not os.path.exists(filepath):
        return set()

    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        return {entry["ocid"] for entry in data if "ocid" in entry}
    except (json.JSONDecodeError, KeyError):
        return set()


def is_processed(ocid: str, processed: set) -> bool:
    """
    Return True if this OCID has already been processed.

    Args:
        ocid: The OCID string to check.
        processed: Set of previously processed OCIDs.
    """
    return ocid in processed


def mark_processed(ocid: str, filepath: str = DEFAULT_FILE) -> None:
    """
    Add OCID to processed file. Prunes entries older than 14 days.

    Args:
        ocid: The OCID string to mark as processed.
        filepath: Path to the processed OCIDs JSON file.
    """
    # Load existing entries
    entries = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, KeyError):
            entries = []

    # Add the new entry
    entries.append({
        "ocid": ocid,
        "processed_at": datetime.utcnow().isoformat(),
    })

    # Prune entries older than 14 days
    cutoff = datetime.utcnow() - timedelta(days=PRUNE_AFTER_DAYS)
    entries = [
        e for e in entries
        if datetime.fromisoformat(e.get("processed_at", "2000-01-01")) > cutoff
    ]

    # Save
    with open(filepath, "w") as f:
        json.dump(entries, f, indent=2)
