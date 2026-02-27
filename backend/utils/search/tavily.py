import asyncio
from config import logger
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from tavily import AsyncTavilyClient
from backend.models.SQL import KnowledgeData
from backend.core.database import DataInterface
from .scrape import clean_scraped_content, clean_domain_name
from .whitelist import NEWS_MEDIA, TECH_MEDIA, RESEARCH_MEDIA, POLICY_MEDIA, EXCLUDE_DOMAINS

class TavilySearch:
    """
    Search Aggregator class to fetch news from multiple Apify twitter scraper tasks.
    
    Attributes:
        fetched_queries (Set[str]): The set of indexed ids of the fetched news items.
        
    #TODO: add search results into knowledge database
    """
    def __init__(
        self, 
        max_items: int = 2, # how many articles to fetch from tavily search   
        max_chars: int = 2048 # how many characters to fetch from search results
    ) -> None:
        """Initialize the search aggregator."""
        self._max_items: int = max_items
        self._max_chars: int = max_chars
        self.client: AsyncTavilyClient = AsyncTavilyClient()
        self.knowledge_queries: List[Dict[str, Any]] = []
        self.whitelist = NEWS_MEDIA + TECH_MEDIA + RESEARCH_MEDIA + POLICY_MEDIA
        self.domain_map = {
            "tech_search": TECH_MEDIA,
            "academic_search": RESEARCH_MEDIA,
            "broad_search": NEWS_MEDIA,
            "policy_search": POLICY_MEDIA,
        }

    # TODO: add knowledge queries to the database, not sure if this is a good practice
    # TODO: maybe not at a query level, but at a url summary level
    # async def load_knowledge(self, db: DatabaseManager) -> None:
    #     """load the knowledge queries from the database. to save on api calls"""
        
    #     # Fetch the ids from the last 30 days
    #     time_range = (datetime.now(timezone.utc) - timedelta(30), None)
    #     try:
    #         fetched_data = await db.query(KnowledgeData, time_range = time_range)
    #         self.knowledge_queries = [data.to_schema() for data in fetched_data]
    #     except Exception as e:
    #         logger.error(f"Failed to load knowledge queries: {e}")
        
    #     logger.debug(f"Loaded {len(self.knowledge_queries)} recent knowledge queries.")

    async def execute_search(self, search_query: str, search_type: str, domain_name: str) -> List[Dict[str, Any]]:
        """ Execute the search query and process the results. """
        
        if not search_query or not search_type:
            logger.error("Search query or search type is empty.")
            return []
        
        try:
            search_results = await self.client.search(
                    search_query,
                    max_results=20,
                    include_raw_content=True,
                    topic="general",
                )
            
        except Exception as e:
                logger.error(f"Error searching for {search_query}: {e}")
                return []
        
        final_results = []
        remaining_results = [] 
        
        for result in search_results["results"]:
            if (num_remaining := self._max_items - len(final_results)) <= 0:
                break
            
            if not result or not isinstance(result, Dict) or "url" not in result:
                continue
            
            media_url = clean_domain_name(result["url"])
            
            # process premium domains first
            if self._is_premium_domain(media_url, search_type, domain_name):
                logger.debug(f"Premium domain: {media_url}")
                if processed_result := self.process_search_result(search_query, result):
                    final_results.append(processed_result)
                continue

            remaining_results.append(result)
                
        # Process remaining results if needed
        if num_remaining > 0:
            final_results.extend([
                self.process_search_result(search_query, result)
                for result in remaining_results[:num_remaining]
            ])
        
        return final_results
            
    async def search_web(self, search_plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """2nd search algorithm to fetch news from the web"""
        try:
            search_tasks = [
                self.execute_search(plan["query"], plan["type"], plan.get("domain_name", "")) 
                for plan in search_plans
            ]
            search_results = await asyncio.gather(*search_tasks)
            return self.flatten_search_results(search_results)
        
        except Exception as e:
            logger.error(f"Error searching the web for {search_plans}: {e}")
            return []
    
    def flatten_search_results(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Flatten and filter search results."""
        
        # Flatten and filter search results
        flattened_results = []
        seen_urls = set()
        
        for results in search_results:
            if not results:  # Skip empty result lists
                continue
                
            for result in results:
                if not result:  # Skip empty results
                    continue
                    
                url = result.get("url")
                if not url or url in seen_urls:  # Skip duplicates
                    continue    
                seen_urls.add(url)
                
                #TODO: save the resules into knowledge database
                flattened_results.append(result.get("content"))
                
        return flattened_results
    
    def _is_premium_domain(self, media_url: str, search_type: str, domain_name: str) -> bool:
        """Check if the media URL is from a valid domain."""

        if domain_name and domain_name.lower().strip() in media_url:
            return True
        
        if domain_list := self.domain_map.get(search_type):
            if media_url in domain_list:
                return True
                
        return media_url in self.whitelist
            
    def process_search_result(self, search_query: str, search_result: Dict[str, Any]) -> Dict[str, Any] | None:
        """Process the search result."""
        
        media_url = search_result.get("url")
        media_score = search_result.get("score") or 0
        media_name = clean_domain_name(media_url)
        
        if media_score < 0.2:
            """ return None if the media score is disqualified """
            logger.debug(f"Search result score is {media_score}: {media_url}")
            return None
        
        if not (content := search_result.get("raw_content")):
            """ return None if the raw_content is not present """
            logger.debug(f"Search result raw_content is not present: {media_url}")
            content = search_result.get("content")

        # format the content
        content = clean_scraped_content(content)
        if len(content) > self._max_chars:
            # truncate the raw_content if it is longer than the max_chars 
            content = content[:self._max_chars] + "... [truncated]"

        return {
            "query": search_query,
            "url": media_url,
            "content": f"<SOURCE_MEDIA>{media_name}</SOURCE_MEDIA>: {content}",
            "raw_content": search_result["raw_content"],
            "score": media_score
        }
    
    async def search(self, search_queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Old search functions."""
        
        search_tasks = []
        for search_query in search_queries:
            query_type = search_query["type"]
            query = search_query["query"]

            # If the query is a direct search, then search from the domain name
            if query_type == "direct_search":
                if domain := search_query.get("domain_name"):
                    search_tasks.append(self.search_news(query, [domain]))
                    continue
                else:
                    # If the domain name is not present, then search from the tech media
                    query_type = "tech_search"
                    continue
            
            domain_list = self.domain_map.get(query_type)
            if not domain_list:
                logger.error(f"Invalid query type: {query_type}")
                domain_list = TECH_MEDIA
            
            search_tasks.append(self.search_news(query, domain_list))
           
        # Wait for all tasks to complete    
        search_results = await asyncio.gather(*search_tasks)
        return self.flatten_search_results(search_results)
    
    async def search_news(self, search_query: str, domain_list: List[str]) -> List[Dict[str, Any]]:
        """Search for the single news query."""
        
        try:
            search_results = await self.client.search(
                    search_query,
                    max_results=20,
                    include_raw_content=True,
                    topic="general",
                    include_domains=domain_list,
                    exclude_domains=EXCLUDE_DOMAINS
            )
            
            #sort search results by score and return the top 3
            search_results["results"].sort(key=lambda x: x["score"], reverse=True)
            search_results["results"] = search_results["results"][:self._max_items]

            # filter out the empty results
            return [
                self.process_search_result(search_query, result) 
                for result in search_results["results"] 
            ]

        except Exception as e:
            logger.error(f"Error searching {search_query}: {e}")
            return []
        