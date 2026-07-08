mcp-wiki

# Wikipedia MCP — Integration Spec

**Server:** `wikipedia-mcp` v3.4.3
**Transport:** stdio
**Protocol:** JSON-RPC 2.0 (MCP 2024-11-05)
**No API key required**

---

## How to Start the Server

```bash
cd cat-health-mcp/wikipedia-mcp
source venv/bin/activate
wikipedia-mcp
```

Or with explicit transport flag:

```bash
wikipedia-mcp --transport stdio
```

---

## Important Note on Duplicate Tools

Every tool appears **twice** in the tools list — once with a plain name (e.g. `search_wikipedia`) and once with a `wikipedia_` prefix (e.g. `wikipedia_search_wikipedia`). They are **identical in behaviour**. Your LangChain agent should use the **plain names** (without the prefix) to keep things clean.

---

## Tools Reference

### 1. `search_wikipedia`

Search Wikipedia for articles matching a query. Use this first to find relevant article titles before fetching full content.

**Input**

| Parameter | Type    | Required | Default | Description                                         |
| --------- | ------- | -------- | ------- | --------------------------------------------------- |
| `query` | string  | yes      | —      | The search term, e.g.`"cat distress meow causes"` |
| `limit` | integer | no       | 10      | Max results to return (1–500)                      |

**Output**

```json
{
  "query": "cat distress meow causes",
  "status": "success",
  "count": 10,
  "language": "en",
  "results": [
    {
      "title": "Cat communication",
      "snippet": "...",
      "pageid": 12345,
      "wordcount": 4200,
      "timestamp": "2024-11-01T00:00:00Z"
    }
  ]
}
```

**Typical cat health use cases:**

- `"cat distress vocalisation"`
- `"feline upper respiratory infection symptoms"`
- `"Persian cat breed characteristics"`
- `"cat pain behaviour signs"`

---

### 2. `get_article`

Get the full content of a Wikipedia article by title. Use the `title` returned from `search_wikipedia`.

**Input**

| Parameter | Type   | Required | Description                             |
| --------- | ------ | -------- | --------------------------------------- |
| `title` | string | yes      | Exact article title from search results |

**Output**

```json
{
  "title": "Cat communication",
  "exists": true,
  "pageid": 12345,
  "summary": "Cat communication includes...",
  "text": "Full article text...",
  "url": "https://en.wikipedia.org/wiki/Cat_communication",
  "sections": [...],
  "categories": ["Cats", "Animal communication"],
  "links": ["Meow", "Purr", "Hiss"]
}
```

> ⚠️ `text` can be very long. Prefer `get_summary` or `summarize_article_for_query` to keep LLM context manageable.

---

### 3. `get_summary`

Get a concise summary of a Wikipedia article. Recommended over `get_article` for most agent use cases.

**Input**

| Parameter | Type   | Required | Description         |
| --------- | ------ | -------- | ------------------- |
| `title` | string | yes      | Exact article title |

**Output**

```json
{
  "title": "Cat communication",
  "summary": "Cat communication includes vocalizations like meowing, purring, trilling..."
}
```

---

### 4. `summarize_article_for_query`

Get a summary snippet from an article focused on a specific query. Most useful for the cat health use case — e.g. pull out only the part about pain symptoms.

**Input**

| Parameter      | Type    | Required | Default | Description                    |
| -------------- | ------- | -------- | ------- | ------------------------------ |
| `title`      | string  | yes      | —      | Article title                  |
| `query`      | string  | yes      | —      | The specific topic to focus on |
| `max_length` | integer | no       | 250     | Max length of the snippet      |

**Output**

```json
{
  "title": "Cat communication",
  "query": "pain vocalization",
  "summary": "Cats in pain may produce high-pitched, repetitive meows..."
}
```

---

### 5. `summarize_article_section`

Get a summary of one specific section within an article.

**Input**

| Parameter         | Type    | Required | Default | Description                      |
| ----------------- | ------- | -------- | ------- | -------------------------------- |
| `title`         | string  | yes      | —      | Article title                    |
| `section_title` | string  | yes      | —      | Name of the section to summarise |
| `max_length`    | integer | no       | 150     | Max length of the summary        |

**Output**

```json
{
  "title": "Cat communication",
  "section_title": "Vocalizations",
  "summary": "Cats use a range of vocalizations including meow, purr, chirp..."
}
```

---

### 6. `extract_key_facts`

Extract a list of key facts from an article, optionally focused on a topic within it.

**Input**

| Parameter                | Type    | Required | Default | Description                    |
| ------------------------ | ------- | -------- | ------- | ------------------------------ |
| `title`                | string  | yes      | —      | Article title                  |
| `topic_within_article` | string  | no       | `""`  | Focus topic within the article |
| `count`                | integer | no       | 5       | Number of facts to extract     |

**Output**

```json
{
  "title": "Persian cat",
  "topic_within_article": "health issues",
  "facts": [
    "Persian cats are prone to polycystic kidney disease.",
    "Their flat faces cause brachycephalic respiratory issues.",
    "..."
  ]
}
```

---

### 7. `get_coordinates`

Get geographic coordinates of a Wikipedia article. Not relevant for this project but available.

---

### 8. `test_wikipedia_connectivity`

Diagnostic tool — checks if the Wikipedia API is reachable. No parameters needed. Returns response time in ms.

---

## Recommended Agent Tool Call Sequence

For the cat health diagnosis flow, your agent should chain these tools like this:

```
1. search_wikipedia(query="<cat symptom or breed>")
   → get article titles from results

2. summarize_article_for_query(title="<best result>", query="<specific symptom>")
   → get focused context for the LLM

3. extract_key_facts(title="<article>", topic_within_article="<symptom>")
   → get bullet-point facts for the LLM to reason over
```

Avoid calling `get_article` directly — the full text is too long and will bloat the LLM context window.

---

## LangChain MCP Config

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "wikipedia": {
        "command": "/absolute/path/to/wikipedia-mcp/venv/bin/wikipedia-mcp",
        "args": [],
        "transport": "stdio",
    }
})
```
