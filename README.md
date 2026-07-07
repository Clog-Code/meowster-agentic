# Pet Companion — Module 2: Autonomous Intervention

Backend service for the **Health & Medical Emergency** and **Supply Chain &
Inventory** workflows from the AI Pet Companion architecture. Built with
LangChain **deepagents**, a self-discovering **MCP** layer, and **AG-UI**
event streaming over a single FastAPI app.

This service is backend-only. `static/` is a throwaway test harness for
exercising the AG-UI contract during development — the real frontend is a
separate Flutter app talking to the same `/agent` and `/perception` routes.

## How the pieces fit together

```
Module 1 (ML: video/audio → species/emotion/health/food/water)
        │  POST /perception  (JSON, see backend/main.py::PerceptionPayload)
        ▼
agent/core/perception.py   — classify: health_emergency | supply_shortage | info_only
        ▼
agent/core/runner.py       — create_deep_agent orchestrator (agent/prompts/initializer_prompt.md)
        │
        ├─ subagent: vet-emergency      (maps MCP + calendar + communication tools)
        ├─ subagent: supply-inventory   (maps MCP + commerce tools)
        └─ subagent: pet-info-lookup    (wikipedia MCP, read-only)
        ▼
AG-UI SSE events  ──►  static/ test page  or  Flutter app
```

## Setup

```bash
cp .env.example .env   # fill in all values
uv pip install -r requirements.txt
```

Run it:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000/` for the test harness, or `http://localhost:8000/docs`
for the OpenAPI schema.

## Adding a new MCP plugin (self-discovery)

No code changes needed — just edit `.env`:

```bash
MCP_SERVERS=maps,wikipedia,petstore

MCP_PETSTORE_URL=https://your-petstore-mcp.example.com/mcp
MCP_PETSTORE_TRANSPORT=streamable_http
MCP_PETSTORE_API_KEY=your-key
```

`agent/mcp/config.py` reads `MCP_SERVERS` and builds a connection spec per
name; `agent/mcp/loader.py` connects and calls `get_tools()` on each server,
so every tool the plugin exposes is discovered automatically. To let a
subagent use it, add the server name to that subagent's `tools:` field in
its `AGENT.md` (see `agent/subagents/*/AGENT.md`) — the name just needs to
match what's in `MCP_SERVERS`.

Stdio-transport plugins are supported too — use `MCP_<NAME>_COMMAND` /
`MCP_<NAME>_ARGS` instead of `_URL` (see `.env.example`).

## What's stubbed vs. functional

| Tool                        | File                                            | Status                                                       |
| --------------------------- | ----------------------------------------------- | ------------------------------------------------------------ |
| `make_phone_call`         | `agent/tools/communication/call_tool.py`      | **Stub** — wire up Twilio or similar                  |
| `send_email`              | `agent/tools/communication/email_tool.py`     | **Stub** — wire up SMTP/SendGrid/etc.                 |
| `send_whatsapp_message`   | `agent/tools/communication/whatsapp_tool.py`  | **Stub** — wire up WhatsApp Business API              |
| `place_order`             | `agent/tools/commerce/order_tool.py`          | **Stub** — wire up retailer API + TnG/payment gateway |
| `get_user_availability`   | `agent/tools/calendar/availability_tool.py`   | **Stub** — wire up Google Calendar/Outlook            |
| `calculate_daily_portion` | `agent/tools/commerce/nutrition_tool.py`      | ✅ Functional (RER/DER veterinary formulas)                  |
| `get_pet_profile`         | `agent/tools/pet_profile/pet_profile_tool.py` | ✅ Functional (reads`backend/db.py` SQLite)                |

Every stub returns `{"status": "stubbed", ...}` and logs a clear TODO —
subagents and skills are instructed to always surface that to the user
rather than claim a real action happened.

## Testing without a live LLM/MCP setup

```bash
python tests/test_perception_routing.py   # workflow classification logic
python tests/test_mcp_config.py           # env-driven MCP self-discovery
```

Both run standalone, no network or API keys required.

## Folder structure

```
pet-module2-agent/
├── agent/
│   ├── config.py, llm.py
│   ├── core/            # registry, events, messages, perception, runner
│   ├── mcp/              # self-discovery config + loader
│   ├── tools/             # communication/, commerce/, calendar/, pet_profile/
│   ├── filesystem/        # paths, prompts, subagent loader
│   ├── backends/          # skills-only filesystem backend (no sandbox)
│   ├── prompts/           # initializer_prompt.md, thread_title_prompt.md
│   ├── subagents/         # vet-emergency/, supply-inventory/, pet-info-lookup/
│   └── skills/            # emergency-booking/, supply-ordering/, pet-species-lookup/
├── backend/               # FastAPI app, db, services
├── static/                # dev-only AG-UI test harness (not the product frontend)
├── tests/
├── .env.example
└── requirements.txt
```
