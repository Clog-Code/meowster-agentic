"""Visual search tool backed by SerpAPI / Google Lens.

Supports both remote image URLs and local image files (automatically
base64-encoded for the API).
"""

import base64
import os
from typing import Any, Optional

from dotenv import load_dotenv
from langchain_core.tools import tool
from serpapi import GoogleSearch

load_dotenv()

SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")


def _serpapi_configured() -> bool:
    return bool(os.getenv("SERPAPI_KEY"))


def _stub(image_path: str, image_url: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": (
            "SerpAPI is not configured. Set SERPAPI_KEY in .env to enable "
            "visual search."
        ),
        "image_path": image_path or None,
        "image_url": image_url or None,
        "results": [],
    }


@tool
def visual_search(
    image_path: str = "",
    image_url: str = "",
    max_results: int = 10,
) -> dict[str, Any]:
    """
    Perform a Google Lens visual / reverse-image search via SerpAPI.

    Provide *either* a local image file path (`image_path`) or a remote
    image URL (`image_url`), not both.

    Useful for identifying a cat breed from a photo, finding visually
    similar skin/coat conditions, or retrieving information about an
    unknown object or product from an image.

    Args:
        image_path: Absolute or relative path to a local image file.
        image_url:  Public URL of the image to search.
        max_results: Maximum number of visual matches to return (default 10).

    Returns:
        A dict with a 'results' list, each containing 'position', 'title',
        'link', 'source', 'thumbnail', and 'image' keys.
    """
    if not _serpapi_configured():
        return _stub(image_path, image_url)

    if not image_path and not image_url:
        return {
            "success": False,
            "error": "Provide either image_path or image_url.",
            "results": [],
        }

    params: dict[str, Any] = {
        "engine": "google_lens",
        "type": "visual_matches",
        "api_key": SERPAPI_KEY,
    }

    if image_path:
        try:
            with open(image_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            params["image_data"] = encoded
        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Image file not found: {image_path}",
                "results": [],
            }
        except OSError as exc:
            return {
                "success": False,
                "error": f"Failed to read image file: {exc}",
                "results": [],
            }
    else:
        params["url"] = image_url

    try:
        search = GoogleSearch(params)
        results = search.get_dict()
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "results": [],
        }

    if "error" in results:
        return {
            "success": False,
            "error": results["error"],
            "results": [],
        }

    visual_matches = results.get("visual_matches", [])

    return {
        "success": True,
        "image_path": image_path or None,
        "image_url": image_url or None,
        "count": len(visual_matches[:max_results]),
        "results": [
            {
                "position": m.get("position"),
                "title": m.get("title"),
                "link": m.get("link"),
                "source": m.get("source"),
                "thumbnail": m.get("thumbnail"),
                "image": m.get("image"),
            }
            for m in visual_matches[:max_results]
        ],
    }


SEARCH_SERPAPI_TOOLS = [visual_search]
