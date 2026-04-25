"""
Web3 News Reader — Fetches real web3/crypto/DeFi/NFT news.

Uses free RSS feeds from top crypto news sources.
No API key required.
"""
import httpx
import xml.etree.ElementTree as ET
import random


# Free RSS feeds — real crypto/web3 news sources
RSS_FEEDS = {
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "The Block": "https://www.theblock.co/rss.xml",
    "Decrypt": "https://decrypt.co/feed",
    "Cointelegraph": "https://cointelegraph.com/rss",
}

# Keywords that signal high-impact (not fluff)
IMPACT_KEYWORDS = [
    "regulation", "SEC", "ETF", "hack", "exploit", "upgrade", "launch",
    "partnership", "protocol", "L2", "rollup", "bridge", "stablecoin",
    "AI agent", "DeFi", "NFT", "DAO", "governance", "airdrop",
    "Ethereum", "Bitcoin", "Solana", "Base", "Optimism", "Farcaster",
    "Uniswap", "OpenSea", "token", "mainnet", "testnet", "funding",
    "billion", "million", "treasury", "acquisition", "open source",
]


async def fetch_web3_news(max_items: int = 10) -> list:
    """Fetch recent web3/crypto news from RSS feeds."""
    # Pick 2 random sources for variety
    sources = random.sample(list(RSS_FEEDS.items()), min(2, len(RSS_FEEDS)))
    all_items = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for name, url in sources:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                root = ET.fromstring(resp.text)

                # Standard RSS parsing
                for item in root.findall(".//item")[:max_items]:
                    title = item.find("title")
                    link = item.find("link")
                    desc = item.find("description")
                    pub_date = item.find("pubDate")

                    if title is not None and link is not None:
                        title_text = title.text or ""
                        desc_text = (desc.text or "")[:400] if desc is not None else ""
                        # Strip HTML tags from description
                        import re
                        desc_text = re.sub(r'<[^>]+>', '', desc_text).strip()

                        all_items.append({
                            "title": title_text.strip(),
                            "description": desc_text,
                            "url": link.text.strip() if link.text else "",
                            "published": pub_date.text if pub_date is not None else "",
                            "source_name": name,
                            "source": "web3_news"
                        })
            except Exception as e:
                print(f"⚠️ RSS error ({name}): {e}")
                continue

    print(f"📰 Fetched {len(all_items)} web3 news items")
    return all_items


def filter_high_impact(items: list) -> list:
    """Filter for high-impact news (not fluff)."""
    scored = []
    for item in items:
        text = f"{item['title']} {item['description']}".lower()
        score = sum(1 for kw in IMPACT_KEYWORDS if kw.lower() in text)
        if score >= 2:  # At least 2 impact keywords
            item["impact_score"] = score
            scored.append(item)

    # Sort by impact
    scored.sort(key=lambda x: x["impact_score"], reverse=True)
    return scored


async def fetch_top_news() -> dict | None:
    """Get 1 high-impact web3 news item."""
    items = await fetch_web3_news(max_items=15)
    if not items:
        return None

    high_impact = filter_high_impact(items)
    if high_impact:
        return random.choice(high_impact[:3])

    # Fallback: just pick something recent
    return items[0] if items else None
