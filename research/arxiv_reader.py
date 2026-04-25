"""
Arxiv Reader — Fetches recent high-impact AI papers.

Uses the free arxiv API (no auth needed).
Categories: cs.AI, cs.LG, cs.CL, cs.CV, cs.CR (crypto/security)
"""
import httpx
import xml.etree.ElementTree as ET
import random


ARXIV_API = "https://export.arxiv.org/api/query"

# Categories relevant to @matricula's interests
CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.LG",   # Machine Learning
    "cs.CL",   # Computation and Language (NLP/LLMs)
    "cs.CV",   # Computer Vision
    "cs.CR",   # Cryptography and Security
    "cs.MA",   # Multi-Agent Systems
    "cs.DC",   # Distributed Computing (relevant to web3)
]


async def fetch_papers(max_results: int = 10) -> list:
    """Fetch recent papers from arxiv across AI + adjacent categories."""
    # Pick 2-3 random categories each time for variety
    selected = random.sample(CATEGORIES, min(3, len(CATEGORIES)))
    cat_query = " OR ".join([f"cat:{c}" for c in selected])

    params = {
        "search_query": f"({cat_query})",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(ARXIV_API, params=params)
            resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ Arxiv fetch error: {e}")
        return []

    # Parse XML
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    papers = []

    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        abstract = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:500]
        published = entry.find("atom:published", ns).text
        link = entry.find("atom:id", ns).text  # arxiv URL

        authors = []
        for author in entry.findall("atom:author", ns):
            name = author.find("atom:name", ns).text
            authors.append(name)

        categories = []
        for cat in entry.findall("atom:category", ns):
            categories.append(cat.get("term", ""))

        papers.append({
            "title": title,
            "authors": authors[:5],  # Top 5 authors
            "abstract": abstract,
            "url": link,
            "published": published,
            "categories": categories,
            "source": "arxiv"
        })

    print(f"📚 Fetched {len(papers)} papers from arxiv ({', '.join(selected)})")
    return papers


async def fetch_top_paper() -> dict | None:
    """Get 1 interesting paper — pick from recent batch."""
    papers = await fetch_papers(max_results=15)
    if not papers:
        return None

    # Filter out papers with very short abstracts (usually just placeholders)
    quality = [p for p in papers if len(p["abstract"]) > 100]
    if not quality:
        return papers[0]

    # Pick a random one from top 5 for variety
    return random.choice(quality[:5])
