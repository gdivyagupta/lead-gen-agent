#!/usr/bin/env python3
"""One-time OAuth authorization for Google Sheets + Gmail.

Requires config/google_oauth_client_secret.json (a Desktop-app OAuth
client downloaded from Google Cloud Console, with the Sheets API and
Gmail API enabled on that project). Opens a browser, asks you to approve
access, and writes config/google_token.json — gitignored, never commit it.

By default this requests read/append on Sheets and gmail.compose
(drafts only). Pass --allow-send if you also want the pipeline able to
send mail directly, not just create drafts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen.config import load_settings  # noqa: E402
from leadgen.google_auth import DEFAULT_SCOPES, SEND_SCOPE  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-send",
        action="store_true",
        help="Also request the gmail.send scope.",
    )
    args = parser.parse_args()

    settings = load_settings()
    secret_file = settings.google_oauth_client_secret_file
    if not secret_file or not secret_file.exists():
        print(
            f"Missing OAuth client secret file at {secret_file}. "
            "Download it from Google Cloud Console (OAuth client, type "
            "'Desktop app') first.",
            file=sys.stderr,
        )
        return 1

    scopes = list(DEFAULT_SCOPES)
    if args.allow_send:
        scopes.append(SEND_SCOPE)

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), scopes)
    creds = flow.run_local_server(port=0)

    token_file = settings.google_token_file
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(creds.to_json())
    print(f"Saved token to {token_file}. Scopes granted: {scopes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
