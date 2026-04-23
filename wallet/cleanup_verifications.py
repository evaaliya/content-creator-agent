import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()

NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY")
SIGNER_UUID = os.getenv("FARCASTER_SIGNER_UUID")
FARCASTER_FID = os.getenv("FARCASTER_FID")

OLD_ADDRESSES = [
    "0xE10482BC8CF4aE8c47628dfC7AF491d71d427454", # Custody
    "0x2dBb1EcA97f2529233F7B3edC8fa893035Ec66cd"  # Old Sandbox
]

async def cleanup():
    headers = {
        "api_key": NEYNAR_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        for addr in OLD_ADDRESSES:
            print(f"🗑️ Removing {addr}...")
            # Neynar DELETE /v2/farcaster/user/verification
            # Note: Neynar might require the payload in the body for DELETE or as query params.
            # According to docs, it's a DELETE request with signer_uuid and address.
            try:
                res = await client.request(
                    "DELETE",
                    "https://api.neynar.com/v2/farcaster/user/verification",
                    headers=headers,
                    json={
                        "signer_uuid": SIGNER_UUID,
                        "address": addr
                    }
                )
                if res.status_code == 200:
                    print(f"✅ Removed {addr}")
                else:
                    print(f"❌ Failed to remove {addr}: {res.status_code} {res.text}")
            except Exception as e:
                print(f"⚠️ Error: {e}")

        # Verify remaining
        print("\n📋 Checking remaining verifications...")
        res = await client.get(
            f"https://api.neynar.com/v2/farcaster/user/bulk?fids={FARCASTER_FID}",
            headers=headers
        )
        user = res.json()["users"][0]
        eth = user.get("verified_addresses", {}).get("eth_addresses", [])
        print(f"✅ Current verified addresses: {eth}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(cleanup())
