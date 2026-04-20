import httpx
from config import FARCASTER_SIGNER_UUID, FARCASTER_FID, NEYNAR_API_KEY


class FarcasterClient:
    def __init__(self):
        self.headers = {
            "accept": "application/json",
            "api_key": NEYNAR_API_KEY,
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.neynar.com/v2/farcaster"
        self.fid = FARCASTER_FID

    # ──────────────────── READ: Notifications ────────────────────
    async def fetch_notifications(self):
        """Fetch mentions, replies, and reactions directed at our FID."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/notifications",
                    headers=self.headers,
                    params={"fid": self.fid, "type": "mentions,replies"}
                )
                res.raise_for_status()
                data = res.json()
                notifs = data.get("notifications", [])
                print(f"📬 Fetched {len(notifs)} notifications")
                return notifs
            except Exception as e:
                print(f"Fetch notifications error: {e}")
                return []

    # ──────────────────── READ: Trending (global) ────────────────
    async def fetch_trending_feed(self, limit: int = 25):
        """Fetch trending casts from the ENTIRE Farcaster network — not just subscriptions."""
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                res = await client.get(
                    f"{self.base_url}/feed/trending",
                    headers=self.headers,
                    params={"limit": limit, "time_window": "24h"}
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
                        "signer_uuid": FARCASTER_SIGNER_UUID,
                        "parent": parent_hash
                    }
                )
                res.raise_for_status()
                print(f"✅ Reply published to {parent_hash[:10]}...")
                return res.json()
            except Exception as e:
                print(f"Reply error: {e}")
                return None