"""SerpAPI visual search helper."""

import os

from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def visual_search(image_url: str, max_results: int = 10) -> list:
    """Run a Google Lens visual search and return normalised matches."""
    params = {
        "engine": "google_lens",
        "url": image_url,
        "type": "visual_matches",
        "api_key": SERPAPI_KEY,
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    if "error" in results:
        raise RuntimeError(results["error"])

    visual_matches = results.get("visual_matches", [])

    return [
        {
            "position": match.get("position"),
            "title": match.get("title"),
            "link": match.get("link"),
            "source": match.get("source"),
            "thumbnail": match.get("thumbnail"),
            "image": match.get("image"),
        }
        for match in visual_matches[:max_results]
    ]
