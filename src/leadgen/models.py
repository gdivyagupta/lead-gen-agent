from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Lead:
    full_name: str
    title: str
    company: str
    email: str
    linkedin_url: str = ""
    profile_name: str = ""
    raw: dict = field(default_factory=dict)

    def is_usable(self) -> bool:
        return bool(self.email and self.full_name)


@dataclass
class EmailDraft:
    subject: str
    body: str
    body_html: str


@dataclass
class SheetRow:
    lead: Lead
    email_draft: EmailDraft | None
    status: str
    gmail_draft_id: str = ""
    sent_at: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def as_row(self) -> list[str]:
        return [
            self.timestamp,
            self.lead.profile_name,
            self.lead.full_name,
            self.lead.title,
            self.lead.company,
            self.lead.email,
            self.lead.linkedin_url,
            self.email_draft.subject if self.email_draft else "",
            self.email_draft.body if self.email_draft else "",
            self.status,
            self.gmail_draft_id,
            self.sent_at,
        ]


SHEET_HEADER = [
    "timestamp",
    "profile",
    "full_name",
    "title",
    "company",
    "email",
    "linkedin_url",
    "email_subject",
    "email_body",
    "status",
    "gmail_draft_id",
    "sent_at",
]
