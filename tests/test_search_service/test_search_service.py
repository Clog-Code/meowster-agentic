"""Unit tests for the search tools (agent/tools/search/*) — no network needed."""

import os
import sys
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

os.environ.setdefault("SERPAPI_KEY", "test-serpapi-key")

# pylint: disable=wrong-import-position
import agent.tools.search.duckduckgo_tool as ddg
import agent.tools.search.serpapi_tool as serp

# ---------------------------------------------------------------------------
# web_search (DuckDuckGo)
# ---------------------------------------------------------------------------


def _fake_ddgs_context(results):
    """Build a mocked DDGS() context manager yielding the given text results."""
    fake_ddgs = mock.MagicMock()
    fake_ddgs.text.return_value = results
    cm = mock.MagicMock()
    cm.__enter__.return_value = fake_ddgs
    cm.__exit__.return_value = False
    return cm


def test_web_search_maps_fields():
    """web_search maps title/href/body into title/url/snippet."""
    raw = [
        {
            "title": "Cat Eye Care",
            "href": "https://example.com/eyes",
            "body": "Keep them clean.",
        },
        {"title": "Another", "href": "https://example.com/2", "body": "More info."},
    ]
    patch_path = "agent.tools.search.duckduckgo_tool.DDGS"
    with mock.patch(patch_path, return_value=_fake_ddgs_context(raw)):
        result = ddg.web_search.invoke({"query": "persian cat eyes", "max_results": 5})
    assert result["success"] is True
    assert result["count"] == 2
    assert result["results"][0] == {
        "title": "Cat Eye Care",
        "url": "https://example.com/eyes",
        "snippet": "Keep them clean.",
    }
    assert result["results"][1]["url"] == "https://example.com/2"


def test_web_search_respects_max_results():
    """web_search forwards max_results to the underlying DDGS text call."""
    raw = [
        {"title": f"r{i}", "href": f"https://e.com/{i}", "body": "b"} for i in range(10)
    ]
    fake_ddgs = mock.MagicMock()
    fake_ddgs.text.return_value = raw
    cm = mock.MagicMock()
    cm.__enter__.return_value = fake_ddgs
    cm.__exit__.return_value = False
    patch_path = "agent.tools.search.duckduckgo_tool.DDGS"
    with mock.patch(patch_path, return_value=cm):
        ddg.web_search.invoke({"query": "cats", "max_results": 3})
    _, kwargs = fake_ddgs.text.call_args  # pylint: disable=no-member
    assert kwargs["max_results"] == 3


def test_web_search_error_returns_failure():
    """web_search returns a failure dict when DDGS raises."""
    cm = mock.MagicMock()
    cm.__enter__.side_effect = RuntimeError("DDGS unavailable")
    cm.__exit__.return_value = False
    patch_path = "agent.tools.search.duckduckgo_tool.DDGS"
    with mock.patch(patch_path, return_value=cm):
        result = ddg.web_search.invoke({"query": "cats"})
    assert result["success"] is False
    assert "DDGS unavailable" in result["error"]


# ---------------------------------------------------------------------------
# visual_search (SerpAPI / Google Lens)
# ---------------------------------------------------------------------------


def test_visual_search_maps_matches():
    """visual_search (via URL) maps visual_matches into the expected shape."""
    raw = {
        "visual_matches": [
            {
                "position": 1,
                "title": "Orange Tabby",
                "link": "https://example.com/tabby",
                "source": "example.com",
                "thumbnail": "https://example.com/t.jpg",
                "image": "https://example.com/t.png",
            }
        ]
    }
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = raw
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(patch_path, return_value=fake_search):
        result = serp.visual_search.invoke(
            {"image_url": "https://example.com/cat.jpg", "max_results": 10}
        )
    assert result["success"] is True
    assert result["count"] == 1
    match = result["results"][0]
    assert match["position"] == 1
    assert match["title"] == "Orange Tabby"
    assert match["link"] == "https://example.com/tabby"
    assert match["source"] == "example.com"
    assert match["thumbnail"] == "https://example.com/t.jpg"
    assert match["image"] == "https://example.com/t.png"


