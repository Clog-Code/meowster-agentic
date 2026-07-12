"""Web search tool backed by DuckDuckGo (no API key needed)."""

import time
from typing import Any

from ddgs import DDGS
from langchain_core.tools import tool


@tool
def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """
    Search the web via DuckDuckGo and return normalised results.

    Useful for finding up-to-date pet care advice, veterinary reference
    material, clinic websites, and general knowledge the LLM might not
    have in its training data.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return (default 5).

    Returns:
        A dict with a 'results' list, each containing 'title', 'url',
        and 'snippet' keys.
    """
    results: list[dict[str, Any]] = []
    time.sleep(1)
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(
                query,
                max_results=max_results,
                region="wt-wt",
                safesearch="off",
                backend="lite",
            ):
                results.append(
                    {
                        "title": result.get("title"),
                        "url": result.get("href"),
                        "snippet": result.get("body"),
                    }
                )
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "results": [],
        }

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "results": results,
    }


SEARCH_DUCKDUCKGO_TOOLS = [web_search]
