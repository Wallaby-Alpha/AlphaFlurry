import requests
from config import ALLOWED_SOURCES

DEXSCREENER_NEW_PAIRS = "https://api.dexscreener.com/latest/dex/pairs/solana"
PUMPFUN_RECENT = "https://pump.fun/api/trending"  # lightweight endpoint


def fetch_dexscreener_new_pairs():
    """
    Returns tokens from DexScreener's new pairs feed.
    """
    try:
        data = requests.get(DEXSCREENER_NEW_PAIRS, timeout=10).json()
    except Exception:
        return []

    tokens = []
    for pair in data.get("pairs", []):
        token_address = pair.get("pairAddress")
        volume_24h = float(pair.get("volume", 0))

        tokens.append({
            "address": token_address,
            "source": 2,
            "volume_24h": volume_24h,
        })

    return tokens


def fetch_pumpfun_recent():
    """
    Returns recently launched Pump.fun tokens.
    """
    try:
        data = requests.get(PUMPFUN_RECENT, timeout=10).json()
    except Exception:
        return []

    tokens = []
    for item in data.get("tokens", []):
        token_address = item.get("mint")
        volume_24h = float(item.get("volume_24h", 0))

        tokens.append({
            "address": token_address,
            "source": 4,
            "volume_24h": volume_24h,
        })

    return tokens


def discover_candidates():
    """
    Unified discovery pipeline.
    Filters by ALLOWED_SOURCES (default: {2, 4}).
    """
    tokens = []

    tokens.extend(fetch_dexscreener_new_pairs())
    tokens.extend(fetch_pumpfun_recent())

    return [t for t in tokens if t["source"] in ALLOWED_SOURCES]
