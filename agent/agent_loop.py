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
from brain.decision_engine import make_decision, analyze_cast_for_engagement, set_goal_context, set_memory_context, clear_memory_context
from metrics.engagement_tracker import extract_metrics, update_history, get_stats
from brain.reflection import reflect, needs_reflection
from brain.energy_manager import get_energy_manager
from goals.goal_tracker import evaluate as evaluate_goals, dashboard, get_goal_prompt
from goals.spend_log import get_summary as get_spend_summary

# ── Limits ──
MAX_DAILY_CASTS = 30
CHANNELS_TO_MONITOR = ["ai", "dev", "crypto", "founders"]
FEED_ENGAGEMENT_LIMIT = 15  # engage with up to 15 casts per run


class AutonomousAgent:
    def __init__(self):
        self.fc = FarcasterClient()
        self.wallet = PrivyWallet()
        self.mem = VectorMemory()

        # Tracking
        self.daily_casts = 0
        self.daily_reset_date = datetime.date.today()
        
        # Load replied hashes from file to avoid repeating across runs
        from config import get_data_path
        self._hashes_file = get_data_path("replied_hashes.json")
        try:
            import json
            with open(self._hashes_file, "r") as f:
                self.replied_hashes = set(json.load(f))
        except Exception:
            self.replied_hashes = set()
            
        self._posted_research_today = False

    def _check_daily_reset(self):
        """Reset counter at midnight."""
        today = datetime.date.today()
        if today > self.daily_reset_date:
            print("🔄 New day — resetting daily cast counter")
            self.daily_casts = 0
            self.daily_reset_date = today
            self.replied_hashes.clear()
            self._posted_research_today = False

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
                    import json
                    with open(self._hashes_file, "w") as f:
                        json.dump(list(self.replied_hashes), f)
                    print(f"📊 Daily casts: {self.daily_casts}/{MAX_DAILY_CASTS}")

            elif a_type == "tip_user":
                await self.wallet.send_tip(target, amt)

            elif a_type == "like_cast":
                await self.fc.like_cast(target)

            elif a_type == "recast":
                await self.fc.recast(target)

            elif a_type == "follow_user":
                # target is the user's FID
                try:
                    fid = int(target)
                    await self.fc.follow_user(fid)
                    print(f"   👤 Proactively following FID: {fid}")
                except Exception as e:
                    print(f"   ⚠️ Could not follow user {target}: {e}")

            elif a_type == "none":
                pass

    # ──────────────────── STEP 1: Make one original cast ──────────
    async def post_original_cast(self):
        print("\n── ✍️ Step 1: Making original cast ──")
        if not self._can_cast():
            print("   🚫 Daily limit reached")
            return

        # Retrieve past experience for smarter posting
        past_successes = self.mem.recall_what_worked("AI web3 engagement")
        if past_successes:
            memory_text = "\n".join([f"- {m['content']}" for m in past_successes])
            set_memory_context(memory_text)
        else:
            set_memory_context("No past experience yet — experiment freely.")

        memories = self.mem.remember_for_post_creation("what should I post about today")
        decision = make_decision([], [], memories)

        # Clear memory context so replies don't get it
        clear_memory_context()

        actions = decision.get("actions", [])
        if actions:
            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            await self.execute_actions(actions)

            # Store own cast in memory for learning
            for a in actions:
                if a.get("type") == "publish_cast" and a.get("content"):
                    self.mem.remember_my_cast(
                        cast_text=a["content"],
                        cast_hash="pending",  # Hash not yet available
                        metrics={"posted_at": str(datetime.datetime.utcnow())}
                    )
                    print("   💾 Own cast stored in memory")
        else:
            print("   ⏭️ No cast decision")

    # ──────────────────── STEP 1.5: Share research ──────────────────
    async def post_research_cast(self):
        print("\n── 📚 Step 1.5: Research cast ──")
        if not self._can_cast():
            print("   🚫 Daily limit reached")
            return

        try:
            from research.paper_caster import pick_and_cast
            result = await pick_and_cast()

            if result and result.get("content"):
                cast_text = result["content"]
                print(f"   📝 Research cast: {cast_text[:80]}...")

                # Post it
                res = await self.fc.publish_cast(cast_text)
                if res:
                    self.daily_casts += 1
                    self._posted_research_today = True
                    print("   ✅ Research cast published!")

                    # Store in memory
                    source_item = result.get("source_item", {})
                    self.mem.remember_my_cast(
                        cast_text=cast_text,
                        cast_hash="research",
                        metrics={
                            "type": "research",
                            "source": source_item.get("source", "unknown"),
                            "title": source_item.get("title", ""),
                            "posted_at": str(datetime.datetime.utcnow())
                        }
                    )
            else:
                print("   ⏭️ No interesting research found this cycle")
        except Exception as e:
            print(f"   ⚠️ Research cast error: {e}")

    # ──────────────────── STEP 2: Respond to ALL notifications ─────
    async def handle_notifications(self):
        print("\n── 📬 Step 2: Checking notifications ──")
        notifs = await self.fc.fetch_notifications()

        if not notifs:
            print("   No new notifications")
            return

        followed_back = 0
        replied = 0
        skipped_bots = 0

        for notif in notifs[:20]:
            notif_type = notif.get("type", "unknown")
            cast = notif.get("cast", notif)

            # ── FOLLOWS: Follow back real users ──
            if notif_type == "follows":
                follows = notif.get("follows", [])
                for f in (follows if isinstance(follows, list) else []):
                    follower = f.get("user", f)
                    if not self.fc.is_real_user(follower):
                        skipped_bots += 1
                        continue
                    fid = follower.get("fid")
                    username = follower.get("username", "?")
                    if fid:
                        print(f"   👤 New follower: @{username} — following back")
                        await self.fc.follow_user(fid)
                        followed_back += 1
                continue

            # ── LIKES / RECASTS: Track but don't reply ──
            if notif_type in ("likes", "recasts"):
                continue  # Just logged by fetch_notifications count

            # ── MENTIONS / REPLIES: Respond if real user ──
            if notif_type in ("mention", "reply"):
                if not self._can_cast():
                    break

                cast_hash = cast.get("hash", "")
                if cast_hash in self.replied_hashes:
                    continue

                author = cast.get("author", {})
                username = author.get("username", "?")
                text = cast.get("text", "")

                # Skip bots
                if not self.fc.is_real_user(author):
                    print(f"   🤖 Skipping bot @{username}")
                    skipped_bots += 1
                    continue

                # Skip spam mentions (token/airdrop bait)
                if any(spam in text.lower() for spam in ["token bag", "reward", "airdrop", "claim your"]):
                    print(f"   🚫 Skipping spam from @{username}")
                    skipped_bots += 1
                    continue

                print(f"   💬 [{notif_type}] @{username}: {text[:80]}...")

                memories = self.mem.remember_for_post_creation(text)
                decision = make_decision([cast], [], memories)

                print(f"   🧠 {decision.get('thoughts', '')[:100]}")
                actions = decision.get("actions", [])
                await self.execute_actions(actions)
                
                # Auto-follow the user we replied to
                if any(a.get("type") != "none" for a in actions):
                    author_fid = author.get("fid")
                    if author_fid:
                        await self.fc.follow_user(author_fid)
                
                replied += 1

                # Store interaction in memory
                self.mem.remember_post(text, {"fid": str(author.get("fid", ""))})

        print(f"   📊 Replied: {replied}, Followed back: {followed_back}, Bots skipped: {skipped_bots}")

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

            # Skip empty casts
            if not text.strip():
                continue

            print(f"\n   👀 @{username}: {text[:80]}...")

            memories = self.mem.remember_for_post_creation(text)
            decision = analyze_cast_for_engagement(cast, memories)

            action_type = decision.get("actions", [{}])[0].get("type", "none")

            if action_type == "none":
                print("   ⏭️ Skip")
                continue

            print(f"   🧠 {decision.get('thoughts', '')[:100]}")
            actions = decision.get("actions", [])
            await self.execute_actions(actions)
            
            # Auto-follow the user we interacted with
            author_fid = author.get("fid")
            if author_fid:
                await self.fc.follow_user(author_fid)
                
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

    # ──────────────────── STEP 0.5: Check Goals ─────────────────
    async def check_goals(self):
        print("\n── 🎯 Step 0.5: Goal evaluation ──")
        eng_stats = get_stats()
        spend_stats = get_spend_summary()

        # Get wallet balance
        wallet_balance = 0.0
        try:
            balance_str = await self.wallet.get_balance()
            # Try to parse balance from output
            import re
            match = re.search(r'(\d+\.\d+)\s*ETH', balance_str)
            if match:
                wallet_balance = float(match.group(1))
        except Exception:
            pass

        report = await evaluate_goals(
            engagement_stats=eng_stats,
            spend_log=spend_stats,
            wallet_balance=wallet_balance,
            daily_spend=self.wallet.daily_spend
        )

        # Print dashboard
        print(dashboard(report))

        # Inject goal context into decision engine
        goal_prompt = get_goal_prompt(report)
        set_goal_context(goal_prompt)

        return report

    # ──────────────────── MAIN RUN (single execution) ─────────────
    async def run(self):
        self._check_daily_reset()
        energy = get_energy_manager()

        print(f"\n{'='*50}")
        print("🤖 @matricula — single run")
        print(f"   {energy.status_line()}")
        print(f"{'='*50}")

        # Step 0: Reflect (10% chance to run to save tokens, skip if energy is low)
        if not energy.should_skip_heavy() and random.randint(1, 10) == 1:
            await self.self_reflect()
        else:
            print("\n── 🪞 Step 0: Skipped (runs rarely to save tokens) ──")

        # Step 0.5: Evaluate goals (cheap — no LLM call)
        goal_report = await self.check_goals()

        if not self._can_cast():
            print("🚫 Daily cast limit reached.")
            return

        # Step 1: Make one original cast
        await self.post_original_cast()

        # Step 1.5: Share research (once per day)
        if not self._posted_research_today and not energy.should_skip_heavy():
            await self.post_research_cast()
        elif self._posted_research_today:
            print("\n── 📚 Step 1.5: Research already posted today ──")

        # Step 2: Respond to notifications/reactions (always do this)
        await self.handle_notifications()

        # Step 3: Engage with feed (skip if energy is critical)
        if energy.should_skip_heavy():
            print(f"\n── 🌍 Step 3: Skipped (energy {energy.energy_ratio():.0%} — survival mode) ──")
        else:
            await self.engage_feed()

        print(f"\n{'='*50}")
        print(f"✅ Run complete. Casts: {self.daily_casts}/{MAX_DAILY_CASTS}")
        print(f"   Priority: {goal_report.get('priority', '?').upper()}")
        print(f"   {energy.status_line()}")
        print(f"{'='*50}")

    # ──────────────────── LEGACY: Loop mode (optional) ────────────
    async def start(self):
        """Run once and exit. No infinite loop."""
        print("🚀 Agent sequence initiated.")
        await self.run()
        print("👋 Done.")
