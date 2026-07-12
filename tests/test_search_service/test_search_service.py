"""Unit tests for the search-service helpers and routes (no network needed)."""

import os
import sys
from pathlib import Path
from unittest import mock

SEARCH_SERVICE = (
    Path(__file__).resolve().parent.parent.parent / "examples" / "search_service"
)
sys.path.insert(0, str(SEARCH_SERVICE))

os.environ.setdefault("SERPAPI_KEY", "test-serpapi-key")

# The search-service depends on third-party clients (ddgs, serpapi) that are
# not required by the agentic test environment. Inject lightweight fakes so the
# modules import cleanly; individual tests patch the clients as needed.
sys.modules.setdefault("ddgs", mock.MagicMock())
sys.modules.setdefault("serpapi", mock.MagicMock())

# pylint: disable-next=wrong-import-position
from app.duckduckgo import web_search  # noqa: E402

# pylint: disable-next=wrong-import-position
from app.serpapi import visual_search  # noqa: E402


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
    with mock.patch("app.duckduckgo.DDGS", return_value=_fake_ddgs_context(raw)):
        results = web_search("persian cat eyes", 5)
    assert len(results) == 2
    assert results[0] == {
        "title": "Cat Eye Care",
        "url": "https://example.com/eyes",
        "snippet": "Keep them clean.",
    }
    assert results[1]["url"] == "https://example.com/2"


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
    with mock.patch("app.duckduckgo.DDGS", return_value=cm):
        web_search("cats", 3)
    _, kwargs = fake_ddgs.text.call_args
    assert kwargs["max_results"] == 3


# ---------------------------------------------------------------------------
# visual_search (SerpAPI / Google Lens)
# ---------------------------------------------------------------------------


def test_visual_search_maps_matches():
    """visual_search maps visual_matches into the expected shape."""
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
    with mock.patch("app.serpapi.GoogleSearch", return_value=fake_search):
        results = visual_search("https://example.com/cat.jpg", 10)
    assert len(results) == 1
    match = results[0]
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
    with mock.patch("app.serpapi.GoogleSearch", return_value=fake_search):
        results = visual_search("https://example.com/cat.jpg", 2)
    assert len(results) == 2


def test_visual_search_raises_on_api_error():
    """visual_search raises when SerpAPI returns an error payload."""
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {"error": "Invalid API key"}
    with mock.patch("app.serpapi.GoogleSearch", return_value=fake_search):
        try:
            visual_search("https://example.com/cat.jpg")
            assert False, "expected Exception"
        except Exception as exc:  # noqa: BLE001
            assert "Invalid API key" in str(exc)


def test_visual_search_empty_when_no_matches():
    """visual_search returns an empty list when there are no matches."""
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = {}
    with mock.patch("app.serpapi.GoogleSearch", return_value=fake_search):
        results = visual_search("https://example.com/cat.jpg")
    assert results == []


# ---------------------------------------------------------------------------
# FastAPI routes (only when fastapi is available)
# ---------------------------------------------------------------------------


pytest = __import__("pytest")
fastapi = pytest.importorskip("fastapi")


def _client():
    # pylint: disable=import-outside-toplevel
    from fastapi.testclient import TestClient
    import main

    return TestClient(main.app)


def test_health_endpoint():
    """The /health endpoint reports ok without auth or network."""
    client = _client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "search-service"}


def test_web_search_route():
    """POST /web-search maps query results through the route."""
    raw = [{"title": "t", "href": "https://e.com", "body": "b"}]
    with mock.patch("app.duckduckgo.DDGS", return_value=_fake_ddgs_context(raw)):
        client = _client()
        resp = client.post("/web-search", json={"query": "cats", "max_results": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "cats"
    assert body["count"] == 1
    assert body["results"][0]["url"] == "https://e.com"


def test_visual_search_route():
    """POST /visual-search maps visual matches through the route."""
    raw = {
        "visual_matches": [
            {
                "position": 1,
                "title": "t",
                "link": "l",
                "source": "s",
                "thumbnail": "th",
                "image": "im",
            }
        ]
    }
    fake_search = mock.Mock()
    fake_search.get_dict.return_value = raw
    with mock.patch("app.serpapi.GoogleSearch", return_value=fake_search):
        client = _client()
        resp = client.post(
            "/visual-search",
            json={"image_url": "https://e.com/c.jpg", "max_results": 10},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["image_url"] == "https://e.com/c.jpg"
    assert body["count"] == 1
    assert body["results"][0]["title"] == "t"


def test_web_search_route_error_returns_500():
    """The web-search route surfaces failures as HTTP 500."""
    cm = mock.MagicMock()
    cm.__enter__.side_effect = RuntimeError("boom")
    cm.__exit__.return_value = False
    with mock.patch("app.duckduckgo.DDGS", return_value=cm):
        client = _client()
        resp = client.post("/web-search", json={"query": "cats"})
    assert resp.status_code == 500
    assert "Search failed" in resp.json()["detail"]
