"""Visual search tool backed by SerpAPI / Google Lens.

SerpAPI only accepts a public image URL — it has no file-upload endpoint.
For local files, the image is first uploaded to catbox.moe (free, no API
key required) to obtain a public URL, which is then passed to Google Lens.
"""

import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool
from serpapi import GoogleSearch

load_dotenv()

SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
_CATBOX_URL = "https://catbox.moe/user/api.php"


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


def _publish_local_file(image_path: str) -> tuple[str | None, str | None]:
    """Upload a local file to catbox.moe and return (public_url, error)."""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                _CATBOX_URL,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(image_path), f)},
                timeout=30,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if not url.startswith("http"):
            return None, f"catbox.moe returned unexpected response: {url}"
        return url, None
    except FileNotFoundError:
        return None, f"Image file not found: {image_path}"
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        text = exc.response.text if exc.response is not None else "?"
        return None, f"Upload failed ({status}): {text}"
    except OSError as exc:
        return None, f"Failed to read image file: {exc}"
    except Exception as exc:
        return None, str(exc)


def _run_lens(url: str, max_results: int) -> dict[str, Any]:
    """Run Google Lens against a public URL and return normalised results."""
    try:
        search = GoogleSearch(
            {
                "engine": "google_lens",
                "type": "visual_matches",
                "url": url,
                "api_key": SERPAPI_KEY,
            }
        )
        data = search.get_dict()
    except Exception as exc:
        return {"success": False, "error": str(exc), "results": []}

    if "error" in data:
        return {"success": False, "error": data["error"], "results": []}

    matches = data.get("visual_matches", [])[:max_results]
    return {
        "success": True,
        "count": len(matches),
        "results": [
            {
                "position": m.get("position"),
                "title": m.get("title"),
                "link": m.get("link"),
                "source": m.get("source"),
                "thumbnail": m.get("thumbnail"),
                "image": m.get("image"),
            }
            for m in matches
        ],
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

    Local files are automatically published to a temporary public host so
    Google Lens can process them — no manual hosting required.

    Useful for identifying a pet breed from a photo, finding visually
    similar skin/coat conditions, or retrieving information about an
    unknown object or product from an image.

    Args:
        image_path: Absolute path to a local image file.
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

    if image_path:
        public_url, err = _publish_local_file(image_path)
        if err:
            return {"success": False, "error": err, "results": []}
        assert public_url is not None
        result = _run_lens(public_url, max_results)
        result["image_path"] = image_path
        result["published_url"] = public_url
        return result

    result = _run_lens(image_url, max_results)
    result["image_url"] = image_url
    return result


SEARCH_SERPAPI_TOOLS = [visual_search]
