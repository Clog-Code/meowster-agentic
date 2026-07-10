"""Unit tests for the Green API WhatsApp helper (no network needed)."""

import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "examples"))

os.environ["GREEN_API_INSTANCE_ID"] = "12345"
os.environ["GREEN_API_TOKEN"] = "secret-token"
os.environ["RECIPIENT_NUMBER"] = "601158606808"

# pylint: disable-next=wrong-import-position
import greenapi as mod


def test_base_url_format():
    """BASE_URL should embed the configured instance id."""
    assert mod.BASE_URL == "https://api.green-api.com/waInstance12345"


def test_send_whatsapp():
    """send_whatsapp should POST to the sendMessage endpoint with the chatId."""
    fake = mock.Mock()
    fake.raise_for_status.return_value = None
    fake.json.return_value = {"idMessage": "abc"}
    with mock.patch.object(mod.requests, "post", return_value=fake) as post:
        result = mod.send_whatsapp("601158606808", "hello")
    post.assert_called_once()
    args, kwargs = post.call_args
    assert (
        args[0] == "https://api.green-api.com/waInstance12345/sendMessage/secret-token"
    )
    assert kwargs["json"]["chatId"] == "601158606808@c.us"
    assert kwargs["json"]["message"] == "hello"
    assert result == {"idMessage": "abc"}


def test_check_whatsapp():
    """check_whatsapp should POST to the checkWhatsapp endpoint with the phone number."""
    fake = mock.Mock()
    fake.raise_for_status.return_value = None
    fake.json.return_value = {"existsWhatsapp": True}
    with mock.patch.object(mod.requests, "post", return_value=fake) as post:
        result = mod.check_whatsapp("601158606808")
    args, kwargs = post.call_args
    assert (
        args[0]
        == "https://api.green-api.com/waInstance12345/checkWhatsapp/secret-token"
    )
    assert kwargs["json"]["phoneNumber"] == "601158606808"
    assert result == {"existsWhatsapp": True}


def test_format_vet_message():
    """format_vet_message should embed the clinic, phone and message."""
    msg = mod.format_vet_message(
        "Living Hope Animal Clinic", "013-297 3396", "My cat is distressed."
    )
    assert "Living Hope Animal Clinic" in msg
    assert "013-297 3396" in msg
    assert "My cat is distressed." in msg
    assert "MeowDoc" in msg
