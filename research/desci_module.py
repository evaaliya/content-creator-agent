import json
import os
import datetime
import asyncio
import subprocess
import urllib.request
import tempfile
import traceback

import ccxt
from scholarly import scholarly
from langchain_community.document_loaders import PyPDFLoader
from brain.llm_client import generate_agent_decision
from memory.supabase_client import supabase

ZORA_CONTRACT = "0x1111111111166b7fe7bd91427724b487980afc69"
# Placeholder for BIO/Molecule contract address until provided by the user
MOLECULE_CONTRACT = "0x0000000000000000000000000000000000000000"

def logTransaction(data):
    if not supabase:
        print("Supabase client not initialized, skipping log.")
        return
    try:
        supabase.table("agent_assets").insert({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "article_title": data.get("article_title"),
            "tx_hash": data.get("tx_hash"),
            "nft_url": data.get("nft_url"),
            "insight_text": data.get("insight_text"),
            "asset_type": data.get("asset_type")
        }).execute()
        print(f"✅ Logged {data.get('asset_type')} transaction to Supabase.")
    except Exception as e:
        print(f"⚠️ Error logging transaction to Supabase: {e}")

async def executeAgentAction(tx_data):
    """Fallback to generic executeAgentAction if we don't use Zora Create"""
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wallet", "privy_server.mjs")
    cmd = ["node", script, "executeAgentAction", json.dumps({"transaction": tx_data})]
    return await _run_node(cmd)

async def zoraCreateEdition(name, description):
    """Use the specific Zora SDK command in our node script"""
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "wallet", "privy_server.mjs")
    
    # We will encode the insight as the URI or description
    payload = {
        "name": name[:50] + " (DeSci)",
        "contractURI": f"data:application/json;utf8,{json.dumps({'name': name, 'description': description})}",
        "tokenURI": f"data:application/json;utf8,{json.dumps({'name': name, 'description': description})}"
    }
    
    cmd = ["node", script, "zoraCreate", json.dumps(payload)]
    return await _run_node(cmd)

async def _run_node(cmd):
    try:
        result = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True, timeout=120)
        output = result.stdout.strip()
        start = output.find('{')
        end = output.rfind('}')
        if start != -1 and end != -1:
            data = json.loads(output[start:end+1])
            return data
        return {"success": False, "error": output or result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_eth_price():
    try:
        exchange = ccxt.kraken()
        ticker = exchange.fetch_ticker('ETH/USD')
        return ticker['last']
    except Exception as e:
        print(f"⚠️ ccxt error: {e}")
        return 3000.0 # fallback

def get_citation_count(title):
    try:
        search_query = scholarly.search_pubs(title)
        pub = next(search_query)
        return pub.get('num_citations', 0)
    except StopIteration:
        return 0
    except Exception as e:
        print(f"⚠️ scholarly error: {e}")
        return 0

def extract_pdf_text(url):
    """Use LangChain PyPDFLoader to extract text from ArXiv PDF"""
    if "arxiv.org/abs/" in url:
        pdf_url = url.replace("abs", "pdf") + ".pdf"
    else:
        pdf_url = url
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            req = urllib.request.Request(pdf_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                temp_file.write(response.read())
            temp_path = temp_file.name
            
        loader = PyPDFLoader(temp_path)
        pages = loader.load()
        text = " ".join([p.page_content for p in pages[:3]]) # first 3 pages
        os.remove(temp_path)
        return text
    except Exception as e:
        print(f"⚠️ LangChain PDF error: {e}")
        return ""

async def evaluateAndMint(article_data):
    print("🧬 DeSciCurationModule activated")
    
    title = article_data.get('title', '')
    url = article_data.get('url', '')
    
    # 1. Fetch citations to boost score
    citations = get_citation_count(title)
    print(f"   📊 Citations found: {citations}")
    
    # 2. Extract deep text using LangChain
    deep_text = extract_pdf_text(url)
    if not deep_text:
        deep_text = article_data.get('abstract', '')
        
    content = f"Title: {title}\nCitations: {citations}\nContent snippet: {deep_text[:3000]}"
    prompt = (
        "You are a scientific evaluator for a DeSci (Decentralized Science) curation fund. "
        "Evaluate the following research paper based on its potential impact, originality, and methodology. "
        "The citation count is provided (high citations should boost the score). "
        "Return a JSON object strictly with these keys: "
        "'score' (integer 0-100), "
        "'is_bio_molecule' (boolean, true if it's related to biology, medicine, molecules, or biotech), "
        "'insight' (a short 1-2 sentence brilliant technical insight about this paper)."
    )
    
    decision = generate_agent_decision(content, prompt)
    if not decision:
        return None
        
    score = decision.get("score", 0)
    print(f"   🧠 DeSci Evaluation Score: {score}/100")
    
    if score > 80:
        insight = decision.get("insight", "An incredible breakthrough in science.")
        is_bio = decision.get("is_bio_molecule", False)
        
        # Action 1 & 2: Mint Zora Edition
        print("   🖼️ Minting Zora NFT...")
        res = await zoraCreateEdition(title, insight)
        
        if res.get("success"):
            tx_data_res = res.get("result", {})
            tx_hash = tx_data_res.get("txHash", "unknown")
            contract_address = tx_data_res.get("contractAddress", "unknown")
            
            print(f"   ✅ Zora NFT Created! tx: {tx_hash}")
            
            logTransaction({
                "article_title": title,
                "tx_hash": tx_hash,
                "nft_url": f"https://basescan.org/address/{contract_address}",
                "insight_text": insight,
                "asset_type": "Zora NFT"
            })
            
            # Action 3: BIO/Molecule investment
            if is_bio:
                print("   🧬 Bio/Molecule detected! Initiating $5 share purchase...")
                eth_price = get_eth_price()
                eth_value = 5.0 / eth_price
                wei_value = int(eth_value * 10**18)
                
                tx_data_buy = {
                    "to": MOLECULE_CONTRACT,
                    "value": str(wei_value),
                    "data": "0x" # call to buy share function when ABI is known
                }
                
                # Uncomment to execute actual buy when contract is provided
                # buy_res = await executeAgentAction(tx_data_buy)
                # if buy_res.get("success"):
                #     logTransaction({
                #         "article_title": title,
                #         "tx_hash": buy_res.get("result"),
                #         "nft_url": f"https://basescan.org/tx/{buy_res.get('result')}",
                #         "insight_text": f"Bought $5 equivalent ({eth_value:.4f} ETH) of Molecule shares",
                #         "asset_type": "Molecule Share"
                #     })
                print(f"   (Simulated) Bought {eth_value:.6f} ETH of BIO shares.")
            
            # Mini App link - replace with actual if needed
            mini_app_link = "https://matricula-sand.vercel.app" 
            return f"\n\n🧬 DeSci Status: Анализ зафиксирован в блокчейне Base. Посмотреть в моем [Mini App Link: {mini_app_link}]."
            
    return None
