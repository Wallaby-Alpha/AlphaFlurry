import requests
from datetime import datetime, timedelta
from config import HELIUS_API_KEY

BASE_URL = "https://api.helius.xyz/v0"


# ---------------------------------------------------------
# 1. Fetch token transactions (Enhanced API)
# ---------------------------------------------------------

def fetch_token_transactions(token_address: str, limit: int = 200):
    """
    Converts Helius enhanced transactions into normalized buy/sell events.
    """

    url = f"{BASE_URL}/addresses/{token_address}/transactions?api-key={HELIUS_API_KEY}&limit={limit}"

    try:
        raw = requests.get(url, timeout=10).json()
    except Exception:
        return []

    txs = []

    for tx in raw:
        events = tx.get("events", {})
        token_transfers = events.get("tokenTransfers", [])

        for transfer in token_transfers:
            if transfer.get("mint") != token_address:
                continue

            # Determine buy/sell direction
            from_addr = transfer.get("fromUserAccount")
            to_addr = transfer.get("toUserAccount")

            if to_addr and not from_addr:
                tx_type = "buy"
                wallet = to_addr
            elif from_addr and not to_addr:
                tx_type = "sell"
                wallet = from_addr
            else:
                continue

            # Wallet age estimation
            wallet_age_minutes = estimate_wallet_age(wallet)

            # Funding source (detect bot bundles)
            funded_by = get_funding_source(wallet)

            # Timestamp
            ts = datetime.fromtimestamp(tx.get("timestamp", 0))

            txs.append({
                "type": tx_type,
                "timestamp": ts,
                "wallet": wallet,
                "funded_by": funded_by,
                "wallet_age_minutes": wallet_age_minutes,
            })

    return txs


# ---------------------------------------------------------
# 2. Wallet age estimation (basic heuristic)
# ---------------------------------------------------------

def estimate_wallet_age(wallet: str) -> float:
    """
    Returns wallet age in minutes using Helius account history.
    """
    url = f"{BASE_URL}/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}&limit=1"

    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return 9999

    if not data:
        return 9999

    first_tx = data[-1]
    ts = first_tx.get("timestamp")
    if not ts:
        return 9999

    created = datetime.fromtimestamp(ts)
    age_minutes = (datetime.utcnow() - created).total_seconds() / 60
    return age_minutes


# ---------------------------------------------------------
# 3. Funding source detection (bot bundle detection)
# ---------------------------------------------------------

def get_funding_source(wallet: str) -> str:
    """
    Returns the address that funded this wallet.
    Useful for detecting bot bundles.
    """
    url = f"{BASE_URL}/addresses/{wallet}/transactions?api-key={HELIUS_API_KEY}&limit=5"

    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return None

    for tx in data:
        events = tx.get("events", {})
        transfers = events.get("nativeTransfers", [])
        for t in transfers:
            if t.get("toUserAccount") == wallet:
                return t.get("fromUserAccount")

    return None


# ---------------------------------------------------------
# 4. Top-holder concentration check
# ---------------------------------------------------------

def check_top_holder_risk(token_address: str) -> bool:
    """
    Returns True if top 10 wallets hold >= 30% of supply.
    """
    url = f"{BASE_URL}/token-accounts?api-key={HELIUS_API_KEY}&tokenAddress={token_address}"

    try:
        data = requests.get(url, timeout=10).json()
    except Exception:
        return False

    accounts = data.get("tokenAccounts", [])
    if not accounts:
        return False

    accounts.sort(key=lambda x: -int(x.get("amount", 0)))

    top10 = accounts[:10]
    total_supply = sum(int(a.get("amount", 0)) for a in accounts)

    if total_supply == 0:
        return False

    top10_share = sum(int(a.get("amount", 0)) for a in top10) / total_supply

    return top10_share >= 0.30
