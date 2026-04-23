import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

COHERE_API_KEY = os.getenv("COHERE_API_KEY")

PRIVY_APP_ID = os.getenv("PRIVY_APP_ID")
PRIVY_APP_SECRET = os.getenv("PRIVY_APP_SECRET")

FARCASTER_FID = os.getenv("FARCASTER_FID")
FARCASTER_FID = os.getenv("FARCASTER_FID")
FARCASTER_SIGNER_PRIVATE_KEY = os.getenv("FARCASTER_SIGNER_PRIVATE_KEY")
FARCASTER_SIGNER_PUBLIC_KEY = os.getenv("FARCASTER_SIGNER_PUBLIC_KEY")
FARCASTER_SIGNER_UUID = os.getenv("FARCASTER_SIGNER_UUID")
NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY")

def get_data_path(filename):
    """Return writable path for data files. Use /tmp on Vercel."""
    if os.getenv("VERCEL"):
        return os.path.join("/tmp", filename)
    # Default to current directory or specific data dir
    return os.path.join(os.path.dirname(__file__), filename)