"""Example helper module for sending WhatsApp messages via Green API."""

# Install:
# pip install deepagents python-dotenv requests

import os

import requests
from dotenv import load_dotenv

load_dotenv()

INSTANCE_ID = os.getenv("GREEN_API_INSTANCE_ID")
TOKEN = os.getenv("GREEN_API_TOKEN")
RECIPIENT = os.getenv("RECIPIENT_NUMBER")

BASE_URL = f"https://api.green-api.com/waInstance{INSTANCE_ID}"


def send_whatsapp(phone_number: str, message: str) -> dict:
    """Send a WhatsApp message to the given phone number (falls back to RECIPIENT_NUMBER)."""
    chat_id = f"{phone_number or RECIPIENT}@c.us"
    url = f"{BASE_URL}/sendMessage/{TOKEN}"
    payload = {
        "chatId": chat_id,
        "message": message,
    }
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def check_whatsapp(phone_number: str) -> dict:
    """Verify whether a phone number is registered on WhatsApp."""
    url = f"{BASE_URL}/checkWhatsapp/{TOKEN}"
    payload = {"phoneNumber": phone_number}
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def format_vet_message(clinic_name: str, phone_number: str, message: str) -> str:
    """Format a cat health alert message for a vet clinic."""
    return f"""
🐱 *Cat Health Alert — MeowDoc*

*Clinic:* {clinic_name}
*Contact:* {phone_number}

{message}

_This message was sent automatically by MeowDoc Cat Health AI._
    """.strip()
