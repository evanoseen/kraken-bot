import os
from dotenv import load_dotenv

load_dotenv()

KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY")
KRAKEN_PRIVATE_KEY = os.getenv("KRAKEN_PRIVATE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

MAX_TRADE_AMOUNT = float(os.getenv("MAX_TRADE_AMOUNT", "25.0"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.80"))
RUN_INTERVAL_MINUTES = int(os.getenv("RUN_INTERVAL_MINUTES", "15"))
DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", "50.0"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "0.10"))    # sell if down 10%
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "0.25"))  # sell if up 25%
