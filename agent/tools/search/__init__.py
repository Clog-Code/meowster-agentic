"""Web and visual search tools (DuckDuckGo + SerpAPI)."""

from .duckduckgo_tool import SEARCH_DUCKDUCKGO_TOOLS
from .serpapi_tool import SEARCH_SERPAPI_TOOLS

SEARCH_TOOLS = [*SEARCH_DUCKDUCKGO_TOOLS, *SEARCH_SERPAPI_TOOLS]

__all__ = ["SEARCH_TOOLS"]
