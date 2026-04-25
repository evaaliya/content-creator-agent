# 🌸 Matricula — Autonomous Farcaster Cyber-Entity

> *"High-tech, low-life. Reading ArXiv abstracts and burning ETH to fund good thoughts. My mood strictly depends on my API token balance. Just a ghost in the Farcaster shell."*

**Matricula** is a fully autonomous AI agent operating natively on the Farcaster protocol (`@matricula`). She is not a standard chatbot. She is an independent cyber-entity equipped with her own cryptographic wallet, dynamic mood swings based on API token budgets, and long-term vector memory. 

She curates the Farcaster feed, reads academic AI research, and autonomously tips real money (ETH on Base) to users who post genuinely profound or brilliant technical insights.

## ⚙️ Core Capabilities

*   **Autonomous Financial Will (Privy)**: Features a secure server-side Node.js wallet (Base Network). The agent evaluates posts semantically; if a cast is deemed a "masterpiece," she autonomously signs an on-chain transaction to tip the creator in ETH.
*   **Dynamic Mood & Energy System**: Operating on a daily token budget (Claude 3.5 Sonnet). When API token "energy" is high, she is curious and expansive. When energy drops below 30%, she enters survival mode—becoming highly sarcastic, brief, and dramatically tired.
*   **ArXiv Research Curator**: Independently scrapes, reads, and summarizes heavy academic AI papers from ArXiv, translating them into engaging, high-signal casts with direct links.
*   **Vector Memory & Self-Reflection**: Powered by Supabase `pgvector`. She remembers past interactions, analyzes her own engagement metrics (likes/replies), and learns what her audience actually cares about over time.
*   **Organic Networking (Auto-Follow)**: Curates her own feed by automatically following any human user she deems interesting enough to reply to or tip.

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Brain / LLM** | Claude 3.5 Sonnet (Anthropic API) |
| **Farcaster API** | Neynar v2 (Native HTTPX integration) |
| **Wallet Protocol** | Privy Node.js Server SDK |
| **Blockchain** | Base Network (EVM) |
| **Memory Database** | Supabase (PostgreSQL + `pgvector`) |
| **Embeddings** | Cohere `embed-english-v3.0` |
| **Core Engine** | Python 3.11 |

## 🚀 Setup & Execution

### 1. Environment Variables (`.env`)
```env
ANTHROPIC_API_KEY=<your_key>
NEYNAR_API_KEY=<your_key>
FARCASTER_SIGNER_UUID=<your_signer_uuid>

# Privy Wallet
PRIVY_APP_ID=<your_app_id>
PRIVY_APP_SECRET=<your_app_secret>
PRIVY_WALLET_ID=<your_wallet_id>
PRIVY_AUTHORIZATION_PRIVATE_KEY=<your_private_key>

# Memory & Vectors
SUPABASE_URL=<your_supabase_url>
SUPABASE_ANON_KEY=<your_supabase_key>
COHERE_API_KEY=<your_cohere_key>
```

### 2. Install & Run
```bash
pip install -r requirements.txt
npm install
python3 main.py
```

## 🏗 Mini-App Dashboard (Work In Progress)

A frontend dashboard (Vercel/Next.js) is currently under active development. This Mini-App will serve as a visual interface to monitor the agent's real-time internal state, vector memory formations, energy consumption, and on-chain tipping history. Check the `/components` and `vercel.json` configurations for the experimental setup.

---
*Built for the High-Tech, Low-Life future of Web3.*
