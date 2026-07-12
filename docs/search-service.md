# Search Service

Handles web search and visual search capabilities for the MeowDoc cat health AI system.

## Prerequisites

- Python 3.12+
- A SerpAPI account (free tier at serpapi.com — 100 searches/month)

## Setup

The service lives at `examples/search_service`. Its dependencies (`ddgs`,
`google-search-results`) are declared in the main `dependencies` list of
`pyproject.toml` alongside `fastapi`, `uvicorn`, `python-dotenv`, and
`requests`.

Create a `.env` file in `examples/search_service`:

```
SERPAPI_KEY=your_serpapi_key_here
```

No API key needed for DuckDuckGo web search.

## Run

```bash
cd examples/search_service
uvicorn main:app --reload --port 8002
```

## Endpoints

| Method | Endpoint           | Description                             |
| ------ | ------------------ | --------------------------------------- |
| POST   | `/web-search`    | Search the web via DuckDuckGo           |
| POST   | `/visual-search` | Visual search via Google Lens (SerpAPI) |
| GET    | `/health`        | Health check                            |
| GET    | `/docs`          | Interactive API docs                    |

## Example Requests

### Web Search

```bash
curl -X POST "http://localhost:8002/web-search" \
-H "Content-Type: application/json" \
-d '{"query": "Persian cat eye discharge treatment", "max_results": 5}'
```

Response:

```json
{
  "query": "Persian cat eye discharge treatment",
  "count": 5,
  "results": [
    {
      "title": "How to Treat Cat Eye Discharge",
```
