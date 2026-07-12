"""FastAPI routes for the search service (uses agent/tools/search)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agent.tools.search.duckduckgo_tool import web_search
from agent.tools.search.serpapi_tool import visual_search

router = APIRouter()


class WebSearchRequest(BaseModel):
    """Request body for the web search endpoint."""

    query: str
    max_results: int = 5


class VisualSearchRequest(BaseModel):
    """Request body for the visual search endpoint."""

    image_url: str = ""
    image_path: str = ""
    max_results: int = 10


@router.post("/web-search")
def search(request: WebSearchRequest):
    """Perform a web search and return normalised results."""
    try:
        result = web_search.invoke(
            {"query": request.query, "max_results": request.max_results}
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "search failed"))
        return {
            "query": request.query,
            "count": result["count"],
            "results": result["results"],
        }
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
        kwargs: dict[str, str | int] = {"max_results": request.max_results}
        if request.image_url:
            kwargs["image_url"] = request.image_url
        if request.image_path:
            kwargs["image_path"] = request.image_path
        result = visual_search.invoke(kwargs)
        if not result["success"]:
            raise RuntimeError(result.get("error", "visual search failed"))
        return {
            "image_url": request.image_url,
            "image_path": request.image_path or None,
            "count": result["count"],
            "results": result["results"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Visual search failed: {str(e)}"
        ) from e
