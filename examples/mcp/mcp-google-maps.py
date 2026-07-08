import os
import subprocess
import json
import time
from dotenv import load_dotenv

load_dotenv()

proc = subprocess.Popen(
    ["node", "node_modules/@modelcontextprotocol/server-google-maps/dist/index.js"],
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

# Call maps_search_places — search for vet clinics in KL
send(
    proc,
    2,
    "tools/call",
    {
        "name": "maps_search_places",
        "arguments": {
            "query": "vet clinic",
            "location": {"lat": 3.1390, "lng": 101.6869},
            "radius": 5000,
        },
    },
)

# maps_place_details
send(
    proc,
    3,
    "tools/call",
    {
        "name": "maps_place_details",
        "arguments": {"place_id": "ChIJp92YC5RLzDER8Augxs2PEn4"},
    },
)

time.sleep(3)
proc.stdin.close()

output = proc.stdout.read().decode()
for line in output.strip().split("\n"):
    try:
        print(json.dumps(json.loads(line), indent=2))
    except Exception:
        print(line)
