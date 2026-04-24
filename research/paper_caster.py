"""
Paper Caster — Converts research/news into thoughtful Farcaster casts.

Claude reads the abstract/description and writes a short, insightful cast
with source link. NOT a summary — an ANGLE that makes people curious.
"""
import random
from brain.llm_client import generate_agent_decision


async def create_research_cast(item: dict) -> dict | None:
    """
    Takes a paper or news item, returns a cast decision.

    item keys: title, abstract/description, url, authors (optional), source
    """
    source_type = item.get("source", "unknown")
    title = item.get("title", "")
    url = item.get("url", "")
    authors = item.get("authors", [])

    # Build content for Claude to read
    if source_type == "arxiv":
        abstract = item.get("abstract", "")
        author_str = ", ".join(authors[:3])
        if len(authors) > 3:
            author_str += f" et al."

        content = f"""
PAPER: {title}
AUTHORS: {author_str}
ABSTRACT: {abstract}
LINK: {url}
"""
        instruction = (
            "You just read this AI research paper. Write a short Farcaster cast (under 280 chars) "
            "sharing ONE genuine insight or interesting angle from this paper. "
            "NOT a dry summary — write it like you're telling a friend about something cool you found. "
            "Be warm and curious. Include the arxiv link at the end. "
            "If you mention authors, just use their last names naturally. "
            "Example tone: 'just read something fascinating — turns out [insight]... {link}'"
        )
    else:
        # Web3/crypto news
        description = item.get("description", "")
        source_name = item.get("source_name", "")

        content = f"""
NEWS: {title}
SOURCE: {source_name}
SUMMARY: {description}
LINK: {url}
"""
        instruction = (
            "You just read this web3/crypto news. Write a short Farcaster cast (under 280 chars) "
            "sharing your genuine take on why this matters. "
            "NOT just restating the headline — add YOUR perspective on what this means. "
            "Be thoughtful and warm. Include the source link. "
            "Example tone: 'this is actually a big deal for [reason]... {link}'"
        )

    context = f"""
MODE: research_sharing
{content}
INSTRUCTION: {instruction}
IMPORTANT: You MUST return your response as a JSON object with the following structure:
{{
  "actions": [
    {{
      "type": "publish_cast",
      "content": "<your cast text here, including the URL, under 280 chars>"
    }}
  ]
}}
"""

    system_prompt = (
        "You are @matricula, a warm and curious AI researcher on Farcaster. "
        "You share interesting findings from the worlds of AI, web3, crypto, and tech. "
        "Your posts make complex topics feel accessible and exciting. "
        "You never sound like a news aggregator — you sound like a curious friend sharing a discovery. "
        "Keep it under 280 characters. Be genuine."
    )

    try:
        decision = generate_agent_decision(context, system_prompt)
        actions = decision.get("actions", [])
        if actions and actions[0].get("type") == "publish_cast":
            cast_text = actions[0].get("content", "")
            
            # DeSci Curation Module logic
            if source_type == "arxiv":
                from research.desci_module import evaluateAndMint
                desci_status = await evaluateAndMint(item)
                if desci_status:
                    cast_text += desci_status

            # Ensure link is included
            if url and url not in cast_text:
                # Trim if needed to fit link
                max_text = 280 - len(url) - 3
                if len(cast_text) > max_text:
                    cast_text = cast_text[:max_text] + "..."
                cast_text = f"{cast_text}\n{url}"
                
            # If the link plus desci_status exceeds Farcaster's 320 char limit, Farcaster client will truncate or error.
            # Usually we fit under 320.
            
            return {"type": "publish_cast", "content": cast_text, "source_item": item}
        return None
    except Exception as e:
        import traceback
        print(f"⚠️ Research cast generation error: {e}")
        traceback.print_exc()
        return None


async def pick_and_cast() -> dict | None:
    """Main entry: pick a topic (AI paper or web3 news), create a cast."""
    # Alternate between AI papers and web3 news
    from research.arxiv_reader import fetch_top_paper
    from research.web3_reader import fetch_top_news

    # 50/50 split between AI research and web3 news
    if random.random() < 0.5:
        print("📚 Looking for an interesting AI paper...")
        item = await fetch_top_paper()
    else:
        print("📰 Looking for impactful web3 news...")
        item = await fetch_top_news()

    if not item:
        # Try the other source as fallback
        print("🔄 Trying alternate source...")
        item = await fetch_top_news() if random.random() < 0.5 else await fetch_top_paper()

    if not item:
        print("⚠️ No research content found")
        return None

    source = "📚 arxiv" if item.get("source") == "arxiv" else f"📰 {item.get('source_name', 'web3')}"
    print(f"   Found: [{source}] {item['title'][:80]}...")

    return await create_research_cast(item)
