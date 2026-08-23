from __future__ import annotations

import json
import logging
import re

from google import genai

from .config import ClientProfile, Settings
from .models import EmailDraft, Lead

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """You are writing a single cold outreach email on behalf \
of {sender_name}.

About the sender's offer:
- Value proposition: {value_prop}
- Desired call to action: {cta}
- Tone: {tone}

About the recipient (a real lead — get specifics right, don't invent facts \
not given here):
- Name: {full_name}
- Title: {title}
- Company: {company}

Write a short, personalized cold email. Rules:
- Reference the recipient's actual role/company naturally, don't force it.
- No generic filler ("I hope this email finds you well", "I came across \
your profile"). No exclamation points. No emojis.
- Under 120 words in the body.
- End with the call to action, phrased as a low-friction ask.
- Output ONLY minified JSON, no markdown fences, no commentary, matching \
exactly this shape: {{"subject": "...", "body": "..."}}
"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Gemini response did not contain JSON: {text!r}")
    return json.loads(match.group(0))


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
    )
    data = _extract_json(response.text)
    return EmailDraft(subject=data["subject"].strip(), body=data["body"].strip())
