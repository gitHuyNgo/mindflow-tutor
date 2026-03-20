import os
import logging
from typing import List, Optional
from tavily import AsyncTavilyClient
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class TavilyProvider:
    """Provider for Tavily web search"""
    
    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY")
        self.client = AsyncTavilyClient(api_key=self.api_key)
    
    async def search(
        self, 
        query: str, 
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True
    ) -> dict:
        """Perform a web search"""
        try:
            response = await self.client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
                include_answer=include_answer,
                include_images=False
            )
            
            return {
                "query": query,
                "results": [
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    }
                    for result in response.get("results", [])
                ],
                "answer": response.get("answer")
            }
        except Exception as e:
            logger.error(f"Error performing search: {e}")
            raise
    
    async def search_educational(self, topic: str, max_results: int = 3) -> dict:
        """Search for educational content about a topic"""
        query = f"explain {topic} tutorial beginner guide"
        return await self.search(query, max_results=max_results, search_depth="advanced")


# Singleton instance
_tavily_provider: Optional[TavilyProvider] = None

async def get_tavily_provider() -> TavilyProvider:
    global _tavily_provider
    if _tavily_provider is None:
        _tavily_provider = TavilyProvider()
    return _tavily_provider
