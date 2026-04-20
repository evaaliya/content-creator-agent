import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from agent.agent_loop import AutonomousAgent

def print_banner():
    try:
        if os.path.exists("logo.txt"):
            with open("logo.txt", "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("🚀 Agent sequence initiated.")
    except Exception:
        print("🚀 Agent sequence initiated.")

async def main():
    print_banner()
    agent = AutonomousAgent()
    await agent.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🔌 Agent safely terminated by user.")
