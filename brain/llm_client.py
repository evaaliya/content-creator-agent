from anthropic import Anthropic
from typing import Dict, Any
import json
from config import ANTHROPIC_API_KEY
from .energy_manager import get_energy_manager

anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_agent_decision(context: str, system_prompt: str) -> Dict[str, Any]:
    energy = get_energy_manager()

    try:
        response = anthropic.messages.create(
            model="claude-opus-4-7",
            max_tokens=1000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": context}
            ]
        )

        # Track energy cost
        usage = response.usage
        cost = energy.add_usage(usage.input_tokens, usage.output_tokens)
        print(f"   ⚡ Cost: ${cost:.4f} | {energy.energy_emoji()} {energy.energy_ratio():.0%} remaining")

        text = response.content[0].text
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
        return json.loads(text)
    except Exception as e:
        print(f"LLM Client Error: {e}")
        return {
            "thoughts": "Failed",
            "validation": "Error",
            "actions": [{"type": "none", "content": "", "target_user": "", "amount_usdc": 0}]
        }
def get_embedding(text: str) -> list:
    """Get text embedding using Cohere's free embedding model."""
    try:
        import os
        import cohere
        co = cohere.ClientV2(os.getenv("COHERE_API_KEY"))
        response = co.embed(
            texts=[text],
            model="embed-english-v3.0",
            input_type="search_document",
            embedding_types=["float"]
        )
        return response.embeddings.float_[0]
    except Exception as e:
        print(f"⚠️ Embedding error: {e} — using zero vector")
        return [0.0] * 1024