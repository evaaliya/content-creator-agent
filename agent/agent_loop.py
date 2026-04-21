import asyncio
import random
import sys
import os
import datetime

# Ensure the parent directory is loaded in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from farcaster_service.farcaster_client import FarcasterClient
from wallet.privy_wallet import PrivyWallet
from memory.vector_memory import VectorMemory
from brain.decision_engine import make_decision, analyze_cast_for_engagement
from metrics.engagement_tracker import extract_metrics, update_history, get_history, get_stats
from brain.reflection import reflect, needs_reflection

# ── Limits ──
MAX_DAILY_CASTS = 30
CHANNELS_TO_MONITOR = ["ai", "dev", "crypto", "founders"]
FEED_ENGAGEMENT_LIMIT = 30  # engage with up to 30 casts per run


class AutonomousAgent:
    def __init__(self):
        self.fc = FarcasterClient()
        self.wallet = PrivyWallet()
        self.mem = VectorMemory()

        # Tracking
        self.daily_casts = 0
        self.daily_reset_date = datetime.date.today()
        self.replied_hashes = set()  # avoid double-replying in same session

    def _check_daily_reset(self):
        """Reset counter at midnight."""
        today = datetime.date.today()
        if today > self.daily_reset_date:
            print("🔄 New day — resetting daily cast counter")
            self.daily_casts = 0
            self.daily_reset_date = today
            self.replied_hashes.clear()

    def _can_cast(self) -> bool:
        return self.daily_casts < MAX_DAILY_CASTS

    # ──────────────────── EXECUTE ACTIONS ─────────────────────────
    async def execute_actions(self, actions: list):
        for action in actions:
            if not self._can_cast() and action.get("type") in ("publish_cast", "reply_cast"):
                print(f"🚫 Daily limit reached ({MAX_DAILY_CASTS}). Skipping.")
                continue

            a_type = action.get("type")
            content = action.get("content", "")
            target = action.get("target_user", "")
            amt = action.get("amount_usdc", 0)

            if a_type == "publish_cast":
                result = await self.fc.publish_cast(content)
                if result:
                    self.daily_casts += 1
                    print(f"📊 Daily casts: {self.daily_casts}/{MAX_DAILY_CASTS}")

            elif a_type == "reply_cast":
                if target in self.replied_hashes:
                    print(f"⏭️ Already replied to {target[:10]}... skipping")
                    continue
                result = await self.fc.reply_cast(content, target)
                if result:
                    self.daily_casts += 1
                    self.replied_hashes.add(target)
                    print(f"📊 Daily casts: {self.daily_casts}/{MAX_DAILY_CASTS}")

            elif a_type == "tip_user":
                await self.wallet.send_tip(target, amt)

            elif a_type == "none":
                pass

    # ──────────────────── STEP 1: Make one original cast ──────────
    async def post_original_cast(self):
        print("\n── ✍️ Step 1: Making original cast ──")
        if not self._can_cast():
            print("   🚫 Daily limit reached")
            return

        memories = await self.mem.semantic_search("what should I post about today")
        decision = make_decision([], [], memories)

        actions = decision.get("actions", [])
        if actions:
            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            await self.execute_actions(actions)
        else:
            print("   ⏭️ No cast decision")

    # ──────────────────── STEP 2: Respond to reactions/notifs ─────
    async def handle_notifications(self):
        print("\n── 📬 Step 2: Checking notifications ──")
        notifs = await self.fc.fetch_notifications()

        if not notifs:
            print("   No new notifications")
            return

        for notif in notifs[:10]:
            if not self._can_cast():
                break

            cast = notif.get("cast", notif)
            cast_hash = cast.get("hash", "")

            if cast_hash in self.replied_hashes:
                continue

            author = cast.get("author", {})
            username = author.get("username", "?")
            text = cast.get("text", "")

            print(f"   💬 @{username}: {text[:80]}...")

            memories = await self.mem.semantic_search(text)
            decision = make_decision([cast], [], memories)

            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            await self.execute_actions(decision.get("actions", []))

            # Store interaction in memory
            await self.mem.store_memory(str(author.get("fid", "")), text)

    # ──────────────────── STEP 3: Engage with feed (30 casts) ─────
    async def engage_feed(self):
        print(f"\n── 🌍 Step 3: Engaging with feed ({FEED_ENGAGEMENT_LIMIT} casts) ──")

        # Collect casts from trending + channels
        all_casts = []

        # Trending
        trending = await self.fc.fetch_trending_feed(limit=25)
        all_casts.extend(trending)

        # Channels
        for channel in CHANNELS_TO_MONITOR:
            channel_casts = await self.fc.fetch_channel_feed(channel, limit=10)
            all_casts.extend(channel_casts)

        # Deduplicate by hash
        seen = set()
        unique_casts = []
        for c in all_casts:
            h = c.get("hash", "")
            if h and h not in seen:
                seen.add(h)
                unique_casts.append(c)

        # Shuffle so it's not always the same order
        random.shuffle(unique_casts)

        print(f"   📋 {len(unique_casts)} unique casts to scan")

        engaged = 0
        for cast in unique_casts:
            if not self._can_cast() or engaged >= FEED_ENGAGEMENT_LIMIT:
                break

            cast_hash = cast.get("hash", "")
            if cast_hash in self.replied_hashes:
                continue

            author = cast.get("author", {})
            username = author.get("username", "?")
            text = cast.get("text", "")

            # Skip very short or empty casts
            if len(text.strip()) < 20:
                continue

            print(f"\n   👀 @{username}: {text[:80]}...")

            memories = await self.mem.semantic_search(text)
            decision = analyze_cast_for_engagement(cast, memories)

            action_type = decision.get("actions", [{}])[0].get("type", "none")

            if action_type == "none":
                print(f"   ⏭️ Skip")
                continue

            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            await self.execute_actions(decision.get("actions", []))
            engaged += 1

            # 2-4 sec pause between engagements (minimal, just to not hammer API)
            await asyncio.sleep(random.uniform(2, 4))

        print(f"\n   ✅ Engaged with {engaged} casts total")

    # ──────────────────── STEP 0: Self-Reflect ────────────────────
    async def self_reflect(self):
        print("\n── 🪞 Step 0: Self-reflection ──")
        # Fetch my recent casts with engagement data
        my_casts = await self.fc.fetch_my_casts(limit=50)
        if not my_casts:
            print("   No casts to analyze yet")
            return

        # Extract and store metrics
        metrics = extract_metrics(my_casts)
        history = update_history(metrics)

        # Only reflect if we have enough new data
        if needs_reflection(history, min_new_casts=5):
            stats = get_stats()
            print(f"   📊 Stats: {stats.get('total_casts', 0)} casts, avg engagement: {stats.get('avg_engagement', 0)}")
            reflection = reflect(history, stats)
            if reflection:
                print(f"   🧬 New rules: {reflection.get('rules', [])[:2]}")
        else:
            print("   ⏭️ Not enough new data to reflect (need 5+ new casts)")

    # ──────────────────── MAIN RUN (single execution) ─────────────
    async def run(self):
        self._check_daily_reset()

        print(f"\n{'='*50}")
        print(f"🤖 @matricula — single run")
        print(f"{'='*50}")

        # Step 0: Reflect on past performance (updates strategy)
        await self.self_reflect()

        if not self._can_cast():
            print("🚫 Daily cast limit reached.")
            return

        # Step 1: Make one original cast (uses updated strategy)
        await self.post_original_cast()

        # Step 2: Respond to notifications/reactions
        await self.handle_notifications()

        # Step 3: Engage with feed (up to 30 casts, no sleeping)
        await self.engage_feed()

        print(f"\n{'='*50}")
        print(f"✅ Run complete. Casts: {self.daily_casts}/{MAX_DAILY_CASTS}")
        print(f"{'='*50}")

    # ──────────────────── LEGACY: Loop mode (optional) ────────────
    async def start(self):
        """Run once and exit. No infinite loop."""
        print("🚀 Agent sequence initiated.")
        await self.run()
        print("👋 Done.")
