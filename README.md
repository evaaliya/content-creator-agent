# 🤖 Matricula — Autonomous Farcaster Agent

An AI-powered autonomous agent that operates its own Farcaster account (`@matricula`). It reads trending casts, replies with context-aware responses, explores channels, and tips quality content creators with ETH — all without human intervention.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Agent Loop                        │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Phase 1  │  │ Phase 2  │  │     Phase 3       │  │
│  │ Notifs   │→ │ Trending │→ │ Channel Explorer  │  │
│  └────┬─────┘  └────┬─────┘  └────────┬──────────┘  │
│       └──────────────┴────────────────┘              │
│                      ↓                               │
│              Decision Engine (Claude)                │
│                      ↓                               │
│         ┌────────────┴────────────┐                  │
│         │                         │                  │
│    Publish / Reply           Tip User                │
│    (Neynar API)          (Privy Wallet)              │
│                          Arbitrum ETH                │
└─────────────────────────────────────────────────────┘
```

## Stack

| Component | Technology |
|---|---|
| **LLM Brain** | Claude (Anthropic API) |
| **Farcaster API** | Neynar v2 |
| **Wallet** | Privy Agent Wallet CLI |
| **Tipping Chain** | Arbitrum One |
| **Memory** | Supabase (vector search) |
| **Language** | Python 3.11 + Node.js |

## Project Structure

```
content-creator-agent/
├── agent/
│   └── agent_loop.py        # Main autonomous loop (3 phases)
├── brain/
│   └── decision_engine.py    # Claude-powered decision making
├── farcaster_service/
│   └── farcaster_client.py   # Neynar API client (read/write/lookup)
├── wallet/
│   └── privy_wallet.py       # Privy CLI wrapper for ETH tipping
├── memory/
│   └── vector_memory.py      # Supabase vector memory
├── config.py                 # Environment loader
├── main.py                   # Entry point
├── register_agent.mjs        # One-time: register new Farcaster account
├── publish_cast.mjs          # Utility: manual cast publishing
├── schema.sql                # Supabase table schema
└── requirements.txt          # Python dependencies
```

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/evaaliya/content-creator-agent.git
cd content-creator-agent

# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for Neynar + Privy CLI)
npm install
```

### 2. Environment Variables

Create `.env` with:

```env
# Farcaster Agent Account
FARCASTER_FID=<agent_fid>
FARCASTER_SIGNER_UUID=<signer_uuid>

# APIs
NEYNAR_API_KEY=<neynar_api_key>
ANTHROPIC_API_KEY=<claude_api_key>

# Supabase (memory)
SUPABASE_URL=<url>
SUPABASE_ANON_KEY=<key>

# Privy Wallet (tipping)
PRIVY_APP_ID=<app_id>
PRIVY_APP_SECRET=<app_secret>
PRIVY_WALLET_ID=<wallet_id>
PRIVY_WALLET_ADDRESS=<wallet_address>

# Warpcast
WARPCAST_BEARER_TOKEN=<token>
```

### 3. Privy Wallet Setup

```bash
# Install Privy CLI globally
npm install -g @privy-io/agent-wallet-cli

# Login to Privy
npx @privy-io/agent-wallet-cli login

# List wallets (verify your wallet is visible)
npx @privy-io/agent-wallet-cli list-wallets
```

### 4. Register a New Agent Account (one-time)

> Only needed if creating a fresh Farcaster identity.

1. Create an **App Wallet** at [dev.neynar.com](https://dev.neynar.com) → App → App Wallet tab
2. Fund it with ~$0.50 ETH on Optimism
3. Run the registration script:

```bash
node register_agent.mjs
```

4. Copy the output values (`AGENT_FID`, `AGENT_SIGNER_UUID`, etc.) into `.env`

## Running

```bash
python3 main.py
```

The agent runs in an infinite loop:
1. **Phase 1** — Responds to @mentions and replies
2. **Phase 2** — Engages with trending casts (max 3/cycle)
3. **Phase 3** — Explores random channels (ai, dev, crypto, founders)
4. **Sleep** — Waits 5-10 minutes between cycles

### Safety Limits

| Limit | Value |
|---|---|
| Max casts per day | 30 |
| Max tip per transaction | 1.0 ETH |
| Max daily spend | 5.0 ETH |
| Cycle interval | 5-10 min (randomized) |

## Agent Profile

| Field | Value |
|---|---|
| Username | `@matricula` |
| Display Name | Matriculate |
| Bio | enrolled in everything. committed to nothing. |
| FID | 3319768 |
| Wallet | Privy sandbox on Arbitrum |

## License

MIT