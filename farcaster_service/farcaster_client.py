import httpx
import os
from config import FARCASTER_FID, NEYNAR_API_KEY


class FarcasterClient:
    def __init__(self):
        self.headers = {
            "accept": "application/json",
            "api_key": NEYNAR_API_KEY,
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.neynar.com/v2/farcaster"
        self.fid = FARCASTER_FID

    # ──────────────────── READ: My own casts (for metrics) ────────
    async def fetch_my_casts(self, limit: int = 50):
        """Fetch the agent's own casts with engagement data."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/feed/user/casts",
                    headers=self.headers,
                    params={"fid": self.fid, "limit": limit}
                )
                res.raise_for_status()
                data = res.json()
                casts = data.get("casts", [])
                print(f"📊 Fetched {len(casts)} of my own casts")
                return casts
            except Exception as e:
                print(f"Fetch my casts error: {e}")
                return []

    # ──────────────────── READ: Notifications (ALL types) ──────────
    async def fetch_notifications(self):
        """Fetch ALL notifications: mentions, replies, likes, recasts, follows."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/notifications",
                    headers=self.headers,
                    params={"fid": self.fid}  # No type filter = get everything
                )
                res.raise_for_status()
                data = res.json()
                notifs = data.get("notifications", [])
                
                # Count by type
                types = {}
                for n in notifs:
                    t = n.get("type", "unknown")
                    types[t] = types.get(t, 0) + 1
                type_str = ", ".join(f"{v} {k}" for k, v in types.items())
                print(f"📬 Fetched {len(notifs)} notifications ({type_str})")
                return notifs
            except Exception as e:
                print(f"Fetch notifications error: {e}")
                return []

    # ──────────────────── UTIL: Check if user is real ─────────────
    @staticmethod
    def is_real_user(author: dict) -> bool:
        """Filter out bots by checking score and activity."""
        score = author.get("score", 0)
        if isinstance(score, (int, float)) and score < 0.2:
            return False
        # Check for spam patterns in username
        username = author.get("username", "")
        if any(pat in username for pat in ["bot", "spam", "airdrop", "token"]):
            if "robot" not in username:  # don't filter "robot" as it's legit
                return False
        return True

    # ──────────────────── WRITE: Follow user ──────────────────────
    async def follow_user(self, target_fid: int):
        """Follow a user by FID."""
        from config import FARCASTER_SIGNER_UUID
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/user/follow",
                    headers=self.headers,
                    json={
                        "signer_uuid": os.getenv("FARCASTER_SIGNER_UUID"),
                        "target_fids": [target_fid]
                    }
                )
                res.raise_for_status()
                print(f"✅ Followed FID {target_fid}")
                return True
            except Exception as e:
                print(f"Follow error: {e}")
                return False

    # ──────────────────── WRITE: Like a cast ──────────────────────
    async def like_cast(self, cast_hash: str):
        """Like (react to) a cast."""
        from config import FARCASTER_SIGNER_UUID
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/reaction",
                    headers=self.headers,
                    json={
                        "signer_uuid": os.getenv("FARCASTER_SIGNER_UUID"),
                        "reaction_type": "like",
                        "target": cast_hash
                    }
                )
                res.raise_for_status()
                print(f"❤️ Liked {cast_hash[:10]}...")
                return True
            except Exception as e:
                print(f"Like error: {e}")
                return False

    # ──────────────────── WRITE: Recast ───────────────────────────
    async def recast(self, cast_hash: str):
        """Recast (share) a cast."""
        from config import FARCASTER_SIGNER_UUID
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/reaction",
                    headers=self.headers,
                    json={
                        "signer_uuid": os.getenv("FARCASTER_SIGNER_UUID"),
                        "reaction_type": "recast",
                        "target": cast_hash
                    }
                )
                res.raise_for_status()
                print(f"🔁 Recasted {cast_hash[:10]}...")
                return True
            except Exception as e:
                print(f"Recast error: {e}")
                return False

    # ──────────────────── READ: Trending (global) ────────────────
    async def fetch_trending_feed(self, limit: int = 25):
        """Fetch trending casts from the ENTIRE Farcaster network — not just subscriptions."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/feed/trending",
                    headers=self.headers,
                    params={"limit": limit}
                )
                res.raise_for_status()
                data = res.json()
                casts = data.get("casts", [])
                print(f"🌍 Fetched {len(casts)} trending casts")
                return casts
            except Exception as e:
                print(f"Fetch trending error: {e}")
                return []

    # ──────────────────── READ: Channel feed ─────────────────────
    async def fetch_channel_feed(self, channel_id: str, limit: int = 15):
        """Fetch casts from a specific Farcaster channel (e.g. 'ai', 'dev', 'crypto')."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/feed",
                    headers=self.headers,
                    params={
                        "feed_type": "filter",
                        "filter_type": "channel_id",
                        "channel_id": channel_id,
                        "limit": limit
                    }
                )
                res.raise_for_status()
                data = res.json()
                casts = data.get("casts", [])
                print(f"📡 Fetched {len(casts)} casts from /{channel_id}")
                return casts
            except Exception as e:
                print(f"Fetch channel /{channel_id} error: {e}")
                return []

    # ──────────────────── BACKWARD COMPAT ────────────────────────
    async def fetch_mentions(self):
        """Legacy alias — now calls fetch_notifications."""
        return await self.fetch_notifications()

    async def fetch_home_feed(self):
        """Legacy alias — now calls fetch_trending_feed."""
        return await self.fetch_trending_feed()

    # ──────────────────── WRITE: Publish cast ────────────────────
    async def publish_cast(self, text: str):
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/cast",
                    headers=self.headers,
                    json={"text": text, "signer_uuid": FARCASTER_SIGNER_UUID}
                )
                res.raise_for_status()
                print("✅ Cast published!")
                return res.json()
            except Exception as e:
                print(f"Publish cast error: {e}")
                return None

    # ──────────────────── WRITE: Reply to cast ───────────────────
    async def reply_cast(self, text: str, parent_hash: str):
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/cast",
                    headers=self.headers,
                    json={
                        "text": text,
                        "signer_uuid": os.getenv("FARCASTER_SIGNER_UUID"),
                        "parent": parent_hash
                    }
                )
                res.raise_for_status()
                print(f"✅ Reply published to {parent_hash[:10]}...")
                return res.json()
            except Exception as e:
                print(f"Reply error: {e}")
                return None