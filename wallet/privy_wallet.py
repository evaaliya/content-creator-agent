import asyncio
import subprocess
import json
import os
import datetime
import shutil

MAX_TIP_PER_TX = 0.00005    # ~$0.01 per tip (micro-tip)
MAX_DAILY_SPEND = 0.001     # ~$0.30 daily max

# Find npx path
NPX_PATH = shutil.which("npx") or "/usr/local/bin/npx"
CLI_PACKAGE = "@privy-io/agent-wallet-cli"


class PrivyWallet:
    def __init__(self):
        self.daily_spend = 0.0
        self.daily_reset_date = datetime.date.today()
        self.wallet_address = "0x2dBb1EcA97f2529233F7B3edC8fa893035Ec66cd"

    def _check_daily_reset(self):
        today = datetime.date.today()
        if today > self.daily_reset_date:
            self.daily_spend = 0.0
            self.daily_reset_date = today

    def _run_cli(self, args: list) -> dict:
        """Run a Privy Agent CLI command and return parsed output."""
        cmd = [NPX_PATH, CLI_PACKAGE] + args
        # Ensure node/npx are on PATH for subprocess
        env = dict(os.environ)
        env["PATH"] = "/usr/local/bin:/opt/homebrew/bin:" + env.get("PATH", "")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip()
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e)}

    async def get_balance(self) -> str:
        """Check wallet balances via CLI."""
        result = await asyncio.to_thread(self._run_cli, ["list-wallets"])
        if result["success"]:
            print(f"💰 Wallets:\n{result['stdout']}")
        else:
            print(f"⚠️ Balance check failed: {result['stderr']}")
        return result["stdout"]

    async def send_tip(self, recipient_address: str, amount: float) -> bool:
        """
        Send ETH tip via Privy Agent CLI.
        Uses eth_sendTransaction RPC method.
        
        Args:
            recipient_address: Ethereum address (0x...) of the recipient
            amount: Amount in ETH to send (e.g., 0.0001)
        """
        self._check_daily_reset()

        # Safety checks
        if amount > MAX_TIP_PER_TX:
            print(f"🚫 BLOCKED: Tip ${amount} exceeds max per tx (${MAX_TIP_PER_TX})")
            return False

        if self.daily_spend + amount > MAX_DAILY_SPEND:
            print(f"🚫 BLOCKED: Daily spend limit reached (${MAX_DAILY_SPEND})")
            return False

        if not recipient_address or not recipient_address.startswith("0x"):
            print(f"🚫 BLOCKED: Invalid address: {recipient_address}")
            return False

        # Convert ETH to wei hex
        wei = int(amount * 10**18)
        value_hex = hex(wei)

        # Build RPC command — Privy requires caip2 + params.transaction
        rpc_payload = json.dumps({
            "method": "eth_sendTransaction",
            "caip2": "eip155:42161",
            "params": {
                "transaction": {
                    "to": recipient_address,
                    "value": value_hex
                }
            }
        })

        print(f"💸 Tipping {amount} ETH to {recipient_address[:10]}...")

        result = await asyncio.to_thread(
            self._run_cli,
            ["rpc", "--json", rpc_payload]
        )

        if result["success"]:
            self.daily_spend += amount
            print(f"✅ Tip sent! {result['stdout']}")
            print(f"📊 Daily spend: ${self.daily_spend:.4f}/${MAX_DAILY_SPEND}")
            return True
        else:
            error = result["stderr"] or result["stdout"]
            print(f"❌ Tip failed: {error}")
            return False
