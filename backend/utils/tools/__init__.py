import asyncio
from config import logger
from typing_extensions import List, Dict, Any

from langchain_community.tools import TavilySearchResults 

class Toolbox:
    """
    Toolbox is a class that manages all the tools in the system.
    
    Attributes:
        tools: List of tools
        client: the client that the tools are available for
    
    """
    def __init__(self, client: str = "ALL")-> None:
        self.client: str = client.lower()
        self.tools: List[Any] = self.initialize_tools()
        self.tool_map: Dict[str, Any] = {tool.name: tool for tool in self.tools}
    
    @property
    def tool_list(self) -> List[Any]:
        return self.tools

    def initialize_tools(self) -> List[Any]:
        """ Initialize all the tools """
        
        # Add built-in tools
        search_tool = TavilySearchResults(
            name="web_search",
            max_results=2,
            search_depth="advanced",
            include_raw_content=True,
            response_format="content_and_artifact"
        )
        # wiki_tool = WikipediaQueryRun()

        tool_list = [
            search_tool,  # tool to search the internet
        ]
        
        return tool_list
    
    async def execute_tool(self, tool_calls: List[Dict[str, Any]]) -> List[Any]:
        """ Execute the tool calls """

        if not tool_calls:
            logger.warning("No tool calls provided.")
            return []
        
        tool_tasks = []
        for call in tool_calls:
            tool_name = call.get("name")
            input_data = call.get("args")
            tool = self.tool_map.get(tool_name)
            if tool:
                tool_tasks.append(tool.ainvoke(input_data))
            else:
                logger.error(f"Tool '{tool_name}' not found.")
        
        try:
           results = await asyncio.gather(*tool_tasks)
           return results
        except Exception as e:
            logger.error(f"Unexpected error during tool execution: {e}")
            return []
