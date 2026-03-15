import asyncio
import signal
from dotenv import load_dotenv
from config import logger
from backend.services.workflow import FlowOrchestrator

load_dotenv()

async def main():
    stop_event = asyncio.Event()

    def handle_shutdown_signal() -> None:
        logger.debug("Shutdown signal received, stopping orchestrator.")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown_signal)

    async with FlowOrchestrator() as orchestrator:
        # Run orchestrator.start() as a background task
        orchestrator_task = asyncio.create_task(orchestrator.start())
        logger.debug("Orchestrator started. Waiting for shutdown signal...")
        
        # Wait until a termination signal is received
        await stop_event.wait()
        
        # Gracefully shutdown the orchestrator (sets _running to False)
        await orchestrator.stop()
        await orchestrator_task

if __name__ == "__main__":
    asyncio.run(main())
