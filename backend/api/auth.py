"""
Auth routes — Google OAuth 2.0 for per-user calendar access.

Prefix: /auth
  GET  /auth/google            Initiate OAuth login for a thread
  GET  /auth/google/callback   OAuth callback — stores tokens
  GET  /auth/me                List connected providers for a thread
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from ..services import get_oauth_token, store_oauth_token

router = APIRouter(prefix="/auth")

_OAUTH_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


@router.get("/google")
def auth_google(thread_id: str = Query(...)):
    """
    Redirect the user to Google's OAuth consent screen to grant calendar
    read access for the given conversation thread.

    After consent, Google redirects to /auth/google/callback which stores
    the tokens linked to this thread_id.
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
    if not client_id or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_REDIRECT_URI must be set.",
        )

    params = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": _OAUTH_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
            "state": thread_id,
        }
    )
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
def auth_google_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """
    Google OAuth callback: exchange the authorization code for tokens and
    store them linked to the thread_id (carried in `state`).
    """
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth env vars not configured.",
        )

    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    if not resp.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Token exchange failed: {resp.text}",
        )

    token_data = resp.json()

    user_email = None
    try:
        info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
            timeout=10,
        )
        if info.ok:
            user_email = info.json().get("email")
    except Exception:
        pass

    store_oauth_token(
        thread_id=state,
        provider="google",
        token_data={
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token", ""),
            "scope": token_data.get("scope", _OAUTH_SCOPE),
            "expiry": str(
                datetime.now(UTC)
                + timedelta(seconds=token_data.get("expires_in", 3600))
            ),
            "user_email": user_email,
        },
    )

    return HTMLResponse(
        content=f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Calendar connected</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; display: flex;
           justify-content: center; align-items: center;
           min-height: 100vh; margin: 0; background: #0f1115; color: #e6e8ec; }}
    .card {{ text-align: center; padding: 32px; }}
    .ok {{ color: #4caf50; font-size: 2rem; }}
    .email {{ color: #9aa1ac; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="card">
    <p class="ok">&#10003; Calendar connected</p>
    <p class="email">{user_email or ""}</p>
    <p>You can close this tab now.</p>
  </div>
  <script>
    if (window.opener) {{
      window.opener.postMessage({{ type: "oauth-connected", provider: "google" }}, "*");
    }}
  </script>
</body>
</html>""",
        media_type="text/html",
    )


@router.get("/me")
def auth_me(thread_id: str = Query(...)):
    """List connected OAuth providers for a given conversation thread."""
    token = get_oauth_token(thread_id, "google")
    if token is None:
        return {"thread_id": thread_id, "providers": []}

    return {
        "thread_id": thread_id,
        "providers": [
            {
                "provider": "google",
                "scope": token.get("scope"),
                "user_email": token.get("user_email"),
            }
        ],
    }
