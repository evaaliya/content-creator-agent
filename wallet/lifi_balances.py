"""
LI.FI Balance Checker — Cross-chain wallet balances via LI.FI SDK.

Calls Node.js wrapper (lifi_check.mjs) which uses the official @lifi/sdk.
"""
import subprocess
import json
import os


def check_balances(address: str = None) -> dict:
    """Check ETH/USDC/token balances across all chains via LI.FI SDK."""
    if not address:
        address = os.getenv("PRIVY_WALLET_ADDRESS")
    if not address:
        return {"error": "No wallet address configured"}

    script = os.path.join(os.path.dirname(__file__), "lifi_check.mjs")

    try:
        result = subprocess.run(
            ["node", script, address],
            capture_output=True, text=True, timeout=30,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )

        if result.returncode != 0:
            err = result.stderr.strip()
            try:
                return json.loads(err)
            except:
                return {"error": err or "LI.FI check failed"}

        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {"error": "LI.FI balance check timed out"}
    except Exception as e:
        return {"error": str(e)}


def print_dashboard(address: str = None):
    """Print wallet balance dashboard."""
    if not address:
        address = os.getenv("PRIVY_WALLET_ADDRESS")

    print(f"\n💰 Wallet: {address[:6]}...{address[-4:]}")
    print("=" * 50)

    balances = check_balances(address)
    if "error" in balances:
        print(f"  ⚠️ {balances['error']}")
        return balances

    for chain_name, data in balances.items():
        eth = float(data.get("eth", "0"))
        usdc = float(data.get("usdc", "0"))
        others = data.get("otherTokens", [])

        has_funds = eth > 0 or usdc > 0 or others
        if has_funds:
            print(f"\n  📍 {data.get('chain', chain_name)}:")
            if eth > 0:
                print(f"     ETH: {eth:.6f}")
            if usdc > 0:
                print(f"     USDC: {usdc:.2f}")
            for t in others:
                print(f"     {t['symbol']}: {t['amount']}")

    print("=" * 50)
    return balances