def test_visual_search_limits_results():
    """visual_search truncates to max_results."""
    raw = {
        "visual_matches": [
            {
                "position": i,
                "title": f"m{i}",
                "link": f"l{i}",
                "source": "s",
                "thumbnail": "t",
                "image": "i",
            }
            for i in range(5)
        ]
    }
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = raw
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(patch_path, return_value=fake_search):
        result = serp.visual_search.invoke(
            {"image_url": "https://example.com/cat.jpg", "max_results": 2}
        )
    assert result["success"] is True
    assert result["count"] == 2


def test_visual_search_raises_on_api_error():
    """visual_search reports error when SerpAPI returns an error payload."""
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {"error": "Invalid API key"}
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(patch_path, return_value=fake_search):
        result = serp.visual_search.invoke({"image_url": "https://example.com/cat.jpg"})
    assert result["success"] is False
    assert "Invalid API key" in result["error"]


def test_visual_search_empty_when_no_matches():
    """visual_search returns empty results when there are no matches."""
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {}
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(patch_path, return_value=fake_search):
        result = serp.visual_search.invoke({"image_url": "https://example.com/cat.jpg"})
    assert result["success"] is True
    assert result["results"] == []


def test_visual_search_requires_url_or_path():
    """visual_search fails if neither image_url nor image_path is given."""
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {}
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(patch_path, return_value=fake_search):
        result = serp.visual_search.invoke({})
    assert result["success"] is False
    assert "image_path" in result["error"] or "image_url" in result["error"]


def test_visual_search_local_file(tmp_path):
    """visual_search (via local file) uploads to catbox.moe and sends the public URL."""
    img_file = Path(tmp_path) / "test_cat.jpg"
    img_file.write_bytes(b"fake-image-bytes")

    fake_post_resp = mock.Mock()
    fake_post_resp.raise_for_status.return_value = None
    fake_post_resp.text = "https://files.catbox.moe/uploaded.jpg"

    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {
        "visual_matches": [
            {
                "position": 1,
                "title": "Local Cat",
                "link": "https://example.com/local",
                "source": "example.com",
                "thumbnail": "https://example.com/t.jpg",
                "image": "https://example.com/t.png",
            }
        ]
    }
    patch_path = "agent.tools.search.serpapi_tool.GoogleSearch"
    with mock.patch(
        "agent.tools.search.serpapi_tool.requests.post", return_value=fake_post_resp
    ):
        with mock.patch(patch_path, return_value=fake_search) as mock_gs:
            result = serp.visual_search.invoke(
                {"image_path": str(img_file), "max_results": 5}
            )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["results"][0]["title"] == "Local Cat"

    call_args, _ = mock_gs.call_args
    params = call_args[0]
    assert "url" in params
    assert params["url"] == "https://files.catbox.moe/uploaded.jpg"


def test_visual_search_local_file_not_found(monkeypatch):
    """visual_search returns an error when the local file does not exist."""
    monkeypatch.setenv("SERPAPI_KEY", "test-key")
    result = serp.visual_search.invoke({"image_path": "/nonexistent/no-cat.jpg"})
    assert result["success"] is False
    assert "not found" in result["error"]


def test_visual_search_not_configured_returns_stub(monkeypatch):
    """visual_search returns a stub when SERPAPI_KEY is not set."""
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    result = serp.visual_search.invoke({"image_url": "https://example.com/cat.jpg"})
    assert result["success"] is False
    assert "not configured" in result["error"]


# ---------------------------------------------------------------------------
# Tool-list exports via package __init__
# ---------------------------------------------------------------------------


def test_search_tools_exported():
    """SEARCH_TOOLS is re-exported from the package __init__."""
    from agent.tools.search import SEARCH_TOOLS  # pylint: disable=import-outside-toplevel

    tool_names = {t.name for t in SEARCH_TOOLS}
    assert "web_search" in tool_names
    assert "visual_search" in tool_names
