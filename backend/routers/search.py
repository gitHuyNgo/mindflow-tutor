import logging

from fastapi import APIRouter, HTTPException

from schemas.models import SearchRequest, SearchResponse, SearchResult
from providers.tavily_provider import get_tavily_provider

logger = logging.getLogger(__name__)
router = APIRouter(tags=["search"])


@router.post("/v1/search", response_model=SearchResponse)
async def web_search(request: SearchRequest):
    """Perform a web search using Tavily"""
    try:
        tavily = await get_tavily_provider()
        results = await tavily.search(request.query, max_results=request.max_results)
        return SearchResponse(
            query=results["query"],
            results=[
                SearchResult(
                    title=r["title"],
                    url=r["url"],
                    content=r["content"],
                    score=r["score"]
                )
                for r in results["results"]
            ],
            answer=results.get("answer")
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
