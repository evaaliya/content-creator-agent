"""
Vercel Serverless Entry Point — One agent cycle per invocation.

Triggered by:
- Vercel Cron (every 10 min on Pro plan)
- External cron service (cron-job.org, free)
- Manual GET /api/tick

Replaces the old `python3 main.py` infinite loop.
"""
import sys
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))


async def run_agent_cycle():
    """Run one complete agent cycle (replaces the infinite loop)."""
    from agent.agent_loop import AutonomousAgent

    agent = AutonomousAgent()
    agent._check_daily_reset()

    # Load persisted state from Supabase
    await load_state(agent)

    results = {
        "status": "ok",
        "daily_casts": agent.daily_casts,
        "actions": []
    }

    try:
        await agent.run()
        results["daily_casts"] = agent.daily_casts
        results["actions"].append("cycle_complete")
    except Exception as e:
        results["status"] = "error"
        results["error"] = str(e)
        print(f"❌ Agent cycle error: {e}")

    # Save state back to Supabase
    await save_state(agent)

    return results


async def load_state(agent):
    """Load agent state from Supabase (serverless = no memory between calls)."""
    try:
        from memory.supabase_client import supabase
        if not supabase:
            return

        result = supabase.table("agent_state").select("*").eq("key", "daily_state").execute()
        if result.data:
            state = result.data[0].get("value", {})
            agent.daily_casts = state.get("daily_casts", 0)
            agent.replied_hashes = set(state.get("replied_hashes", []))
            agent._posted_research_today = state.get("posted_research_today", False)

            # Check if state is from today
            import datetime
            state_date = state.get("date", "")
            today = str(datetime.date.today())
            if state_date != today:
                print("🔄 New day — resetting state")
                agent.daily_casts = 0
                agent.replied_hashes = set()
                agent._posted_research_today = False
    except Exception as e:
        print(f"⚠️ State load error: {e}")


async def save_state(agent):
    """Save agent state to Supabase for next invocation."""
    try:
        from memory.supabase_client import supabase
        if not supabase:
            return

        import datetime
        state = {
            "daily_casts": agent.daily_casts,
            "replied_hashes": list(agent.replied_hashes)[:100],
            "posted_research_today": agent._posted_research_today,
            "date": str(datetime.date.today()),
            "updated_at": str(datetime.datetime.utcnow()),
        }

        supabase.table("agent_state").upsert({
            "key": "daily_state",
            "value": state
        }).execute()
        print("💾 State saved to Supabase")
    except Exception as e:
        print(f"⚠️ State save error: {e}")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET /api/tick — run one agent cycle."""
        # Verify cron secret (optional security)
        auth = self.headers.get("Authorization", "")
        cron_secret = os.getenv("CRON_SECRET", "")

        if cron_secret and auth != f"Bearer {cron_secret}":
            # Also allow Vercel's internal cron header
            vercel_cron = self.headers.get("x-vercel-cron", "")
            if not vercel_cron:
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b'{"error": "unauthorized"}')
                return

        try:
            result = asyncio.run(run_agent_cycle())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
