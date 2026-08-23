from __future__ import annotations

import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .models import SHEET_HEADER, SheetRow

logger = logging.getLogger(__name__)

_RANGE_ALL = "A:A"
_APPEND_RANGE = "A1"


def _sheets_service(creds: Credentials):
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def ensure_header(creds: Credentials, sheet_id: str) -> None:
    service = _sheets_service(creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range="1:1")
        .execute()
    )
    existing = result.get("values", [[]])
    if existing and existing[0]:
        return
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=_APPEND_RANGE,
        valueInputOption="RAW",
        body={"values": [SHEET_HEADER]},
    ).execute()


def get_existing_emails(creds: Credentials, sheet_id: str) -> set[str]:
    """Used to dedupe: never generate/send a second email to the same
    address the sheet already has a row for.
    """
    service = _sheets_service(creds)
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range="F:F")  # column F = email
        .execute()
    )
    values = result.get("values", [])
    return {row[0].strip().lower() for row in values[1:] if row}


def append_rows(creds: Credentials, sheet_id: str, rows: list[SheetRow]) -> None:
    if not rows:
        return
    service = _sheets_service(creds)
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=_APPEND_RANGE,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [r.as_row() for r in rows]},
    ).execute()
    logger.info("Appended %d rows to sheet %s", len(rows), sheet_id)
