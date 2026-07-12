# Search Service

Handles web search and visual search capabilities for the MeowDoc cat health AI system.

This is a self-contained FastAPI service that demonstrates how the agentic
layer can call cat-health web and image searches. It lives under
`examples/search_service` within this repository.

## Prerequisites

- Python 3.12+
- A SerpAPI account (free tier at serpapi.com — 100 searches/month)

## Setup

```bash
python3.13 -m venv venv
source venv/bin/activate
pip install -e .
```

The search-service dependencies (`ddgs`, `google-search-results`) are declared
in the main `dependencies` list of `amd-pet-agentic/pyproject.toml` alongside
`fastapi`, `uvicorn`, `python-dotenv`, and `requests`.

Create a `.env` file in this folder:

```
SERPAPI_KEY=your_serpapi_key_here
```

No API key needed for DuckDuckGo web search.

## Run

```bash
source venv/bin/activate
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

### Visual Search

```bash
curl -X POST "http://localhost:8002/visual-search" \
-H "Content-Type: application/json" \
-d '{"image_url": "https://example.com/cat.jpg", "max_results": 10}'
```
