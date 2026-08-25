from __future__ import annotations

import html
import json
import logging
import re

from google import genai
from google.genai import types

from .config import ClientProfile, Settings
from .models import EmailDraft, Lead

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are writing the body paragraphs of a cold outreach \
email on behalf of {sender_name}.

About the sender's offer:
- Value proposition: {value_prop}
- Desired call to action: {cta}
- Tone: {tone}

About the recipient (a real lead — get specifics right, don't invent facts \
not given here):
- Name: {full_name}
- Title: {title}
- Company: {company}

Write the body of a short, personalized cold email as exactly 3 \
paragraphs:
1. ONE direct sentence naming the specific pain point at their company. \
Address them as "you", not "many companies like X" or "most businesses" \
— no throat-clearing lead-in, go straight to the pain.
2. 1-2 sentences on how the offer solves it. Do not fold the call to \
action into this paragraph.
3. Only the call to action, phrased as a single low-friction question. \
Nothing else in this paragraph.

Rules:
- Do NOT include a greeting/salutation (e.g. no "Hi Name") — it is added \
separately.
- Do NOT include a sign-off (e.g. no "Best," or the sender's name) — it is \
added separately.
- Do NOT mention or link a scheduling/calendar link — it is added \
separately.
- Reference the recipient's actual role/company naturally, don't force it.
- No generic filler ("I hope this email finds you well", "I came across \
your profile", "many firms like X"). No exclamation points. No emojis.
- Combined, under 100 words.
- Output ONLY minified JSON, no markdown fences, no commentary, matching \
exactly this shape: {{"subject": "...", "paragraphs": ["...", "...", "..."]}}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Gemini response did not contain JSON: {text!r}")
    return json.loads(match.group(0))


def _titlecase_subject(subject: str) -> str:
    """Capitalizes the first letter of every word, leaving the rest of each
    word untouched (so acronyms like "HVAC" or contractions like "it's"
    don't get mangled the way str.title() would mangle them).
    """
    return " ".join(w[:1].upper() + w[1:] if w else w for w in subject.split(" "))


def render_body(
    first_name: str, paragraphs: list[str], sender_name: str, calendar_url: str
) -> tuple[str, str]:
    """Builds the final email body deterministically around the AI-written
    paragraphs, so spacing, the greeting, and the calendar hyperlink are
    always exactly right regardless of what the model returns.
    """
    plain_lines = [f"{first_name},", ""]
    for p in paragraphs:
        plain_lines.append(p)
        plain_lines.append("")
    plain_lines.append(f"Book a Slot: My Calendar ({calendar_url})")
    plain_lines.append("")
    plain_lines.append("Best,")
    plain_lines.append(sender_name)
    plain = "\n".join(plain_lines)

    html_parts = [f"<p>{html.escape(first_name)},</p>"]
    for p in paragraphs:
        html_parts.append(f"<p>{html.escape(p)}</p>")
    html_parts.append(
        f'<p>Book a Slot: <a href="{html.escape(calendar_url)}">My Calendar</a></p>'
    )
    html_parts.append(f"<p>Best,<br>{html.escape(sender_name)}</p>")
    body_html = "\n".join(html_parts)

    return plain, body_html


def write_outreach_email(
    settings: Settings, profile: ClientProfile, lead: Lead
) -> EmailDraft:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (see .env.example).")

    prompt = _PROMPT_TEMPLATE.format(
        sender_name=profile.sender_name or "the sender",
        value_prop=profile.value_prop,
        cta=profile.cta,
        tone=profile.tone,
        full_name=lead.full_name,
        title=lead.title,
        company=lead.company,
    )

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        # Writing a couple of templated cold-email paragraphs needs no deep
        # reasoning. Gemini 3.1 Pro defaults to "high" thinking (thousands
        # of hidden tokens billed as output) unless told otherwise, so pin
        # this low to keep per-email cost close to the visible output size.
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
        ),
    )
    data = _extract_json(response.text)
    subject = _titlecase_subject(data["subject"].strip())
    paragraphs = [p.strip() for p in data["paragraphs"] if p and p.strip()]
    first_name = (lead.full_name.split() or [lead.full_name])[0]
    body, body_html = render_body(
        first_name, paragraphs, profile.sender_name, settings.calendar_url
    )
    return EmailDraft(subject=subject, body=body, body_html=body_html)
