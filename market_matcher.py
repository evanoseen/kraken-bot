import json
import logging
import anthropic
from config import ANTHROPIC_API_KEY, MIN_CONFIDENCE

logger = logging.getLogger(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def analyze_news_for_trades(headlines: str, available_coins: list) -> list:
    coins_str = ", ".join(available_coins[:80])  # Limit to avoid token overflow

    prompt = f"""You are an aggressive crypto trader looking for short-term opportunities across ALL coins.

Headlines:
{headlines}

Available coins on Kraken: {coins_str}

Find headlines that will cause significant short-term price moves in ANY of these coins. Consider:
- Celebrity/influencer mentions (Elon Musk, Trump, etc.)
- Exchange listings or delistings
- Protocol upgrades or hacks
- Regulatory news
- Viral social media trends
- Major partnerships
- Any coin-specific news

Respond ONLY with a valid JSON array. Each item must have:
- "coin": exact symbol from the available coins list above
- "action": "buy" or "sell"
- "confidence": float 0.0–1.0
- "reasoning": one sentence

Only include confidence >= {MIN_CONFIDENCE}. If no signals, return: []

JSON array:"""

    try:
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()

        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        signals = json.loads(raw)
        filtered = [s for s in signals if s.get("confidence", 0) >= MIN_CONFIDENCE]

        for s in filtered:
            logger.info(f"Signal: {s['action'].upper()} {s['coin']} | Confidence: {s['confidence']} | {s['reasoning']}")

        return filtered

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return []
    except Exception as e:
        logger.error(f"Error in analysis: {e}")
        return []
