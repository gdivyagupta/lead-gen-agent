from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def _gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_message(sender: str, to: str, subject: str, body: str) -> dict:
    message = MIMEText(body)
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def create_draft(creds: Credentials, sender: str, to: str, subject: str, body: str) -> str:
    service = _gmail_service(creds)
    draft = (
        service.users()
        .drafts()
        .create(userId="me", body={"message": _build_message(sender, to, subject, body)})
        .execute()
    )
    logger.info("Created Gmail draft %s for %s", draft["id"], to)
    return draft["id"]


def send_email(creds: Credentials, sender: str, to: str, subject: str, body: str) -> str:
    """Only ever called when the caller has passed --send explicitly —
    see hitl.require_send_confirmation. This function itself performs no
    approval check; it trusts the pipeline to have already gated it.
    """
    service = _gmail_service(creds)
    sent = (
        service.users()
        .messages()
        .send(userId="me", body=_build_message(sender, to, subject, body))
        .execute()
    )
    logger.info("Sent email %s to %s", sent["id"], to)
    return sent["id"]
