from config import logger
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
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
        self.workflow: CompiledStateGraph | None = None
        self._initialized: bool = False

        # Shared node instances — created once, reused across subgraphs
        self._write_node = WritingNode()
        self._review_node = ReviewNode()
        self._finalize_node = FinalizeNode(
            database=self.database,
            redis_client=self.redis_client
        )
        self._research_node = ResearchNode()
        self._summarize_node = SummarizationNode()

    def _build_flash_subgraph(self) -> CompiledStateGraph:
        """Compile the flash subgraph."""
        
        subgraph = StateGraph(SubNewsState)
        subgraph.add_node("node_write", self._write_node)
        subgraph.add_node("node_review", self._review_node)
        subgraph.add_node("node_finalize", self._finalize_node)
        subgraph.set_entry_point("node_write")
        return subgraph.compile()

    def _build_deep_subgraph(self) -> CompiledStateGraph:
        """Compile the deep subgraph."""
        
        subgraph = StateGraph(SubNewsState)
        subgraph.add_node("node_research", self._research_node)
        subgraph.add_node("node_summarize", self._summarize_node)
        subgraph.add_node("node_write", self._write_node)
        subgraph.add_node("node_review", self._review_node)
        subgraph.add_node("node_finalize", self._finalize_node)
        subgraph.set_entry_point("node_research")
        return subgraph.compile()

    @staticmethod
    def _route_after_flash(state: NewsState) -> str:
        """After flash completes, check if editors recommended a deep dive."""
        if state.get("evaluation", {}).get("deep_dive"):
            return "subgraph_deep"
        return END

    async def initialize(self) -> None:
        """Create and compile the news processing workflow graph."""
        # Pre-compile subgraphs once, store for use by wrapper methods
        self._flash_subgraph = self._build_flash_subgraph()
        self._deep_subgraph = self._build_deep_subgraph()

        graph = StateGraph(NewsState)
        graph.add_node("node_initialize", InitializationNode(database=self.database))
        graph.add_node("node_classify", ClassificationNode())
        graph.add_node("node_evaluate", NewsEvaluationNode())
        graph.set_entry_point("node_initialize")

        # Evaluate always routes to flash via Command(goto="subgraph_flash")
        graph.add_node("subgraph_flash", self._run_flash)

        # After flash, conditionally route to deep
        graph.add_conditional_edges("subgraph_flash", self._route_after_flash, {
            "subgraph_deep": "subgraph_deep",
            END: END,
        })

        graph.add_node("subgraph_deep", self._run_deep)
        graph.add_edge("subgraph_deep", END)

        self.workflow = graph.compile()
        self._initialized = True

    async def _run_flash(self, state: NewsState) -> dict:
        """Invoke the pre-compiled flash subgraph with depth injected."""
        return await self._flash_subgraph.ainvoke({
            "status": state["status"],
            "depth": "FLASH",
            "raw_news": state["raw_news"],
            "evaluation": state["evaluation"],
        })

    async def _run_deep(self, state: NewsState) -> dict:
        """Invoke the pre-compiled deep subgraph with depth injected."""
        return await self._deep_subgraph.ainvoke({
            "status": state["status"],
            "depth": "DEEP",
            "raw_news": state["raw_news"],
            "evaluation": state["evaluation"],
        })

    async def process(self, data_id: str) -> NewsState | None:
        """Process the news item through the workflow."""
        if not self._initialized:
            await self.initialize()

        if not self.workflow:
            logger.error("Workflow graph is not initialized.")
            return None
        
        try:
            return await self.workflow.ainvoke({
                "status": NewsStatus.PENDING,
                "id": data_id
            }) #type: ignore
        except Exception as e:
            logger.error(f"Error running workflow: {e}")
            return None

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()

    async def cleanup(self):
        """Release workflow resources."""
        if self.workflow:
            self.workflow = None
        self._initialized = False
        