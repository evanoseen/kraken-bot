import schedule
import time
import logging
from trader import run_trading_cycle
from heartbeat import write_heartbeat
from config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ]
)
logger = logging.getLogger(__name__)


def run_cycle() -> None:
    """Run one trading cycle, then stamp the heartbeat file.

    Wrapping the cycle here guarantees the heartbeat is written on every
    completed cycle regardless of which early-return path the trader takes.
    """
    run_trading_cycle()
    write_heartbeat()


def main():
    logger.info("Kraken Meme Coin NewsTrader starting...")
    logger.info(f"Running every {cfg.run_interval_minutes} minutes")

    run_cycle()

    schedule.every(cfg.run_interval_minutes).minutes.do(run_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
