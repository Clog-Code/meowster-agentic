"""Tests for the Green API-backed WhatsApp communication tool.

Unit tests run hermetically (requests.post is mocked). Live integration tests
that send a real WhatsApp message via the configured Green API instance run
automatically whenever Green API is configured (.env present); they are skipped
otherwise so the suite stays CI-safe without credentials.
"""

import os
from unittest import mock

import pytest
from dotenv import load_dotenv


import agent.tools.communication.whatsapp_tool as wa

load_dotenv()
REAL_CONFIGURED = bool(
    os.getenv("GREEN_API_INSTANCE_ID")
    and os.getenv("GREEN_API_TOKEN")
    and os.getenv("RECIPIENT_NUMBER")
)


def test_send_stubbed_when_not_configured(monkeypatch):
    """Without Green API env vars, the tool returns a stubbed confirmation."""
    monkeypatch.delenv("GREEN_API_INSTANCE_ID", raising=False)
    result = wa.send_whatsapp_message.invoke(
        {"to_number": "+60123456789", "message": "hello"}
    )
    assert result["status"] == "stubbed"
    assert result["to_number"] == "+60123456789"


def test_send_whatsapp_success(monkeypatch):
    """A configured send posts to the Green API sendMessage endpoint."""
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "12345")
    monkeypatch.setenv("GREEN_API_TOKEN", "secret-token")
    monkeypatch.setenv("RECIPIENT_NUMBER", "601158606808")
    fake = mock.Mock()
    fake.json.return_value = {"idMessage": "abc"}
    with mock.patch.object(wa.requests, "post", return_value=fake) as post:
        result = wa.send_whatsapp_message.invoke(
            {"to_number": "+60123456789", "message": "hello"}
        )
    args, kwargs = post.call_args
    assert (
        args[0] == "https://api.green-api.com/waInstance12345/sendMessage/secret-token"
    )
    assert kwargs["json"]["chatId"] == "601158606808@c.us"
    assert result["status"] == "sent"
    assert result["message_id"] == "abc"
    assert result["recipient"] == "601158606808"


def test_send_whatsapp_green_api_error(monkeypatch):
    """A Green API error response is surfaced with status 'error'."""
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "12345")
    monkeypatch.setenv("GREEN_API_TOKEN", "secret-token")
    monkeypatch.setenv("RECIPIENT_NUMBER", "601158606808")
    fake = mock.Mock()
    fake.json.return_value = {"error": True, "message": "instance not authorized"}
    with mock.patch.object(wa.requests, "post", return_value=fake):
        result = wa.send_whatsapp_message.invoke(
            {"to_number": "+60123456789", "message": "hello"}
        )
    assert result["status"] == "error"
    assert "not authorized" in result["error"]


def test_check_whatsapp_success(monkeypatch):
    """check_whatsapp_number posts to the Green API checkWhatsapp endpoint."""
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "12345")
    monkeypatch.setenv("GREEN_API_TOKEN", "secret-token")
    monkeypatch.setenv("RECIPIENT_NUMBER", "601158606808")
    fake = mock.Mock()
    fake.json.return_value = {"existsWhatsapp": True}
    with mock.patch.object(wa.requests, "post", return_value=fake) as post:
        result = wa.check_whatsapp_number.invoke({"phone_number": "+60123456789"})
    args, kwargs = post.call_args
    assert (
        args[0]
        == "https://api.green-api.com/waInstance12345/checkWhatsapp/secret-token"
    )
    assert kwargs["json"]["phoneNumber"] == "60123456789"
    assert result["is_on_whatsapp"] is True


def test_check_whatsapp_stubbed_when_not_configured(monkeypatch):
    """Without Green API env vars, check returns a stubbed 'unknown' result."""
    monkeypatch.delenv("GREEN_API_TOKEN", raising=False)
    result = wa.check_whatsapp_number.invoke({"phone_number": "+60123456789"})
    assert result["status"] == "stubbed"
    assert result["is_on_whatsapp"] is False


@pytest.mark.skipif(
    not REAL_CONFIGURED,
    reason="Green API not configured (.env missing); live tests skipped",
)
def test_send_whatsapp_real(monkeypatch):
    """Live test: actually send a WhatsApp message via the configured instance."""
    load_dotenv(override=True)
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", os.getenv("GREEN_API_INSTANCE_ID", ""))
    monkeypatch.setenv("GREEN_API_TOKEN", os.getenv("GREEN_API_TOKEN", ""))
    monkeypatch.setenv("RECIPIENT_NUMBER", os.getenv("RECIPIENT_NUMBER", ""))
    result = wa.send_whatsapp_message.invoke(
        {
            "to_number": os.getenv("RECIPIENT_NUMBER", ""),
            "message": "MeowDoc integration test (live)",
        }
    )
    assert result["status"] == "sent", result
    assert result.get("message_id")


@pytest.mark.skipif(
    not REAL_CONFIGURED,
    reason="Green API not configured (.env missing); live tests skipped",
)
def test_check_whatsapp_real(monkeypatch):
    """Live test: verify a real phone number against the configured instance."""
    load_dotenv(override=True)
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", os.getenv("GREEN_API_INSTANCE_ID", ""))
    monkeypatch.setenv("GREEN_API_TOKEN", os.getenv("GREEN_API_TOKEN", ""))
    monkeypatch.setenv("RECIPIENT_NUMBER", os.getenv("RECIPIENT_NUMBER", ""))
    result = wa.check_whatsapp_number.invoke(
        {"phone_number": os.getenv("RECIPIENT_NUMBER", "")}
    )
    assert result["status"] == "ok", result
    assert result["is_on_whatsapp"] is True
