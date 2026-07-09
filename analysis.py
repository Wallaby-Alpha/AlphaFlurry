from datetime import datetime, timedelta
from collections import defaultdict
from helius import check_top_holder_risk


# ---------------------------------------------------------
# 1. Tight Time Cluster Detection (5–15 min flurries)
# ---------------------------------------------------------

def find_time_clusters(timestamps, window_minutes=10, min_cluster_size=5):
    """
    Detect bursts of buyers in a tight time window.
    """
    if not timestamps:
        return []

    timestamps = sorted(timestamps)
    window = timedelta(minutes=window_minutes)
    clusters = []

    for t_start in timestamps:
        count = sum(1 for t in timestamps if t_start <= t < t_start + window)
        if count >= min_cluster_size:
            clusters.append({
                "count": count,
                "start": t_start,
                "end": t_start + window
            })

    clusters.sort(key=lambda x: -x["count"])
    return clusters


# ---------------------------------------------------------
# 2. Sudden Velocity Acceleration (unique buyer spike)
# ---------------------------------------------------------

def detect_velocity_acceleration(buyer_timestamps, lookback_hours=5, burst_minutes=5):
    """
    Measures acceleration: (buyers in last X minutes) / (buyers in last Y hours).
    """
    if not buyer_timestamps:
        return 0.0

    buyer_timestamps = sorted(buyer_timestamps)
    now = buyer_timestamps[-1]

    lookback_start = now - timedelta(hours=lookback_hours)
    burst_start = now - timedelta(minutes=burst_minutes)

    past = [t for t in buyer_timestamps if lookback_start <= t < burst_start]
    burst = [t for t in buyer_timestamps if t >= burst_start]

    past_rate = len(past)
    burst_rate = len(burst)

    if past_rate == 0:
        return float(burst_rate)

    return burst_rate / past_rate


# ---------------------------------------------------------
# 3. Honeypot / No-Sell Guard
# ---------------------------------------------------------

def is_honeypot(total_buys: int, total_sells: int) -> bool:
    """
    If buyers exist but no sells at all → likely honeypot or high-tax scam.
    """
    return total_buys >= 20 and total_sells == 0


# ---------------------------------------------------------
# 4. Sybil / Bot Bundle Detection
# ---------------------------------------------------------

def detect_sybil_bundle(wallet_infos):
    """
    Detects bot bundles funded by same wallet + created recently.
    wallet_infos = [
        {"wallet": "...", "funded_by": "...", "age_minutes": 12},
        ...
    ]
    """
    if not wallet_infos:
        return False

    funded_by_counts = defaultdict(int)
    recent_wallets = 0

    for w in wallet_infos:
        funded_by = w.get("funded_by")
        if funded_by:
            funded_by_counts[funded_by] += 1

        if w.get("age_minutes", 9999) <= 60:
            recent_wallets += 1

    if not funded_by_counts:
        return False

    dominant_funder = max(funded_by_counts.values())
    total_wallets = len(wallet_infos)

    if total_wallets == 0:
        return False

    funded_ratio = dominant_funder / total_wallets
    recent_ratio = recent_wallets / total_wallets

    # 80%+ funded by same wallet AND 80%+ created recently → bot bundle
    return funded_ratio >= 0.80 and recent_ratio >= 0.80


# ---------------------------------------------------------
# 5. Full Token Analysis Pipeline
# ---------------------------------------------------------

def analyze_token(token_address: str, txs, helius_api_key: str):
    """
    Runs all analysis steps and returns a dict describing the token's behavior.
    """
    buyer_timestamps = []
    wallet_infos = []
    total_buys = 0
    total_sells = 0

    for tx in txs:
        tx_type = tx.get("type")

        if tx_type == "buy":
            total_buys += 1
            buyer_timestamps.append(tx["timestamp"])
            wallet_infos.append({
                "wallet": tx.get("wallet"),
                "funded_by": tx.get("funded_by"),
                "age_minutes": tx.get("wallet_age_minutes", 9999),
            })

        elif tx_type == "sell":
            total_sells += 1

    # Honeypot guard
    if is_honeypot(total_buys, total_sells):
        return None

    # Sybil bundle guard
    if detect_sybil_bundle(wallet_infos):
        return None

    # Top-holder concentration guard
    if check_top_holder_risk(token_address):
        return None

    # Cluster detection
    clusters = find_time_clusters(buyer_timestamps)
    largest_cluster = clusters[0] if clusters else None

    # Velocity acceleration
    velocity_accel = detect_velocity_acceleration(buyer_timestamps)

    return {
        "num_first_time_buyers": len(buyer_timestamps),
        "largest_cluster": largest_cluster,
        "velocity_acceleration": velocity_accel,
        "total_buys": total_buys,
        "total_sells": total_sells,
    }


# ---------------------------------------------------------
# 6. Scoring Function (Flurry + Velocity + Under-the-Radar)
# ---------------------------------------------------------

def score_token(token: dict, analysis: dict, min_buyers: int = 10) -> int:
    """
    Computes a score representing how strong the alpha flurry is.
    """
    if not analysis:
        return 0

    n = analysis["num_first_time_buyers"]
    if n < min_buyers:
        return 0

    score = n * 12  # baseline

    # Flurry cluster bonus
    largest = analysis["largest_cluster"]
    if largest and largest["count"] >= 8:
        score += 50
    elif largest and largest["count"] >= 4:
        score += 25

    # Velocity acceleration bonus
    accel = analysis["velocity_acceleration"]
    if accel >= 5:
        score += 40
    elif accel >= 3:
        score += 20

    # Under-the-radar volume bias
    vol = token.get("volume_24h", 0)
    if vol > 150_000:
        score -= 40
    elif vol < 30_000:
        score += 20

    return max(score, 0)
