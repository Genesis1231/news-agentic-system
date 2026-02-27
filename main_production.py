import asyncio
import signal
from config import logger
from backend.services.production.director import ProductionDirector
from dotenv import load_dotenv

load_dotenv()

async def main():
    stop_event = asyncio.Event()

    def handle_shutdown_signal() -> None:
        logger.debug("Shutdown signal received, stopping production.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown_signal)

    async with ProductionDirector() as director:
        # Run director.start() as a background task
        task = asyncio.create_task(director.start())
        logger.debug("Production Director started. Waiting for shutdown signal...")
        
        # Wait until a termination signal is received
        await stop_event.wait()
        
        # Gracefully shutdown the orchestrator (sets _running to False)
        await director.stop()
        await task

if __name__ == "__main__":
    asyncio.run(main())
