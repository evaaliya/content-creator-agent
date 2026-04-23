"""
Verify the Privy Agent Wallet on @matricula's Farcaster profile.

Signs EIP-712 VerificationClaim via Privy CLI (eth_signTypedData_v4)
then submits to Neynar.

Run once: python wallet/verify_privy_wallet.py
"""
import os
import sys
import json
import time
import subprocess
import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

NEYNAR_API_KEY = os.getenv("NEYNAR_API_KEY")
FARCASTER_FID = int(os.getenv("FARCASTER_FID"))
SIGNER_UUID = os.getenv("FARCASTER_SIGNER_UUID")
PRIVY_ADDRESS = os.getenv("PRIVY_WALLET_ADDRESS", "")

# Official Farcaster salt
FARCASTER_SALT = "0xf2d857f4a3edcb9b78b4d503bfe733db1e3f6cdc2b7971ee739626c97e86a558"


def get_block_hash() -> str:
    """Get latest Optimism block hash."""
    payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "eth_getBlockByNumber",
        "params": ["latest", False]
    }
    res = httpx.post("https://mainnet.optimism.io", json=payload, timeout=15)
    bh = res.json()["result"]["hash"]
    print(f"📦 Block hash: {bh}")
    return bh


def sign_with_privy(block_hash: str) -> str:
    """Sign EIP-712 VerificationClaim via Privy CLI."""
    print("✍️ Signing with Privy wallet...")

    # Privy CLI uses snake_case for typed_data fields
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "salt", "type": "bytes32"}
            ],
            "VerificationClaim": [
                {"name": "fid", "type": "uint256"},
                {"name": "address", "type": "address"},
                {"name": "blockHash", "type": "bytes32"},
                {"name": "network", "type": "uint8"}
            ]
        },
        "domain": {
            "name": "Farcaster Verify Ethereum Address",
            "version": "2.0.0",
            "salt": FARCASTER_SALT
        },
        "primary_type": "VerificationClaim",
        "message": {
            "fid": str(FARCASTER_FID),
            "address": PRIVY_ADDRESS,
            "blockHash": block_hash,
            "network": "1"
        }
    }

    script = os.path.join(os.path.dirname(__file__), "privy_server.mjs")
    payload = {"typed_data": typed_data}
    
    result = subprocess.run(
        ["node", script, "eth_signTypedData_v4", json.dumps(payload)],
        capture_output=True, text=True, timeout=30,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )

    if result.returncode != 0:
        print(f"❌ Privy Node error: {result.stderr or result.stdout}")
        # Try personal_sign as fallback
        print("🔄 Trying personal_sign fallback...")
        return sign_with_personal_sign(block_hash)

    output = result.stdout.strip()
    print(f"📝 Raw output: {output[:80]}...")

    try:
        data = json.loads(output)
        if data.get("success"):
            return data.get("result")
    except json.JSONDecodeError:
        pass

    # Fallback: find 0x... signature in raw text
    import re
    match = re.search(r'(0x[a-fA-F0-9]{130,})', output)
    if match:
        return match.group(1)

    # If nothing works, try personal_sign
    print("🔄 Trying personal_sign fallback...")
    return sign_with_personal_sign(block_hash)


def sign_with_personal_sign(block_hash: str) -> str:
    """Fallback: use eth_account to hash the typed data, sign hash via personal_sign."""
    from eth_account.messages import encode_typed_data

    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "salt", "type": "bytes32"}
            ],
            "VerificationClaim": [
                {"name": "fid", "type": "uint256"},
                {"name": "address", "type": "address"},
                {"name": "blockHash", "type": "bytes32"},
                {"name": "network", "type": "uint8"}
            ]
        },
        "domain": {
            "name": "Farcaster Verify Ethereum Address",
            "version": "2.0.0",
            "salt": FARCASTER_SALT
        },
        "primaryType": "VerificationClaim",
        "message": {
            "fid": FARCASTER_FID,
            "address": PRIVY_ADDRESS,
            "blockHash": block_hash,
            "network": 1
        }
    }

    # Compute the EIP-712 hash
    structured = encode_typed_data(full_message=typed_data)
    msg_hash = structured.body.hex()
    print(f"   Hash to sign: 0x{msg_hash[:20]}...")

    # Sign the raw hash via Privy Server SDK
    hex_msg = "0x" + msg_hash
    
    script = os.path.join(os.path.dirname(__file__), "privy_server.mjs")
    payload = {"message": hex_msg}
    
    print(f"   Calling personal_sign...")
    result = subprocess.run(
        ["node", script, "personal_sign", json.dumps(payload)],
        capture_output=True, text=True, timeout=30,
        cwd=os.path.dirname(os.path.dirname(__file__))
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"personal_sign failed: {result.stderr or result.stdout}")

    output = result.stdout.strip()
    try:
        data = json.loads(output)
        if data.get("success"):
            return data.get("result")
        return output
    except json.JSONDecodeError:
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('0x') and len(line) >= 130:
                return line
        return output


def submit_to_neynar(address: str, block_hash: str, signature: str) -> bool:
    """Submit verification to Neynar."""
    print("📤 Submitting to Neynar...")

    headers = {
        "x-api-key": NEYNAR_API_KEY,
        "api_key": NEYNAR_API_KEY,
        "Content-Type": "application/json",
    }

    payload = {
        "signer_uuid": SIGNER_UUID,
        "address": address,
        "block_hash": block_hash,
        "eth_signature": signature,
        "verification_type": 0,
        "chain_id": 0,
    }

    res = httpx.post(
        "https://api.neynar.com/v2/farcaster/user/verification",
        headers=headers, json=payload, timeout=30
    )
    result = res.json()

    if res.status_code == 200:
        print("✅ Privy wallet verified!")
        print(json.dumps(result, indent=2))
        return True
    else:
        print(f"❌ Failed ({res.status_code}): {json.dumps(result, indent=2)}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print(f"🔗 Verifying Privy wallet {PRIVY_ADDRESS}")
    print("=" * 50)

    block_hash = get_block_hash()
    signature = sign_with_privy(block_hash)
    print(f"📝 Signature: {signature[:22]}...")
    success = submit_to_neynar(PRIVY_ADDRESS, block_hash, signature)

    if success:
        time.sleep(3)
        res = httpx.get(
            f"https://api.neynar.com/v2/farcaster/user/bulk?fids={FARCASTER_FID}",
            headers={"api_key": NEYNAR_API_KEY},
            timeout=15
        )
        eth = res.json()["users"][0].get("verified_addresses", {}).get("eth_addresses", [])
        print(f"\n📋 All verified addresses: {eth}")
