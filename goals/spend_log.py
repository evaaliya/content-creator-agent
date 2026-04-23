"""
Spend Log — Tracks strategic spending (not random tips).

Records:
- Mini app interactions
- Channel subscriptions
- Dev support / NFT mints
- Any strategic use of funds
"""
import json
import os
from config import get_data_path
from datetime import datetime

SPEND_LOG_PATH = get_data_path("spend_log.json")


def _load_log() -> list:
    if not os.path.exists(SPEND_LOG_PATH):
        return []
    try:
        with open(SPEND_LOG_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_log(log: list):
    with open(SPEND_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def log_spend(category: str, description: str, amount: float,
              recipient: str = "", tx_hash: str = ""):
    """
    Log a strategic spend.
    Categories: 'mini_app', 'subscription', 'nft_mint', 'dev_support', 'game', 'other'
    """
    log = _load_log()
    log.append({
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "description": description,
        "amount_eth": amount,
        "recipient": recipient,
        "tx_hash": tx_hash,
    })
    _save_log(log)
    print(f"💸 Logged spend: {category} — {description} ({amount} ETH)")


def get_summary() -> dict:
    """Get spending summary for goal tracker."""
    log = _load_log()
    if not log:
        return {"unique_spent": 0, "total_spent": 0.0, "dev_connections": 0}

    unique_recipients = set(e.get("recipient", "") for e in log if e.get("recipient"))
    total = sum(e.get("amount_eth", 0) for e in log)
    
    # Count dev-related interactions
    dev_categories = {"mini_app", "dev_support", "nft_mint"}
    dev_connections = len([e for e in log if e.get("category") in dev_categories])
    
    return {
        "unique_spent": len(unique_recipients),
        "total_spent": total,
        "dev_connections": dev_connections,
        "total_transactions": len(log),
    }
