from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


def _gmail_service(creds: Credentials):
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_message(
    sender: str, to: str, subject: str, body: str, body_html: str
) -> dict:
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))
    message.attach(MIMEText(body_html, "html"))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {"raw": raw}


def create_draft(
    creds: Credentials, sender: str, to: str, subject: str, body: str, body_html: str
) -> str:
    service = _gmail_service(creds)
    draft = (
        service.users()
        .drafts()
        .create(
            userId="me",
            body={"message": _build_message(sender, to, subject, body, body_html)},
        )
        .execute()
    )
    logger.info("Created Gmail draft %s for %s", draft["id"], to)
    return draft["id"]


def delete_draft(creds: Credentials, draft_id: str) -> None:
    service = _gmail_service(creds)
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    logger.info("Deleted Gmail draft %s", draft_id)


def send_draft(creds: Credentials, draft_id: str) -> str:
    """Sends a draft exactly as it currently sits in Gmail (including any
    manual edits made in the Gmail UI after it was created), rather than
    reconstructing the message — see hitl.require_send_confirmation, this
    performs no approval check itself.
    """
    service = _gmail_service(creds)
    sent = (
        service.users()
        .drafts()
        .send(userId="me", body={"id": draft_id})
        .execute()
    )
    logger.info("Sent draft %s as message %s", draft_id, sent["id"])
    return sent["id"]


def send_email(
    creds: Credentials, sender: str, to: str, subject: str, body: str, body_html: str
) -> str:
    """Only ever called when the caller has passed --send explicitly —
    see hitl.require_send_confirmation. This function itself performs no
    approval check; it trusts the pipeline to have already gated it.
    """
    service = _gmail_service(creds)
    sent = (
        service.users()
        .messages()
        .send(userId="me", body=_build_message(sender, to, subject, body, body_html))
        .execute()
    )
    logger.info("Sent email %s to %s", sent["id"], to)
    return sent["id"]
