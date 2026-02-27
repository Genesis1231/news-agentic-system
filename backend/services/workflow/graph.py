from config import logger
from langgraph.graph import StateGraph, END

from backend.core.database import DataInterface
from backend.core.redis import RedisManager

from .state import NewsState, SubNewsState, NewsStatus
from .nodes import (
    InitializationNode,
    ClassificationNode,
    ResearchNode,
    NewsEvaluationNode,
    SummarizationNode,
    WritingNode,
    ReviewNode,
    FinalizeNode
)


class FlowGraph:
    """Manager to create and manage the news processing workflow graph."""

    def __init__(self, database: DataInterface, redis: RedisManager) -> None:
        self.database: DataInterface = database
        self.redis_client: RedisManager = redis
        self.workflow: StateGraph | None = None
        self._initialized: bool = False
        
    async def initialize(self) -> None:
        """Create a news processing workflow graph."""
        
        graph = StateGraph(NewsState)
        graph.add_node("node_initialize", InitializationNode(database=self.database))
        graph.add_node("node_classify", ClassificationNode())
        graph.add_node("node_evaluate", NewsEvaluationNode())
        graph.set_entry_point("node_initialize")
        
        # Subgraphs
        graph.add_node("subgraph_flash", self._create_flash_subgraph)
        graph.add_node("subgraph_brief", self._create_brief_subgraph)
        graph.add_node("subgraph_analysis", self._create_analysis_subgraph)
        
        self.workflow = graph.compile()
        self._initialized = True
        
    async def process(self, data_id: str)-> NewsState | None:
        """Process the news item through the workflow."""
        
        if not self._initialized:
            await self.initialize()
            
        try:
            return await self.workflow.ainvoke({
                "status": NewsStatus.PENDING,
                "id": data_id
            })
            
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return None

    async def _create_flash_subgraph(self, state: NewsState) -> StateGraph:
        """Subgraph for time-sensitive breaking news."""
        subgraph = StateGraph(SubNewsState)            
        subgraph.add_node("node_write", WritingNode())
        subgraph.add_node("node_review", ReviewNode())
        subgraph.add_node("node_finalize", FinalizeNode(
            database=self.database,
            redis_client=self.redis_client
        ))
        
        # set the entry point to the write node
        subgraph.add_edge("node_write", "node_review")
        subgraph.set_entry_point("node_write")
        
        # invoke the subgraph with the initial state
        sub_workflow = subgraph.compile()
        return await sub_workflow.ainvoke({
            "status": state["status"],
            "depth": "FLASH",   
            "raw_news": state["raw_news"],
            "evaluation": state["evaluation"],
        })

    async def _create_brief_subgraph(self, state: NewsState) -> StateGraph:
        """Subgraph for brief analysis pieces."""
        subgraph = StateGraph(SubNewsState)
        subgraph.add_node("node_research", ResearchNode())
        subgraph.add_node("node_summarize", SummarizationNode())
        subgraph.add_node("node_write", WritingNode())
        subgraph.add_node("node_review", ReviewNode())
        subgraph.add_node("node_finalize", FinalizeNode(
            database=self.database,
            redis_client=self.redis_client
        ))
        
        subgraph.set_entry_point("node_research")
        sub_workflow = subgraph.compile()
        return await sub_workflow.ainvoke({
            "status": state["status"],
            "depth": "BRIEF",   
            "raw_news": state["raw_news"],
            "evaluation": state["evaluation"],
        })

    async def _create_analysis_subgraph(self, state: NewsState) -> StateGraph:
        """Subgraph for in-depth analysis."""
        subgraph = StateGraph(SubNewsState)
        subgraph.add_node("node_research", ResearchNode())
        subgraph.add_node("node_summarize", SummarizationNode())
        subgraph.add_node("node_write", WritingNode())
        subgraph.add_node("node_review", ReviewNode())
        subgraph.add_node("node_finalize", FinalizeNode(
            database=self.database,
            redis_client=self.redis_client
        ))
        
        subgraph.set_entry_point("node_research")
        sub_workflow = subgraph.compile()
        return await sub_workflow.ainvoke({
            "status": state["status"],
            "depth": "ANALYSIS",   
            "raw_news": state["raw_news"],
            "evaluation": state["evaluation"],
        })
            
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()
            
    async def cleanup(self):
        """Close the workflow graph and release all resources.  """
        try:
            # Clear the workflow nodes if initialized
            if self.workflow:
                self.workflow.nodes.clear()
                self.workflow = None
        except Exception as e:
            raise Exception(f"Error during workflow graph cleanup: {str(e)}")
        