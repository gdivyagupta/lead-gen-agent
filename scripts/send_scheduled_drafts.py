#!/usr/bin/env python3
"""Sends every sheet row still in `draft_created` status by sending the
Gmail draft as-is (preserving any manual edits made in the Gmail UI),
then flips that row's status to `sent` with a timestamp.

Meant to be invoked once, at a scheduled time, by a detached local
process (see the wrapper that launches this with a computed delay) —
requires the OAuth token to already have the gmail.send scope
(scripts/setup_google_auth.py --allow-send).
"""
from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from leadgen import config, google_auth, sheets_store, gmail_sender  # noqa: E402
from leadgen.models import Lead, EmailDraft, SheetRow  # noqa: E402


def main() -> int:
    settings = config.load_settings()
    creds = google_auth.load_credentials(
        settings, scopes=google_auth.DEFAULT_SCOPES + [google_auth.SEND_SCOPE]
    )

    rows = sheets_store.get_all_rows(creds, settings.google_sheet_id)
    sent, failed = 0, []
    for i, r in enumerate(rows, start=2):
        r = r + [""] * (12 - len(r))
        timestamp, profile_name, full_name, title, company, email, linkedin_url, \
            subject, body, status, draft_id, sent_at = r[:12]

        if status != "draft_created" or not draft_id:
            continue

        try:
            gmail_sender.send_draft(creds, draft_id)
            lead = Lead(
                full_name=full_name, title=title, company=company,
                email=email, linkedin_url=linkedin_url, profile_name=profile_name,
            )
            draft = EmailDraft(subject=subject, body=body, body_html="")
            new_row = SheetRow(
                lead=lead, email_draft=draft, status="sent",
                gmail_draft_id=draft_id,
                sent_at=datetime.now(timezone.utc).isoformat(),
                timestamp=timestamp,
            )
            sheets_store.update_row(creds, settings.google_sheet_id, i, new_row)
            sent += 1
            print(f"row {i}: sent draft {draft_id} for {email}")
        except Exception as e:
            failed.append((email, str(e)))
            print(f"row {i}: FAILED for {email}: {e}")
        time.sleep(0.3)

    print(f"\nDone. {sent} sent, {len(failed)} failed.")
    for email, err in failed:
        print(" -", email, err)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
