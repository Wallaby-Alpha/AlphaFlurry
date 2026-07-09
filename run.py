import time
import traceback
from scanner import scan_token
from config import SCAN_INTERVAL_SECONDS
from discover import discover_candidates  # your token discovery logic

def main():
    while True:
        try:
            tokens = discover_candidates()
            for token in tokens:
                scan_token(token)

        except Exception as e:
            with open("logs/scanner.log", "a") as f:
                f.write(f"{time.ctime()} - ERROR: {e}\n")
                f.write(traceback.format_exc() + "\n")

        time.sleep(SCAN_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
