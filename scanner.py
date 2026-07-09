from analysis import analyze_token, score_token
from helius import fetch_token_transactions
from telegram import send_alert
from config import HELIUS_API_KEY, MIN_SCORE_TO_ALERT

def scan_token(token):
    txs = fetch_token_transactions(token["address"])
    analysis = analyze_token(token["address"], txs, HELIUS_API_KEY)

    if not analysis:
        return None

    score = score_token(token, analysis)

    if score >= MIN_SCORE_TO_ALERT:
        send_alert(
            f"🔥 *ALPHA FLURRY DETECTED*\n\n"
            f"Token: `{token['address']}`\n"
            f"Score: *{score}*\n"
            f"Unique Buyers: {analysis['num_first_time_buyers']}\n"
            f"Cluster Size: {analysis['largest_cluster']['count'] if analysis['largest_cluster'] else 0}\n"
            f"Velocity Accel: {analysis['velocity_acceleration']:.2f}"
        )

    return score
