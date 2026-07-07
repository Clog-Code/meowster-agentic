"""
Outbound email tool — STUB.

TODO(you): wire this up to a real SMTP relay or transactional email API
(SMTP_HOST / SMTP_PORT / SMTP_USERNAME / SMTP_PASSWORD / SMTP_FROM_ADDRESS
in .env), e.g. smtplib, SendGrid, Postmark, or AWS SES.

Until then, `send_email` logs the intended message and returns a mocked
confirmation.
"""

import os
import uuid
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import tool


@tool
def send_email(
    to_address: str,
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> dict[str, Any]:
    """
    Send an email, e.g. an appointment request to a vet clinic or an order
    confirmation summary to the user.

    Args:
        to_address: Recipient email address.
        subject: Email subject line.
        body: Plain-text or simple HTML email body.
        cc: Optional list of additional recipients.

    Returns:
        A send record. Until a real provider is wired in (see TODO in
        email_tool.py), `status` will always be 'stubbed' and no email is
        actually sent.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    from_address = os.getenv("SMTP_FROM_ADDRESS")

    if not (smtp_host and smtp_username and smtp_password and from_address):
        return {
            "email_id": f"stub-{uuid.uuid4().hex[:8]}",
            "status": "stubbed",
            "to_address": to_address,
            "cc": cc or [],
            "subject": subject,
            "body_preview": body[:200],
            "timestamp": datetime.now(UTC).isoformat(),
            "note": (
                "SMTP not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, "
                "SMTP_PASSWORD, and SMTP_FROM_ADDRESS in .env, then implement "
                "the real send in email_tool.py."
            ),
        }

    # ------------------------------------------------------------------
    # TODO(you): real implementation, e.g.:
    #
    #   import smtplib
    #   from email.mime.text import MIMEText
    #   msg = MIMEText(body)
    #   msg["Subject"] = subject
    #   msg["From"] = from_address
    #   msg["To"] = to_address
    #   with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as server:
    #       server.starttls()
    #       server.login(smtp_username, smtp_password)
    #       server.sendmail(from_address, [to_address, *(cc or [])], msg.as_string())
    # ------------------------------------------------------------------
    raise NotImplementedError("Real email integration not yet implemented.")


COMMUNICATION_EMAIL_TOOLS = [send_email]
