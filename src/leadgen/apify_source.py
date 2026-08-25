from __future__ import annotations

import logging

from apify_client import ApifyClient

from .config import ClientProfile, Settings
from .models import Lead

logger = logging.getLogger(__name__)

# Field names verified against the default actor (microworlds/leads-finder)
# by fetching its live input/output schema from the Apify API, plus a few
# common variants seen on other popular lead-scraper actors in case a
# profile is pointed at a different one.
_NAME_KEYS = ["full_name", "fullName", "name"]
_FIRST_NAME_KEYS = ["first_name", "firstName"]
_LAST_NAME_KEYS = ["last_name", "lastName"]
_TITLE_KEYS = ["title", "headline", "job_title", "jobTitle", "position"]
_COMPANY_KEYS = ["company", "organization_name", "organizationName", "company_name"]
_EMAIL_KEYS = ["email", "email_address", "emailAddress"]
_LINKEDIN_KEYS = ["linkedin_url", "linkedinUrl", "linkedin"]


def _first(d: dict, keys: list[str]) -> str:
    for k in keys:
        v = d.get(k)
        if v:
            return str(v)
    return ""


def _full_name(item: dict) -> str:
    direct = _first(item, _NAME_KEYS)
    if direct:
        return direct
    first, last = _first(item, _FIRST_NAME_KEYS), _first(item, _LAST_NAME_KEYS)
    return f"{first} {last}".strip()


def _normalize(item: dict, profile_name: str) -> Lead:
    return Lead(
        full_name=_full_name(item),
        title=_first(item, _TITLE_KEYS),
        company=_first(item, _COMPANY_KEYS),
        email=_first(item, _EMAIL_KEYS),
        linkedin_url=_first(item, _LINKEDIN_KEYS),
        profile_name=profile_name,
        raw=item,
    )


def fetch_leads(settings: Settings, profile: ClientProfile, max_results: int) -> list[Lead]:
    """Runs the profile's Apify actor and returns normalized, usable leads.

    Actors vary in the exact input schema they expect; `search_input` from
    the profile YAML is passed through mostly as-is, with a result-count
    cap merged in under the couple of key names actors commonly use for it.
    """
    if not settings.apify_api_token:
        raise RuntimeError("APIFY_API_TOKEN is not set (see .env.example).")

    actor_id = profile.apify_actor_id or settings.apify_actor_id_default
    if not actor_id:
        raise RuntimeError(
            f"No Apify actor configured for profile '{profile.name}' and no "
            "APIFY_ACTOR_ID default is set."
        )

    run_input = dict(profile.apify_search_input)
    # "max_result" is this actor's real cap field (verified against its
    # input schema); the other two are included for compatibility if a
    # profile is pointed at a different actor that uses those names
    # instead. Extra unrecognized fields are harmless — Apify actors
    # ignore input keys they don't define.
    run_input.setdefault("max_result", max_results)
    run_input.setdefault("maxItems", max_results)
    run_input.setdefault("totalRecordsCount", max_results)

    client = ApifyClient(settings.apify_api_token)
    logger.info("Running Apify actor %s for profile %s", actor_id, profile.name)
    run = client.actor(actor_id).call(run_input=run_input)

    dataset_id = run["defaultDatasetId"]
    items = list(client.dataset(dataset_id).iterate_items())

    leads = [_normalize(item, profile.name) for item in items[:max_results]]
    usable = [l for l in leads if l.is_usable()]
    logger.info(
        "Apify returned %d items, %d usable (had name + email)",
        len(leads),
        len(usable),
    )
    return usable
