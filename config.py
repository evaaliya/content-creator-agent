import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

PRIVY_APP_ID = os.getenv("PRIVY_APP_ID")
PRIVY_APP_SECRET = os.getenv("PRIVY_APP_SECRET")

FARCASTER_FID = os.getenv("FARCASTER_FID")
FARCASTER_SIGNER_UUID = os.getenv("FARCASTER_SIGNER_UUID")
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY")