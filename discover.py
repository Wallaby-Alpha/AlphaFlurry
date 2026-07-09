import requests

DEXSCREENER_TRENDING = "https://api.dexscreener.com/latest/dex/trending/solana"
PUMPFUN_RECENT = "https://api.pump.fun/v1/coins/recent"


def fetch_dexscreener():
    try:
        data = requests.get(DEXSCREENER_TRENDING, timeout=10).json()
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


def fetch_pumpfun():
    try:
        data = requests.get(PUMPFUN_RECENT, timeout=10).json()
    except Exception:
        return []

    tokens = []
    for coin in data.get("coins", []):
        token_address = coin.get("mint")
        volume_24h = float(coin.get("volume_24h", 0))

        tokens.append({
            "address": token_address,
            "source": 4,
            "volume_24h": volume_24h,
        })

    return tokens


def discover_candidates():
    tokens = []
    tokens.extend(fetch_dexscreener())
    tokens.extend(fetch_pumpfun())
    return tokens
