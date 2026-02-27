import asyncio
import signal
from config import logger
from backend.services.distribution import Publisher
from dotenv import load_dotenv

load_dotenv()

async def main():
    stop_event = asyncio.Event()

    def handle_shutdown_signal() -> None:
        logger.debug("Shutdown signal received, stopping publisher.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown_signal)

    async with Publisher() as publisher:
        # Run publisher.start() as a background task
        task = asyncio.create_task(publisher.start())
        logger.debug("Publisher started. Waiting for shutdown signal...")
        
        # Wait until a termination signal is received
        await stop_event.wait()
        
        # Gracefully shutdown the publisher
        await publisher.stop()
        await task

if __name__ == "__main__":
    asyncio.run(main())
