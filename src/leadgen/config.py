from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class ClientProfile:
    name: str
    status: str
    description: str
    apify_actor_id: str
    apify_search_input: dict
    max_free_results: int
    sender_name: str
    value_prop: str
    cta: str
    tone: str

    @classmethod
    def from_dict(cls, d: dict) -> "ClientProfile":
        apify = d.get("apify", {})
        email = d.get("email", {})
        return cls(
            name=d["name"],
            status=d.get("status", "draft"),
            description=d.get("description", ""),
            apify_actor_id=apify.get("actor_id", ""),
            apify_search_input=apify.get("search_input", {}),
            max_free_results=int(apify.get("max_free_results", 25)),
            sender_name=email.get("sender_name", ""),
            value_prop=email.get("value_prop", ""),
            cta=email.get("cta", ""),
            tone=email.get("tone", "professional, concise"),
        )


class ConfigError(RuntimeError):
    pass


@dataclass
class Settings:
    apify_api_token: str
    apify_actor_id_default: str
    gemini_api_key: str
    gemini_model: str
    google_oauth_client_secret_file: Path
    google_token_file: Path
    google_sheet_id: str
    gmail_sender_address: str
    github_token: str
    github_repo_name: str
    github_visibility: str


def load_settings(env_file: Path | None = None) -> Settings:
    load_dotenv(env_file or (REPO_ROOT / ".env"))

    def _path(key: str) -> Path:
        val = os.environ.get(key, "")
        return (REPO_ROOT / val) if val else Path()

    return Settings(
        apify_api_token=os.environ.get("APIFY_API_TOKEN", ""),
        apify_actor_id_default=os.environ.get("APIFY_ACTOR_ID", ""),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        google_oauth_client_secret_file=_path("GOOGLE_OAUTH_CLIENT_SECRET_FILE"),
        google_token_file=_path("GOOGLE_TOKEN_FILE"),
        google_sheet_id=os.environ.get("GOOGLE_SHEET_ID", ""),
        gmail_sender_address=os.environ.get("GMAIL_SENDER_ADDRESS", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        github_repo_name=os.environ.get("GITHUB_REPO_NAME", "lead-gen-agent"),
        github_visibility=os.environ.get("GITHUB_VISIBILITY", "private"),
    )


def load_profiles(path: Path | None = None) -> list[ClientProfile]:
    path = path or (REPO_ROOT / "config" / "client_profiles.yaml")
    data = yaml.safe_load(path.read_text())
    return [ClientProfile.from_dict(p) for p in data.get("profiles", [])]


def get_active_profile(path: Path | None = None) -> ClientProfile:
    """Returns the single active profile, or raises ConfigError.

    This is the human-in-the-loop gate for "which client profile": there is
    no automatic fallback and no default. A human must edit the YAML to
    mark exactly one profile `active`.
    """
    profiles = load_profiles(path)
    active = [p for p in profiles if p.status == "active"]
    if not active:
        raise ConfigError(
            "No active client profile. Edit config/client_profiles.yaml and "
            "set status: active on exactly one profile before running the "
            "pipeline. This is a deliberate human-in-the-loop gate."
        )
    if len(active) > 1:
        names = ", ".join(p.name for p in active)
        raise ConfigError(
            f"Multiple active profiles found ({names}). Exactly one profile "
            "may be active at a time so a run can never silently target the "
            "wrong client."
        )
    return active[0]
