import asyncio
import subprocess
import json
import os
import datetime

# Limits for autonomous spending (in ETH)
MAX_TIP_PER_TX = 0.00000431  # ~0.01 USDC
MAX_DAILY_SPEND = 0.02

# Replaced npx CLI with Node.js Server SDK wrapper

class PrivyWallet:
    def __init__(self):
        self.daily_spend = 0.0
        self.daily_reset_date = datetime.date.today()
        self.wallet_address = os.getenv("PRIVY_WALLET_ADDRESS", "")

    def _check_daily_reset(self):
        today = datetime.date.today()
        if today > self.daily_reset_date:
            self.daily_spend = 0.0
            self.daily_reset_date = today
    def sign_message(self, message: str) -> str:
        """Sign a message using Privy Server SDK (personal_sign)."""
        payload = {"message": message}
        result = self._run_node("personal_sign", payload)
        if result["success"]:
            return result["result"]
        else:
            raise RuntimeError(f"Signing failed: {result.get('error')}")

    def _run_node(self, command: str, payload_dict: dict) -> dict:
        """Run Privy Server SDK wrapper and return parsed output."""
        script = os.path.join(os.path.dirname(__file__), "privy_server.mjs")
        cmd = ["node", script, command, json.dumps(payload_dict)]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )
            
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                try:
                    data = json.loads(err)
                    return {"success": False, "error": data.get("error", err)}
                except Exception:
                    return {"success": False, "error": err}
            
            output = result.stdout.strip()
            lines = [line for line in output.split('\n') if line.strip().startswith('{')]
            if lines:
                data = json.loads(lines[-1])
            else:
                data = json.loads(output)
            return {"success": data.get("success", False), "result": data.get("result", output)}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_balance(self) -> str:
        """Check wallet balances via LI.FI SDK instead of Privy CLI."""
        from wallet.lifi_balances import check_balances
        balances = await asyncio.to_thread(check_balances, self.wallet_address)
        if "error" in balances:
            print(f"⚠️ Balance check failed: {balances['error']}")
            return balances['error']
            
        res = "💰 Wallets:\n"
        for chain, data in balances.items():
            if float(data.get("eth", 0)) > 0 or float(data.get("usdc", 0)) > 0:
                res += f"📍 {data['chain']}: {data['eth']} ETH | {data['usdc']} USDC\n"
        print(res)
        return res

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

        # Convert ETH to wei string
        wei = int(amount * 10**18)
        value_str = str(wei)

        payload = {
            "transaction": {
                "to": recipient_address,
                "value": value_str
            }
        }

        print(f"💸 Tipping {amount} ETH to {recipient_address[:10]}...")

        result = await asyncio.to_thread(
            self._run_node,
            "executeAgentAction", payload
        )

        if result["success"]:
            self.daily_spend += amount
            tx_hash = result["result"]
            print(f"✅ Tip sent! Hash: {tx_hash}")
            print(f"📊 Daily spend: ${self.daily_spend:.4f}/${MAX_DAILY_SPEND}")
            return True
        else:
            error = result.get("error", "Unknown error")
            print(f"❌ Tip failed: {error}")
            return False
