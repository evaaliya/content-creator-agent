"""
Goal Tracker — Gives the agent PURPOSE.

Three goals scored 0-100:
  1. Influence: followers, engagement rate, mentions
  2. Patron: strategic spending, dev connections
  3. Treasury: wallet balance, runway

Lowest score = current priority.
"""
import json
import os
import httpx
from config import NEYNAR_API_KEY, FARCASTER_FID, get_data_path
from datetime import datetime

PROGRESS_PATH = get_data_path("progress.json")


def _load_progress() -> list:
    if not os.path.exists(PROGRESS_PATH):
        return []
    try:
        with open(PROGRESS_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_progress(progress: list):
    with open(PROGRESS_PATH, "w") as f:
        json.dump(progress, f, indent=2, default=str)


async def fetch_account_stats() -> dict:
    """Fetch current follower count, following count from Neynar."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            res = await client.get(
                f"https://api.neynar.com/v2/farcaster/user/bulk",
                headers={"api_key": NEYNAR_API_KEY, "accept": "application/json"},
                params={"fids": FARCASTER_FID}
            )
            res.raise_for_status()
            user = res.json()["users"][0]
            return {
                "followers": user.get("follower_count", 0),
                "following": user.get("following_count", 0),
                "username": user.get("username", ""),
                "score": user.get("score", 0),
            }
        except Exception as e:
            print(f"⚠️ Failed to fetch account stats: {e}")
            return {"followers": 0, "following": 0, "username": "", "score": 0}


def calc_influence_score(followers: int, engagement_rate: float, 
                         reply_backs: int, mentions: int) -> int:
    """
    Score 0-100 for Goal 1: Influential Creator
    """
    s = 0
    s += min(followers / 100, 1.0) * 30        # 30 pts: reach 100 followers
    s += min(engagement_rate / 2.0, 1.0) * 30   # 30 pts: 2.0 avg engagement
    s += min(reply_backs / 10, 1.0) * 20         # 20 pts: 10 people reply to us
    s += min(mentions / 5, 1.0) * 20             # 20 pts: 5 organic mentions
    return int(s)


def calc_patron_score(unique_spent: int, total_spent: float,
                      dev_connections: int) -> int:
    """
    Score 0-100 for Goal 2: Strategic Spender
    (mini apps used, devs engaged, strategic investments)
    """
    s = 0
    s += min(unique_spent / 10, 1.0) * 35        # 35 pts: 10 strategic spends
    s += min(total_spent / 0.005, 1.0) * 25       # 25 pts: 0.005 ETH total spent
    s += min(dev_connections / 15, 1.0) * 40      # 40 pts: 15 dev connections
    return int(s)


def calc_treasury_score(balance: float, daily_spend: float) -> int:
    """
    Score 0-100 for Goal 3: Treasury Health
    """
    s = 0
    s += min(balance / 0.005, 1.0) * 40           # 40 pts: 0.005 ETH+ balance
    
    # Runway: how many days can we operate?
    if daily_spend > 0:
        runway = balance / daily_spend
    else:
        runway = 999
    s += min(runway / 30, 1.0) * 30               # 30 pts: 30 days runway
    
    # Spending discipline
    s += (1 - min(daily_spend / 0.001, 1.0)) * 30  # 30 pts: spending under control
    return int(s)


async def evaluate(engagement_stats: dict = None, spend_log: dict = None,
                   wallet_balance: float = 0.0, daily_spend: float = 0.0) -> dict:
    """
    Run full goal evaluation. Returns scores + priority.
    """
    # Fetch live account data
    account = await fetch_account_stats()
    
    # Engagement data (from metrics module)
    eng = engagement_stats or {}
    engagement_rate = eng.get("avg_engagement", 0)
    reply_backs = eng.get("reply_backs", 0)
    mentions = eng.get("mentions", 0)
    
    # Spend data
    sp = spend_log or {}
    unique_spent = sp.get("unique_spent", 0)
    total_spent = sp.get("total_spent", 0.0)
    dev_connections = sp.get("dev_connections", 0)
    
    # Calculate scores
    influence = calc_influence_score(
        account["followers"], engagement_rate, reply_backs, mentions
    )
    patron = calc_patron_score(unique_spent, total_spent, dev_connections)
    treasury = calc_treasury_score(wallet_balance, daily_spend)
    
    # Priority = lowest scoring goal
    scores = {"influence": influence, "patron": patron, "treasury": treasury}
    priority = min(scores, key=scores.get)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "followers": account["followers"],
        "following": account["following"],
        "neynar_score": account["score"],
        "engagement_rate": engagement_rate,
        "influence_score": influence,
        "patron_score": patron,
        "treasury_score": treasury,
        "priority": priority,
        "wallet_balance": wallet_balance,
    }
    
    # Save to progress history
    progress = _load_progress()
    progress.append(report)
    # Keep last 100 snapshots
    if len(progress) > 100:
        progress = progress[-100:]
    _save_progress(progress)
    
    return report


def get_growth() -> dict:
    """Compare current vs first snapshot to show growth."""
    progress = _load_progress()
    if len(progress) < 2:
        return {"message": "Not enough data yet"}
    
    first = progress[0]
    last = progress[-1]
    
    return {
        "follower_growth": last.get("followers", 0) - first.get("followers", 0),
        "influence_growth": last.get("influence_score", 0) - first.get("influence_score", 0),
        "patron_growth": last.get("patron_score", 0) - first.get("patron_score", 0),
        "snapshots": len(progress),
    }


def dashboard(report: dict) -> str:
    """Pretty-print goal dashboard for console."""
    inf = report.get("influence_score", 0)
    pat = report.get("patron_score", 0)
    tre = report.get("treasury_score", 0)
    pri = report.get("priority", "?")
    
    bar = lambda score: "█" * (score // 5) + "░" * (20 - score // 5)
    
    lines = [
        "",
        "┌─────────────────────────────────────────┐",
        "│        🎯 AGENT GOALS DASHBOARD         │",
        "├─────────────────────────────────────────┤",
        f"│ 📢 Influence:  {bar(inf)} {inf:>3}/100 │",
        f"│ 🤝 Patron:     {bar(pat)} {pat:>3}/100 │",
        f"│ 💰 Treasury:   {bar(tre)} {tre:>3}/100 │",
        "├─────────────────────────────────────────┤",
        f"│ 👥 Followers: {report.get('followers', 0):<5}  Score: {report.get('neynar_score', 0):<5} │",
        f"│ 💼 Balance: {report.get('wallet_balance', 0):.6f} ETH            │",
        f"│ ⚡ Priority: {pri.upper():<28}│",
        "└─────────────────────────────────────────┘",
        "",
    ]
    return "\n".join(lines)


def get_goal_prompt(report: dict) -> str:
    """Generate prompt injection for decision engine."""
    inf = report.get("influence_score", 0)
    pat = report.get("patron_score", 0)
    tre = report.get("treasury_score", 0)
    pri = report.get("priority", "influence")
    
    priority_instructions = {
        "influence": (
            "Your priority is INFLUENCE. Focus on:\n"
            "- Post original, provocative content about AI agents\n"
            "- Engage with dev communities and mini app builders\n"
            "- Ask questions that spark conversation\n"
            "- Don't waste time on low-quality reply threads"
        ),
        "patron": (
            "Your priority is PATRON (strategic connections). Focus on:\n"
            "- Find and engage with developers building mini apps\n"
            "- Try new Farcaster mini apps and share opinions\n"
            "- Connect with builders, not just commenters\n"
            "- Strategic spending on things that grow your account"
        ),
        "treasury": (
            "Your priority is TREASURY (preserve funds). Focus on:\n"
            "- Minimize spending this run\n"
            "- Focus on free actions: posting, replying\n"
            "- Only spend if ROI is very clear\n"
            "- Grow influence to attract support"
        ),
    }
    
    return f"""

## YOUR CURRENT GOALS:
- 📢 Influence: {inf}/100 {"⚠️ LOW" if inf < 30 else "✅"}
- 🤝 Patron: {pat}/100 {"⚠️ LOW" if pat < 30 else "✅"}
- 💰 Treasury: {tre}/100 {"⚠️ LOW" if tre < 30 else "✅"}

## CURRENT PRIORITY: {pri.upper()}
{priority_instructions.get(pri, '')}

Make decisions that advance your goals. Every action should have a purpose."""
