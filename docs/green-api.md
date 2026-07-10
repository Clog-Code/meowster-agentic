# Green API (WhatsApp) — Integration Spec

Send WhatsApp notifications to a vet clinic via [Green API](https://green-api.com).

**Requires:** `requests`, `python-dotenv` (already in `pyproject.toml` dependencies).

## Environment Variables

Create a `.env` file in the project root:

```
GREEN_API_INSTANCE_ID=your_instance_id
GREEN_API_TOKEN=your_token
RECIPIENT_NUMBER=your_number_with_country_code_no_spaces
```

## Module: `examples/greenapi.py`

A small helper module wrapping the Green API WhatsApp endpoints.

| Function | Description |
|---|---|
| `send_whatsapp(phone_number, message)` | Send a WhatsApp message to the configured `RECIPIENT_NUMBER`. |
| `check_whatsapp(phone_number)` | Verify whether a phone number is registered on WhatsApp. |
| `format_vet_message(clinic_name, phone_number, message)` | Format a cat health alert message for a vet clinic. |

All functions read credentials from the environment (via `load_dotenv`) and return the parsed JSON response from the Green API.

## LangChain Tool Integration

Wrap the functions as tools in a LangChain agent:

```python
import requests
from langchain.tools import tool

BASE_URL = "http://localhost:8001"

@tool
def check_whatsapp(phone_number: str) -> str:
    """Check if a phone number is registered on WhatsApp before messaging them.
    Phone number must include country code with no spaces or dashes e.g. 601158606808."""
    response = requests.post(f"{BASE_URL}/check-whatsapp", json={"phone_number": phone_number})
    result = response.json()
    if result["is_on_whatsapp"]:
        return f"{phone_number} is on WhatsApp. Safe to send message."
    return f"{phone_number} is NOT on WhatsApp. Consider calling instead."

@tool
def contact_vet(clinic_name: str, phone_number: str, message: str) -> str:
    """Send a WhatsApp message to a vet clinic when the cat needs medical attention."""
    response = requests.post(f"{BASE_URL}/contact-vet", json={
        "clinic_name": clinic_name,
        "phone_number": phone_number,
        "message": message,
    })
    result = response.json()
    return f"Message sent to {result['clinic_name']}. {result['demo_note']}"
```

## Notes

- On the free Developer plan, messages can only be sent to your verified number.
- The `phone_number` in `send_whatsapp`/`contact_vet` is for display; the actual message goes to `RECIPIENT_NUMBER`.
