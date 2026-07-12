"""DuckDuckGo web search helper."""

import time

from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> list:
    """Run a web search and return normalised results."""
    results = []
    time.sleep(1)  # avoid rate limiting
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
    return results
