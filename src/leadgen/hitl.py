"""Human-in-the-loop gates.

Two categories of decision in this pipeline are deliberately never made
automatically: which client profile to target, and anything that spends
money or sends real email to a real person. The functions here are the
single choke point for both — every code path that needs to cross one of
these lines must call through here, so the gate can't be silently bypassed
by a new caller forgetting to check.
"""

from __future__ import annotations

from .config import ClientProfile


class HumanApprovalRequired(RuntimeError):
    pass


def require_profile_confirmation(profile: ClientProfile, confirm_arg: str | None) -> None:
    """The active profile in YAML is a human's choice; requiring the CLI
    caller to *also* name it out loud (--confirm-profile) stops a stale
    terminal/cron job from silently emailing the wrong client's list after
    someone else flips the active profile in git.
    """
    if not confirm_arg:
        raise HumanApprovalRequired(
            f"Active profile is '{profile.name}'. Re-run with "
            f"--confirm-profile {profile.name} to confirm this is who you "
            "intend to contact."
        )
    if confirm_arg != profile.name:
        raise HumanApprovalRequired(
            f"--confirm-profile '{confirm_arg}' does not match the active "
            f"profile '{profile.name}'. Refusing to run."
        )


def require_spend_approval(
    requested_results: int, free_threshold: int, approved_spend: int | None
) -> int:
    """Returns the number of results this run is allowed to fetch.

    Apify usage costs money past a point. Anything within the profile's
    free_threshold runs with no extra confirmation. Anything above it
    requires an explicit --approve-spend N >= requested_results.
    """
    if requested_results <= free_threshold:
        return requested_results
    if approved_spend is None:
        raise HumanApprovalRequired(
            f"Requested {requested_results} leads, which is above this "
            f"profile's free threshold of {free_threshold}. Re-run with "
            f"--approve-spend {requested_results} to approve the spend."
        )
    if approved_spend < requested_results:
        raise HumanApprovalRequired(
            f"--approve-spend {approved_spend} is less than the "
            f"{requested_results} leads requested. Raise it or lower "
            "--limit."
        )
    return requested_results


def require_send_confirmation(send_flag: bool) -> str:
    """Returns the sheet/email status to use for this run.

    Default is draft-only. Actually sending requires the caller to pass
    --send explicitly; there is no config-file way to turn this on so it
    can never be flipped on by an automated edit alone.
    """
    return "sent" if send_flag else "draft_created"
