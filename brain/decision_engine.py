import os
import json
from .llm_client import generate_agent_decision


def get_system_prompt() -> str:
    path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(path, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    # Layer 4: Inject learned strategy into prompt
    try:
        from .reflection import get_strategy
        strategy = get_strategy()
        if strategy:
            base_prompt += strategy
            print("🧬 Strategy injected into prompt")
    except Exception:
        pass  # No strategy yet — that's fine

    return base_prompt


def build_context(mentions: list, feed: list, memories: list) -> str:
    return json.dumps({
        "recent_mentions": mentions[:5],
        "home_feed": feed[:10],
        "relevant_memories": memories
    }, indent=2)


def make_decision(mentions: list, feed: list, memories: list) -> dict:
    context = build_context(mentions, feed, memories)
    prompt = get_system_prompt()
    return generate_agent_decision(context, prompt)


# ── New: Analyze a single cast and decide whether to engage ──
def analyze_cast_for_engagement(cast: dict, memories: list) -> dict:
    """
    Takes a single cast from the trending/channel feed.
    Returns a decision: reply_cast with content, or none.
    """
    author = cast.get("author", {})
    username = author.get("username", "unknown")
    display_name = author.get("display_name", username)
    cast_text = cast.get("text", "")
    cast_hash = cast.get("hash", "")
    reactions = cast.get("reactions", {})
    likes = reactions.get("likes_count", 0) if isinstance(reactions, dict) else 0
    replies_count = cast.get("replies", {}).get("count", 0) if isinstance(cast.get("replies"), dict) else 0

    context = json.dumps({
        "mode": "proactive_engagement",
        "target_cast": {
            "author": display_name,
            "username": username,
            "text": cast_text,
            "hash": cast_hash,
            "likes": likes,
            "replies": replies_count
        },
        "relevant_memories": memories,
        "instruction": (
            "You just found this cast in the public trending feed. "
            "Analyze the content. If it touches on topics you care about "
            "(AI, neuroscience, AGI, consciousness, building things, Web3 confusion, hackathons), "
            "write a genuine reply that starts a conversation. "
            "Ask a real question or share a related thought. "
            "If the topic is boring or you have nothing real to say, return type 'none'. "
            "IMPORTANT: set target_user to the cast hash so the reply goes to the right place."
        )
    }, indent=2)

    prompt = get_system_prompt()
    return generate_agent_decision(context, prompt)
