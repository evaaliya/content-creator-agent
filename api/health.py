"""Health check + wallet balance endpoint."""
import sys
import os
import json
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """GET /api/health — agent status + wallet balances."""
        from wallet.lifi_balances import check_balances

        address = os.getenv("PRIVY_WALLET_ADDRESS", "")
        fid = os.getenv("FARCASTER_FID", "")

        result = {
            "status": "alive",
            "agent": "@matricula",
            "fid": fid,
            "wallet": address[:6] + "..." + address[-4:] if address else "not configured",
        }

        # Add balances
        try:
            balances = check_balances(address)
            if "error" not in balances:
                result["balances"] = balances
            else:
                result["balance_error"] = balances["error"]
        except Exception as e:
            result["balance_error"] = str(e)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, indent=2).encode())
