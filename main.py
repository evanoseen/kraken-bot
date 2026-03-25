import schedule
import time
import logging
from trader import run_trading_cycle
from config import RUN_INTERVAL_MINUTES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ]
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Kraken Meme Coin NewsTrader starting...")
    logger.info(f"Running every {RUN_INTERVAL_MINUTES} minutes")

    run_trading_cycle()

    schedule.every(RUN_INTERVAL_MINUTES).minutes.do(run_trading_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
