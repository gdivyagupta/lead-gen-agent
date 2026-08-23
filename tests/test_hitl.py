import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402
from leadgen.config import ClientProfile  # noqa: E402
from leadgen.hitl import (  # noqa: E402
    HumanApprovalRequired,
    require_profile_confirmation,
    require_send_confirmation,
    require_spend_approval,
)


def _profile(name="acme", max_free_results=25):
    return ClientProfile(
        name=name,
        status="active",
        description="",
        apify_actor_id="x",
        apify_search_input={},
        max_free_results=max_free_results,
        sender_name="",
        value_prop="",
        cta="",
        tone="",
    )


def test_profile_confirmation_requires_explicit_match():
    profile = _profile("acme")
    with pytest.raises(HumanApprovalRequired):
        require_profile_confirmation(profile, None)
    with pytest.raises(HumanApprovalRequired):
        require_profile_confirmation(profile, "wrong-name")
    require_profile_confirmation(profile, "acme")  # does not raise


def test_spend_approval_allows_within_free_threshold():
    assert require_spend_approval(10, free_threshold=25, approved_spend=None) == 10


def test_spend_approval_blocks_over_threshold_without_approval():
    with pytest.raises(HumanApprovalRequired):
        require_spend_approval(100, free_threshold=25, approved_spend=None)


def test_spend_approval_blocks_insufficient_approval():
    with pytest.raises(HumanApprovalRequired):
        require_spend_approval(100, free_threshold=25, approved_spend=50)


def test_spend_approval_allows_when_approved():
    assert require_spend_approval(100, free_threshold=25, approved_spend=100) == 100


def test_send_confirmation_defaults_to_draft():
    assert require_send_confirmation(False) == "draft_created"
    assert require_send_confirmation(True) == "sent"
