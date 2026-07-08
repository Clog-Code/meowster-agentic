# Google Maps MCP — Integration Spec

**Server:** `@modelcontextprotocol/server-google-maps` v0.6.2  
**Transport:** stdio  
**Protocol:** JSON-RPC 2.0  
**Requires:** `GOOGLE_MAPS_API_KEY` environment variable (Places API New enabled)

---

## How to Start the Server

```bash
GOOGLE_MAPS_API_KEY=your_actual_key_here npx mcp-server-google-maps
```

Expected output:
```
Google Maps MCP Server running on stdio
```

---

## Tools Reference

### 1. `maps_search_places`
Search for nearby places using the Google Maps Places API. This is the primary tool for finding vets and pet shops near the user.

**Input**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | yes | What to search for, e.g. `"vet clinic"` or `"pet shop"` |
| `location` | object | yes | `{ "lat": 3.1390, "lng": 101.6869 }` |
| `radius` | integer | yes | Search radius in meters. Max 50,000 (50km) |

**Example call**
```json
{
  "query": "vet clinic",
  "location": { "lat": 3.1390, "lng": 101.6869 },
  "radius": 5000
}
```

**Output** — returns a list of places, each with:
- `name` — place name
- `place_id` — unique ID (pass this to `maps_place_details` for more info)
- `address` — formatted address
- `rating` — Google rating (if available)
- `location` — lat/lng of the place

**Typical cat health use cases**
| Scenario | Query |
|---|---|
| Cat is sick / in pain | `"vet clinic"` or `"animal hospital"` |
| Cat needs food | `"pet shop"` or `"pet supplies store"` |
| Emergency | `"emergency vet"` or `"24 hour animal clinic"` |

> ⚠️ The Flutter app must send the user's GPS coordinates (lat/lng) to the agent so this tool has a location to search from.

---

### 2. `maps_place_details`
Get detailed information about a specific place using its `place_id`. Use this after `maps_search_places` to get phone numbers, opening hours, and website for a selected clinic or shop.

**Input**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `place_id` | string | yes | The `place_id` returned from `maps_search_places` |

**Example call**
```json
{
  "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"
}
```

**Output** — returns detailed info including:
- `name` — place name
- `formatted_address` — full address
- `formatted_phone_number` — phone number to call or WhatsApp
- `opening_hours` — opening days and times
- `website` — clinic/shop website
- `rating` — Google rating
- `reviews` — user reviews (if available)

**Recommended agent flow:**
```
maps_search_places → user picks a clinic → maps_place_details(place_id) → show phone + hours
```

---

### 3. `maps_geocode`
Convert a human-readable address into geographic coordinates (lat/lng). Useful if the user types their address instead of sharing GPS.

**Input**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `address` | string | yes | Address to convert, e.g. `"Bukit Jalil, Kuala Lumpur"` |

**Example call**
```json
{
  "address": "Bukit Jalil, Kuala Lumpur, Malaysia"
}
```

**Output**
```json
{
  "lat": 3.0580,
  "lng": 101.6974,
  "formatted_address": "Bukit Jalil, 57000 Kuala Lumpur, Malaysia"
}
```

**When to use:** Only needed if the Flutter app cannot provide GPS coordinates directly. If the app sends lat/lng from the device, this tool is not needed.

---

### 4. `maps_directions`
Get directions between two points. Useful if the agent wants to show the user how to get to the selected vet clinic.

**Input**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `origin` | string | yes | Starting point — address or `"lat,lng"` string |
| `destination` | string | yes | End point — address or place name |
| `travel_mode` | string | yes | One of: `drive`, `walk`, `bicycle`, `transit` |

**Example call**
```json
{
  "origin": "3.1390,101.6869",
  "destination": "Klinik Haiwan Damansara, Kuala Lumpur",
  "travel_mode": "drive"
}
```

**Output** — returns:
- `distance` — total distance (e.g. `"3.2 km"`)
- `duration` — estimated travel time (e.g. `"12 mins"`)
- `steps` — turn-by-turn directions

**Recommended use:** Call this after the user confirms which clinic they want to go to.

---

### 5. `maps_distance_matrix`
Calculate travel distance and time between multiple origins and multiple destinations in one call. Useful for ranking which of several clinics is closest to the user.

**Input**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `origins` | array | yes | List of starting points e.g. `["3.1390,101.6869"]` |
| `destinations` | array | yes | List of end points e.g. `["Clinic A", "Clinic B", "Clinic C"]` |
| `travel_mode` | string | yes | One of: `drive`, `walk`, `bicycle`, `transit` |

**Example call**
```json
{
  "origins": ["3.1390,101.6869"],
  "destinations": ["Klinik Haiwan A", "Klinik Haiwan B", "Klinik Haiwan C"],
  "travel_mode": "drive"
}
```

**Output** — returns a matrix of distances and durations for every origin-destination pair.

**Recommended use:** After `maps_search_places` returns multiple clinics, pass them all into `maps_distance_matrix` to find the closest one and rank the results before presenting to the user.

---

### 6. `maps_elevation`
Get elevation data for one or more locations. Not relevant for this project — can be ignored.

---

## Recommended Agent Tool Call Sequence

For the cat health diagnosis flow, the agent should chain these tools like this:

```
1. maps_search_places(query="vet clinic", location={lat, lng}, radius=5000)
   → returns list of nearby clinics with place_ids

2. maps_distance_matrix(origins=[user_lat_lng], destinations=[clinic names], travel_mode="drive")
   → ranks clinics by distance

3. maps_place_details(place_id="<chosen clinic>")
   → gets phone number and opening hours to show user
   
4. maps_directions(origin=user_lat_lng, destination="<chosen clinic>", travel_mode="drive")
   → shows how to get there (optional, only if user confirms they want to go)
```

---

## What the Flutter App Must Send

The agent cannot use `maps_search_places` without the user's location. The Flutter app must include the user's GPS coordinates in every request to the agent:

```json
{
  "user_location": {
    "lat": 3.1390,
    "lng": 101.6869
  }
}
```

Make sure this is agreed on with the Flutter teammate early.

---

## LangChain MCP Config

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "google_maps": {
        "command": "npx",
        "args": ["mcp-server-google-maps"],
        "transport": "stdio",
        "env": {
            "GOOGLE_MAPS_API_KEY": "your_actual_key_here"
        }
    }
})
```

---

## Combined Config (Both MCP Servers Together)

```python
client = MultiServerMCPClient({
    "google_maps": {
        "command": "npx",
        "args": ["mcp-server-google-maps"],
        "transport": "stdio",
        "env": {
            "GOOGLE_MAPS_API_KEY": "your_actual_key_here"
        }
    },
    "wikipedia": {
        "command": "/absolute/path/to/wikipedia-mcp/venv/bin/wikipedia-mcp",
        "args": [],
        "transport": "stdio",
    }
})
```
