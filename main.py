import asyncio
import signal
from dotenv import load_dotenv

from config import logger
from backend.services.aggregators import AggregatorScheduler

load_dotenv()

async def main():
    stop_event = asyncio.Event()

    def handle_shutdown_signal() -> None:
        logger.debug("Shutdown signal received, stopping scheduler.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown_signal)

    try:
        async with AggregatorScheduler() as scheduler:
            await scheduler.start()
            await stop_event.wait()
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
    finally:
        logger.debug("Scheduler stopped.")


if __name__ == "__main__":
    asyncio.run(main())
