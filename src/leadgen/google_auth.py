from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .config import Settings

# gmail.send is intentionally not requested by default. If you need it,
# delete config/google_token.json and re-run scripts/setup_google_auth.py
# with --allow-send once you've decided you actually want the pipeline
# able to send mail, not just draft it.
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.compose",
]

SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


def load_credentials(settings: Settings, scopes: list[str] | None = None) -> Credentials:
    token_file: Path = settings.google_token_file
    if not token_file or not token_file.exists():
        raise RuntimeError(
            "No Google OAuth token found. Run "
            "`python scripts/setup_google_auth.py` once to authorize this "
            "app against your Google account."
        )
    creds = Credentials.from_authorized_user_file(str(token_file), scopes or DEFAULT_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())
    return creds
