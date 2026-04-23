import asyncio
import os
import sys
from http.server import BaseHTTPRequestHandler

# Add parent directory to path to find all modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.agent_loop import AutonomousAgent

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # This is what Vercel Cron calls
        auth_header = self.headers.get('Authorization')
        
        # Check CRON_SECRET to prevent unauthorized calls (optional but recommended)
        # if auth_header != f"Bearer {os.environ.get('CRON_SECRET')}":
        #     self.send_response(401)
        #     self.end_headers()
        #     return

        print("⏰ Vercel Cron triggered agent execution")
        
        try:
            # Run one cycle of the agent
            agent = AutonomousAgent()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(agent.run())
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("✅ Agent run completed successfully".encode())
        except Exception as e:
            print(f"❌ Error during cron execution: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"❌ Error: {str(e)}".encode())
