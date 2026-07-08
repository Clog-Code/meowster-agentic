import os
import subprocess
import json
import time
from dotenv import load_dotenv

load_dotenv()

proc = subprocess.Popen(
    [os.environ["WIKIPEDIA_MCP_PATH"]],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)


def send(proc, id, method, params={}):
    msg = (
        json.dumps({"jsonrpc": "2.0", "id": id, "method": method, "params": params})
        + "\n"
    )
    proc.stdin.write(msg.encode())
    proc.stdin.flush()


# Initialize
send(
    proc,
    1,
    "initialize",
    {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"},
    },
)

# Test 1 — search for articles
send(
    proc,
    2,
    "tools/call",
    {
        "name": "search_wikipedia",
        "arguments": {"query": "cat distress vocalisation", "limit": 3},
    },
)

# Test 2 — get summary of specific article
send(
    proc,
    3,
    "tools/call",
    {"name": "get_summary", "arguments": {"title": "Cat communication"}},
)

# Test 3 — focused summary around a specific topic
send(
    proc,
    4,
    "tools/call",
    {
        "name": "summarize_article_for_query",
        "arguments": {
            "title": "Cat communication",
            "query": "pain vocalization",
            "max_length": 300,
        },
    },
)

time.sleep(4)
proc.stdin.close()

output = proc.stdout.read().decode()
for line in output.strip().split("\n"):
    try:
        print(json.dumps(json.loads(line), indent=2))
    except Exception:
        print(line)
