"""
Farcaster Wallet Linker — Verifies the custody wallet on @matricula's Farcaster profile.

Uses EIP-712 VerificationClaim signed by the custody wallet (mnemonic),
then submits to Neynar POST /v2/farcaster/user/verification.

Run once: python wallet/farcaster_wallet_linker.py
"""
import os
import sys
import json
import time
import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data
from dotenv import load_dotenv

# Load env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY")
FARCASTER_FID = int(os.getenv("FARCASTER_FID"))
SIGNER_UUID = os.getenv("FARCASTER_SIGNER_UUID")
MNEMONIC = os.getenv("AGENT_MNEMONIC")


def get_custody_account():
    """Derive custody wallet from mnemonic."""
    Account.enable_unaudited_hdwallet_features()
    acct = Account.from_mnemonic(MNEMONIC)
    print(f"🔑 Custody address: {acct.address}")
    return acct


def get_latest_block_hash() -> str:
    """Get latest Optimism block hash (needed for verification claim)."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_getBlockByNumber",
        "params": ["latest", False]
    }
    res = httpx.post("https://mainnet.optimism.io", json=payload, timeout=15)
    block = res.json()["result"]
    block_hash = block["hash"]
    print(f"📦 Block hash: {block_hash}")
    return block_hash


def sign_verification_claim(acct, block_hash: str) -> str:
    """Sign EIP-712 VerificationClaim with the custody wallet."""
    print("✍️ Signing EIP-712 verification claim...")

    # Official Farcaster salt for verification claims
    FARCASTER_SALT = "0xf2d857f4a3edcb9b78b4d503bfe733db1e3f6cdc2b7971ee739626c97e86a558"

    structured_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "salt", "type": "bytes32"},
            ],
            "VerificationClaim": [
                {"name": "fid", "type": "uint256"},
                {"name": "address", "type": "address"},
                {"name": "blockHash", "type": "bytes32"},
                {"name": "network", "type": "uint8"},
            ],
        },
        "domain": {
            "name": "Farcaster Verify Ethereum Address",
            "version": "2.0.0",
            "salt": FARCASTER_SALT,
        },
        "primaryType": "VerificationClaim",
        "message": {
            "fid": FARCASTER_FID,
            "address": acct.address,
            "blockHash": block_hash,  # Keep as hex string
            "network": 1,  # FARCASTER_NETWORK_MAINNET
        },
    }

    signed = Account.sign_typed_data(
        acct.key,
        full_message=structured_data
    )
    signature = "0x" + signed.signature.hex()
    print(f"📝 Signature: {signature[:22]}...")
    return signature


def submit_verification(address: str, block_hash: str, signature: str):
    """Submit verification to Neynar API."""
    print("📤 Submitting to Neynar...")

    headers = {
        "x-api-key": NEYNAR_API_KEY,
        "api_key": NEYNAR_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {
        "signer_uuid": SIGNER_UUID,
        "address": address,
        "block_hash": block_hash,
        "eth_signature": signature,
        "verification_type": 0,  # 0 = EOA
        "chain_id": 0,  # 0 = Farcaster default
    }

    res = httpx.post(
        "https://api.neynar.com/v2/farcaster/user/verification",
        headers=headers,
        json=payload,
        timeout=30
    )

    result = res.json()
    if res.status_code == 200:
        print("✅ Wallet verified on Farcaster profile!")
        print(json.dumps(result, indent=2))
        return True
    else:
        print(f"❌ Failed ({res.status_code}): {json.dumps(result, indent=2)}")
        # Try with chain_id variations
        for chain_id in [10, 1]:
            print(f"\n🔄 Retrying with chain_id={chain_id}...")
            payload["chain_id"] = chain_id
            res2 = httpx.post(
                "https://api.neynar.com/v2/farcaster/user/verification",
                headers=headers,
                json=payload,
                timeout=30
            )
            result2 = res2.json()
            if res2.status_code == 200:
                print(f"✅ Worked with chain_id={chain_id}!")
                print(json.dumps(result2, indent=2))
                return True
            else:
                print(f"   ❌ chain_id={chain_id}: {result2.get('message', 'unknown error')}")
        return False


def verify_result():
    """Check if verification was added."""
    res = httpx.get(
        f"https://api.neynar.com/v2/farcaster/user/bulk?fids={FARCASTER_FID}",
        headers={"api_key": NEYNAR_API_KEY, "accept": "application/json"},
        timeout=15
    )
    user = res.json()["users"][0]
    eth = user.get("verified_addresses", {}).get("eth_addresses", [])
    print(f"\n📋 Verified addresses: {eth}")
    return eth


if __name__ == "__main__":
    print("=" * 50)
    print("🔗 Farcaster Wallet Verification for @matricula")
    print("=" * 50)

    acct = get_custody_account()
    block_hash = get_latest_block_hash()
    signature = sign_verification_claim(acct, block_hash)
    success = submit_verification(acct.address, block_hash, signature)

    if success:
        time.sleep(3)  # Wait for propagation
        verify_result()
    else:
        print("\n⚠️ Verification failed. This may require a different approach.")
        print("   The custody address may already be implicitly linked.")