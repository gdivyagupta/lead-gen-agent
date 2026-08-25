from __future__ import annotations

import logging

from . import apify_source, email_writer, gmail_sender, google_auth, sheets_store
from .config import Settings, get_active_profile
from .hitl import (
    require_profile_confirmation,
    require_send_confirmation,
    require_spend_approval,
)
from .models import SheetRow

logger = logging.getLogger(__name__)


def run(
    settings: Settings,
    confirm_profile: str | None,
    limit: int,
    approve_spend: int | None,
    send: bool,
) -> list[SheetRow]:
    profile = get_active_profile()
    require_profile_confirmation(profile, confirm_profile)

    requested = min(limit, limit)  # explicit: the CLI --limit is the ask
    allowed = require_spend_approval(requested, profile.max_free_results, approve_spend)
    status = require_send_confirmation(send)

    creds = google_auth.load_credentials(
        settings,
        scopes=google_auth.DEFAULT_SCOPES
        + ([google_auth.SEND_SCOPE] if send else []),
    )
    sheets_store.ensure_header(creds, settings.google_sheet_id)
    already_contacted = sheets_store.get_existing_emails(creds, settings.google_sheet_id)

    leads = apify_source.fetch_leads(settings, profile, allowed)
    new_leads = [l for l in leads if l.email.lower() not in already_contacted]
    skipped = len(leads) - len(new_leads)
    if skipped:
        logger.info("Skipping %d leads already present in the sheet", skipped)

    rows: list[SheetRow] = []
    for lead in new_leads:
        try:
            draft = email_writer.write_outreach_email(settings, profile, lead)
        except Exception:
            logger.exception("Failed to generate email for %s, skipping", lead.email)
            continue

        gmail_draft_id = ""
        sent_at = ""
        try:
            if send:
                gmail_sender.send_email(
                    creds,
                    settings.gmail_sender_address,
                    lead.email,
                    draft.subject,
                    draft.body,
                    draft.body_html,
                )
                from datetime import datetime, timezone

                sent_at = datetime.now(timezone.utc).isoformat()
            else:
                gmail_draft_id = gmail_sender.create_draft(
                    creds,
                    settings.gmail_sender_address,
                    lead.email,
                    draft.subject,
                    draft.body,
                    draft.body_html,
                )
        except Exception:
            logger.exception("Gmail step failed for %s, logging without it", lead.email)
            status = "generated_gmail_failed"

        rows.append(
            SheetRow(
                lead=lead,
                email_draft=draft,
                status=status,
                gmail_draft_id=gmail_draft_id,
                sent_at=sent_at,
            )
        )

    sheets_store.append_rows(creds, settings.google_sheet_id, rows)
    logger.info(
        "Pipeline complete: %d new leads processed, %d skipped as duplicates",
        len(rows),
        skipped,
    )
    return rows
