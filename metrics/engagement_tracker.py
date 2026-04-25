"""
Layer 2: Engagement Tracker
Collects performance metrics on the agent's own casts.
Stores history in metrics/history.json for reflection.
"""
import json
import os
from config import get_data_path

HISTORY_PATH = get_data_path("history.json")


def _load_history() -> list:
    """Load existing metrics history."""
    if not os.path.exists(HISTORY_PATH):
        return []
    try:
        with open(HISTORY_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_history(history: list):
    """Save metrics history."""
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2, default=str)


def extract_metrics(casts: list) -> list:
    """
    Extract engagement metrics from raw cast data.
    Returns a list of metric dicts, one per cast.
    """
    metrics = []
    for cast in casts:
        reactions = cast.get("reactions", {})
        replies = cast.get("replies", {})

        likes = reactions.get("likes_count", 0) if isinstance(reactions, dict) else 0
        recasts = reactions.get("recasts_count", 0) if isinstance(reactions, dict) else 0
        reply_count = replies.get("count", 0) if isinstance(replies, dict) else 0

        # Engagement score: likes + 2*replies + recasts (replies are worth more)
        engagement_score = likes + (reply_count * 2) + recasts

        # Detect if this is a reply or original cast
        is_reply = cast.get("parent_hash") is not None

        # Extract channel
        channel = None
        if cast.get("channel"):
            channel = cast["channel"].get("id") if isinstance(cast["channel"], dict) else cast["channel"]

        metrics.append({
            "hash": cast.get("hash", ""),
            "text": cast.get("text", "")[:150],
            "posted_at": cast.get("timestamp", ""),
            "is_reply": is_reply,
            "channel": channel,
            "likes": likes,
            "replies": reply_count,
            "recasts": recasts,
            "engagement_score": engagement_score,
        })

    return metrics


def update_history(new_metrics: list) -> list:
    """
    Merge new metrics into history, avoiding duplicates.
    Updates engagement counts for existing casts (they may have changed).
    Returns the full updated history.
    """
    history = _load_history()
    existing_hashes = {m["hash"] for m in history}

    updated = 0
    added = 0

    for metric in new_metrics:
        h = metric["hash"]
        if h in existing_hashes:
            # Update existing entry with fresh engagement data
            for i, existing in enumerate(history):
                if existing["hash"] == h:
                    history[i]["likes"] = metric["likes"]
                    history[i]["replies"] = metric["replies"]
                    history[i]["recasts"] = metric["recasts"]
                    history[i]["engagement_score"] = metric["engagement_score"]
                    updated += 1
                    break
        else:
            history.append(metric)
            existing_hashes.add(h)
            added += 1

    _save_history(history)
    print(f"📈 Metrics: {added} new, {updated} updated, {len(history)} total tracked")
    return history


def get_history(limit: int = 50) -> list:
    """Get recent metrics history, sorted by engagement score (desc)."""
    history = _load_history()
    return sorted(history, key=lambda x: x.get("engagement_score", 0), reverse=True)[:limit]


def get_stats() -> dict:
    """Get summary statistics."""
    history = _load_history()
    if not history:
        return {"total_casts": 0}

    originals = [m for m in history if not m.get("is_reply")]
    replies = [m for m in history if m.get("is_reply")]

    total_engagement = sum(m.get("engagement_score", 0) for m in history)
    avg_engagement = total_engagement / len(history) if history else 0

    # Best performing channels
    channel_scores = {}
    for m in history:
        ch = m.get("channel") or "no_channel"
        if ch not in channel_scores:
            channel_scores[ch] = {"total": 0, "count": 0}
        channel_scores[ch]["total"] += m.get("engagement_score", 0)
        channel_scores[ch]["count"] += 1

    best_channels = sorted(
        channel_scores.items(),
        key=lambda x: x[1]["total"] / x[1]["count"] if x[1]["count"] > 0 else 0,
        reverse=True
    )

    return {
        "total_casts": len(history),
        "originals": len(originals),
        "replies": len(replies),
        "total_engagement": total_engagement,
        "avg_engagement": round(avg_engagement, 2),
        "avg_original_engagement": round(
            sum(m.get("engagement_score", 0) for m in originals) / len(originals), 2
        ) if originals else 0,
        "avg_reply_engagement": round(
            sum(m.get("engagement_score", 0) for m in replies) / len(replies), 2
        ) if replies else 0,
        "best_channels": [
            {"channel": ch, "avg_score": round(s["total"]/s["count"], 2), "count": s["count"]}
            for ch, s in best_channels[:5]
        ],
    }
