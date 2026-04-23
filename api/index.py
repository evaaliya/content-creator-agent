import asyncio
import os
import sys
from http.server import BaseHTTPRequestHandler

# Vercel-specific path fixing
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from agent.agent_loop import AutonomousAgent
    IMPORT_ERROR = None
except Exception as e:
    IMPORT_ERROR = str(e)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        
        if IMPORT_ERROR:
            self.wfile.write(f"❌ Import Error: {IMPORT_ERROR}".encode())
            return

        print("⏰ Vercel Cron triggered agent execution")
        
        try:
            # Run one cycle of the agent
            agent = AutonomousAgent()
            # Since Vercel is already running in an event loop or thread, 
            # we need to be careful with asyncio.
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            loop.run_until_complete(agent.run())
            
            self.wfile.write("✅ Agent run completed successfully".encode())
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            self.wfile.write(f"❌ Execution Error: {str(e)}".encode())
