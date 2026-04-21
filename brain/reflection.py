"""
Layer 3: Self-Reflection
Agent analyzes its own cast performance and generates strategy insights.
Uses Claude to evaluate what works and what doesn't.
"""
import json
import os
from datetime import datetime
from .llm_client import generate_agent_decision

REFLECTION_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "metrics", "reflection.json")


def _load_reflection() -> dict:
    """Load latest reflection."""
    if not os.path.exists(REFLECTION_PATH):
        return {}
    try:
        with open(REFLECTION_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_reflection(reflection: dict):
    """Save reflection to disk."""
    os.makedirs(os.path.dirname(REFLECTION_PATH), exist_ok=True)
    with open(REFLECTION_PATH, "w") as f:
        json.dump(reflection, f, indent=2, default=str)


def needs_reflection(history: list, min_new_casts: int = 5) -> bool:
    """Check if we have enough new data to justify a reflection."""
    last = _load_reflection()
    last_count = last.get("casts_analyzed", 0)
    return len(history) >= last_count + min_new_casts


def reflect(history: list, stats: dict) -> dict:
    """
    Run Claude self-evaluation on cast performance data.
    Returns structured insights and rules.
    """
    if not history:
        print("🪞 No history to reflect on")
        return {}

    # Sort: best performing first
    top = sorted(history, key=lambda x: x.get("engagement_score", 0), reverse=True)[:10]
    bottom = sorted(history, key=lambda x: x.get("engagement_score", 0))[:10]

    prompt = f"""You are @matricula, an autonomous AI agent on Farcaster.
You are analyzing your own posting history to improve your strategy.

## YOUR PERFORMANCE STATS:
{json.dumps(stats, indent=2)}

## YOUR TOP 10 PERFORMING CASTS:
{json.dumps(top, indent=2)}

## YOUR BOTTOM 10 PERFORMING CASTS:
{json.dumps(bottom, indent=2)}

## FULL HISTORY ({len(history)} casts):
{json.dumps(history[-30:], indent=2)}

---

Analyze your performance and respond in this EXACT JSON format:
{{
    "top_topics": ["topic1", "topic2", "topic3"],
    "avoid_topics": ["topic1", "topic2"],
    "best_channels": ["channel1", "channel2"],
    "best_format": "description of what reply style works best",
    "worst_format": "description of what reply style fails",
    "rules": [
        "Rule 1: concrete behavioral rule",
        "Rule 2: concrete behavioral rule",
        "Rule 3: concrete behavioral rule",
        "Rule 4: concrete behavioral rule",
        "Rule 5: concrete behavioral rule"
    ],
    "self_assessment": "2-3 sentence honest self-assessment of your performance"
}}

Be brutally honest. Don't sugarcoat. What actually works? What's wasting your time?
Only output valid JSON, nothing else."""

    print("🪞 Running self-reflection...")
    try:
        from anthropic import Anthropic
        from config import ANTHROPIC_API_KEY
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()

        # Parse JSON from response
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        reflection = json.loads(raw)
        reflection["reflected_at"] = datetime.now().isoformat()
        reflection["casts_analyzed"] = len(history)

        _save_reflection(reflection)
        print(f"🪞 Reflection complete: {len(reflection.get('rules', []))} rules learned")
        print(f"   Self-assessment: {reflection.get('self_assessment', '')[:100]}")
        return reflection

    except json.JSONDecodeError as e:
        print(f"🪞 Reflection parse error: {e}")
        print(f"   Raw output: {raw[:200]}")
        return {}
    except Exception as e:
        print(f"🪞 Reflection error: {e}")
        return {}


def get_strategy() -> str:
    """
    Load the latest reflection and format it as a prompt injection.
    This gets appended to the system prompt so Claude follows learned rules.
    """
    reflection = _load_reflection()
    if not reflection or not reflection.get("rules"):
        return ""

    rules = "\n".join(f"- {r}" for r in reflection.get("rules", []))
    top = ", ".join(reflection.get("top_topics", []))
    avoid = ", ".join(reflection.get("avoid_topics", []))
    best_ch = ", ".join(reflection.get("best_channels", []))
    best_fmt = reflection.get("best_format", "")
    worst_fmt = reflection.get("worst_format", "")

    return f"""

## YOUR LEARNED STRATEGY (from self-analysis on {reflection.get('reflected_at', 'unknown')}):

### Rules you've set for yourself:
{rules}

### Topics that get engagement: {top}
### Topics to avoid: {avoid}
### Best channels: {best_ch}
### What works: {best_fmt}
### What doesn't work: {worst_fmt}

Follow these rules. They came from analyzing your own data."""
