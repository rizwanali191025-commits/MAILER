"""Subscription plan definitions and limits.

A single source of truth for tiers, prices, and the quotas each tier unlocks.
Limits are enforced in :mod:`saas.models` (campaign count) and
:mod:`saas.sending` (monthly send cap, feature gates).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Plan:
    id: str
    name: str
    price_monthly: int          # USD/month, 0 = free
    monthly_send_limit: int     # emails per calendar month
    campaign_limit: int         # -1 = unlimited
    sender_rotation: bool       # multiple rotating "From" display names
    pptx_attachments: bool      # HTML→PowerPoint attachment feature
    tagline: str
    features: list[str] = field(default_factory=list)

    @property
    def is_free(self) -> bool:
        return self.price_monthly == 0

    def campaign_limit_label(self) -> str:
        return "Unlimited" if self.campaign_limit < 0 else str(self.campaign_limit)


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        price_monthly=0,
        monthly_send_limit=100,
        campaign_limit=2,
        sender_rotation=False,
        pptx_attachments=False,
        tagline="Kick the tyres",
        features=[
            "100 emails / month",
            "2 campaigns",
            "{{tag}} personalization",
            "Live preview & dry-run",
        ],
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        price_monthly=19,
        monthly_send_limit=5_000,
        campaign_limit=-1,
        sender_rotation=True,
        pptx_attachments=True,
        tagline="For growing outreach",
        features=[
            "5,000 emails / month",
            "Unlimited campaigns",
            "Rotating sender names",
            "HTML → PowerPoint attachments",
            "Everything in Free",
        ],
    ),
    "business": Plan(
        id="business",
        name="Business",
        price_monthly=49,
        monthly_send_limit=50_000,
        campaign_limit=-1,
        sender_rotation=True,
        pptx_attachments=True,
        tagline="High-volume teams",
        features=[
            "50,000 emails / month",
            "Unlimited campaigns",
            "Rotating sender names",
            "HTML → PowerPoint attachments",
            "Priority send queue",
            "Everything in Pro",
        ],
    ),
}

DEFAULT_PLAN_ID = "free"
ORDERED_PLAN_IDS = ["free", "pro", "business"]


def get_plan(plan_id: str | None) -> Plan:
    """Return a Plan, falling back to the free tier for unknown ids."""
    return PLANS.get(plan_id or DEFAULT_PLAN_ID, PLANS[DEFAULT_PLAN_ID])


def ordered_plans() -> list[Plan]:
    return [PLANS[pid] for pid in ORDERED_PLAN_IDS]
