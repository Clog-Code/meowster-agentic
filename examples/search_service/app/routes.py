"""FastAPI routes for the search service."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.duckduckgo import web_search
from app.serpapi import visual_search

router = APIRouter()


class WebSearchRequest(BaseModel):
    """Request body for the web search endpoint."""

    query: str
    max_results: int = 5


class VisualSearchRequest(BaseModel):
    """Request body for the visual search endpoint."""

    image_url: str
    max_results: int = 10


@router.post("/web-search")
def search(request: WebSearchRequest):
    """Perform a web search and return normalised results."""
    try:
        results = web_search(request.query, request.max_results)
        return {"query": request.query, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}") from e


@router.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "search-service"}


@router.post("/visual-search")
def search_visual(request: VisualSearchRequest):
    """Perform a visual search and return normalised matches."""
    try:
        results = visual_search(request.image_url, request.max_results)
        return {
            "image_url": request.image_url,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Visual search failed: {str(e)}"
        ) from e
