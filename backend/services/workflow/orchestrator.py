import asyncio
import traceback
from typing import Dict, List, Any, Set
from config import logger

from backend.core.redis import RedisManager, RedisQueue
from backend.core.database import DataInterface

from .graph import FlowGraph
from .state import NewsStatus

class FlowOrchestrator:
    """
    Manages asynchronous processing of news items through a workflow graph.
    
    Attributes:
        max_concurrent_flows (int): Maximum number of concurrent workflows
        active_flows (Dict[str, StateGraph]): Currently active workflow instances
        semaphore (asyncio.Semaphore): Controls concurrent access
        _running (bool): Flag to indicate if the main processing loop is running
        sleep_time (int): Time to sleep between main loop checks
    """
    
    def __init__(
        self, 
        max_concurrent_flows: int = 10, # Maximum number of concurrent flows
        sleep_time: int = 5 # Sleep time between main loop checks
    ):
        # Use built-in types for collections
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_flows)
        self.redis_client: RedisManager = RedisManager(service="Orchestrator")
        self.database: DataInterface = DataInterface(service="Orchestrator")
           
        self.active_flows: Dict[str, FlowGraph] = {}
        self._active_tasks: Set[asyncio.Task] = set()
        self._running: bool = False
        self.sleep_time: int = sleep_time
        
        
    async def start(self)-> None:
        """Start the main processing loop."""
        
        if self._running:
            logger.warning("The Orchestrator is already running.")
            return
            
        self._running = True
        while self._running:
            try:
                if not (data := await self.redis_client.listen(RedisQueue.RAW)):
                    continue

                if data_id := data.get("id"):
                    # Create a task to process the news
                    task = asyncio.create_task(self._process_news(data_id))
                    
                    # Add the task to the active tasks set and remove it when it's done
                    self._active_tasks.add(task)
                    task.add_done_callback(self._active_tasks.discard)
            
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                
    
    async def immediate(self, content_id: str) -> Dict[str, Any] | None:
        """
        Process a single news item immediately without queueing.
        This is used for testing and debugging.
        """

        try:
            workflow = FlowGraph(
                database=self.database,
                redis=self.redis_client
            )
            self.active_flows[content_id] = workflow
        
            # Process the news item
            result = await workflow.process(content_id)
        
        except Exception as e:
            logger.error(f"Error processing news: {e}\n{traceback.format_exc()}")
            return None
        
        return f"News {content_id} {result.get('status', 'Unknown') if isinstance(result, dict) else 'Unknown'}"
            
    async def _process_news(self, data_id: str)-> None:
        """Process a single news item through the workflow."""

        # Create a flow id for consistency
        flow_id = f"flow_{data_id}"
                  
        async with self.semaphore:
            try:
                workflow = FlowGraph(
                    database=self.database,
                    redis=self.redis_client
                )
                
                # Add the workflow to the active flows dictionary
                self.active_flows[flow_id] = workflow
                
                # Process the news item
                result = await workflow.process(data_id)
                
                if result and result["status"] != NewsStatus.FAILED:
                    await self.database.update_raw_news(data_id, {"is_processed": True})
                 
            except asyncio.CancelledError:
                logger.info(f"News processing for {flow_id} was cancelled")
                raise
            except Exception as e:
                logger.error(f"Error processing news in {flow_id}: {e}\n{traceback.format_exc()}")
            finally:
                self.cleanup(flow_id)

    async def stop(self):
        """Stop the orchestrator."""
        self._running = False
        
        # Cancel all active tasks
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete or be cancelled
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks, return_exceptions=True)
        
    async def __aenter__(self):
        """Start the orchestrator."""
        
        # unfinished_raw_news = await self.database.load_news(is_produced=False)
        # if unfinished_raw_news:
        #     for news in unfinished_raw_news:
        #         await self._enqueue_news(news.id)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Gracefully shutdown the orchestrator."""
        await self.shutdown()
        
    async def shutdown(self):
        """Shutdown the orchestrator."""
        try:
            # Close connections
            await self.database.close()
            await self.redis_client.close()
            
            # Clean up active flows
            for flow_id in list(self.active_flows.keys()):
                self.cleanup(flow_id)
                
            logger.debug("Orchestrator is shut down successfully.")
        except Exception as e:
            logger.error(f"Error during Orchestrator shutdown: {str(e)}")


    def cleanup(self, flow_id: str) -> None:
        """Clean up resources associated with a flow."""
        flow = self.active_flows.pop(flow_id, None)
        if not flow:
            logger.debug(f"Failed to cleanup, {flow_id} not found in active list.")       
