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

# ── Daily limits ──
MAX_DAILY_CASTS = 30
CHANNELS_TO_MONITOR = ["ai", "dev", "crypto", "founders"]


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

    # ──────────────────── PHASE 1: Respond to notifications ──────
    async def handle_notifications(self):
        print("\n── 📬 Phase 1: Checking notifications ──")
        notifs = await self.fc.fetch_notifications()

        if not notifs:
            print("   No new notifications")
            return

        # Process up to 5 notifications per cycle
        for notif in notifs[:5]:
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

    # ──────────────────── PHASE 2: Engage with trending feed ─────
    async def engage_trending(self):
        print("\n── 🌍 Phase 2: Scanning trending feed ──")
        casts = await self.fc.fetch_trending_feed(limit=25)

        if not casts:
            print("   No trending casts found")
            return

        engaged = 0
        max_engagements_per_cycle = 3  # don't spam

        for cast in casts:
            if not self._can_cast() or engaged >= max_engagements_per_cycle:
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
                print(f"   ⏭️ Skipped (not interesting enough)")
                continue

            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            await self.execute_actions(decision.get("actions", []))
            engaged += 1

            # Small pause between engagements to look human
            await asyncio.sleep(random.randint(3, 8))

        print(f"   ✅ Engaged with {engaged} trending casts")

    # ──────────────────── PHASE 3: Explore channels ──────────────
    async def explore_channels(self):
        print("\n── 📡 Phase 3: Exploring channels ──")

        if not self._can_cast():
            print("   Daily limit reached, skipping channels")
            return

        # Pick 1-2 random channels to explore per cycle
        channels = random.sample(CHANNELS_TO_MONITOR, min(2, len(CHANNELS_TO_MONITOR)))

        for channel in channels:
            if not self._can_cast():
                break

            casts = await self.fc.fetch_channel_feed(channel, limit=10)

            for cast in casts[:3]:  # max 3 per channel
                if not self._can_cast():
                    break

                cast_hash = cast.get("hash", "")
                if cast_hash in self.replied_hashes:
                    continue

                text = cast.get("text", "")
                if len(text.strip()) < 20:
                    continue

                author = cast.get("author", {})
                username = author.get("username", "?")

                print(f"\n   👀 /{channel} @{username}: {text[:80]}...")

                memories = await self.mem.semantic_search(text)
                decision = analyze_cast_for_engagement(cast, memories)

                action_type = decision.get("actions", [{}])[0].get("type", "none")
                if action_type == "none":
                    print(f"   ⏭️ Skipped")
                    continue

                print(f"   🧠 {decision.get('thoughts', '')[:100]}")
                await self.execute_actions(decision.get("actions", []))

                await asyncio.sleep(random.randint(3, 8))

    # ──────────────────── MAIN CYCLE ─────────────────────────────
    async def cycle(self):
        self._check_daily_reset()

        print(f"\n{'='*50}")
        print(f"🤖 Agent Cycle | Casts today: {self.daily_casts}/{MAX_DAILY_CASTS}")
        print(f"{'='*50}")

        if not self._can_cast():
            print("🚫 Daily cast limit reached. Sleeping until tomorrow...")
            return

        # Phase 1: Always respond to people talking to us
        await self.handle_notifications()

        # Phase 2: Go hunting in the trending feed
        await self.engage_trending()

        # Phase 3: Dive into specific channels
        await self.explore_channels()

        print(f"\n📊 Cycle complete. Total casts today: {self.daily_casts}/{MAX_DAILY_CASTS}")

    # ──────────────────── START LOOP ─────────────────────────────
    async def start(self):
        print("🚀 Agent sequence initiated.")
        while True:
            try:
                await self.cycle()
            except Exception as e:
                print(f"⚠️ Loop Error: {e}")

            # Sleep 5-10 minutes between cycles
            jitter_seconds = random.randint(300, 600)
            print(f"💤 Sleeping for {jitter_seconds // 60} min {jitter_seconds % 60} sec...\n")
            await asyncio.sleep(jitter_seconds)
