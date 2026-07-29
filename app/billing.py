"""Trial + Stripe subscription entitlement for grphly users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import Settings
from app.db import UserRecord, utcnow


PLAN_TRIAL = "trial"
PLAN_ACTIVE = "active"
PLAN_PAST_DUE = "past_due"
PLAN_CANCELED = "canceled"


@dataclass(frozen=True)
class Entitlement:
    allowed: bool
    reason: str
    plan_status: str
    trial_ends_at: datetime | None
    upgrade_url: str


def trial_ends_at(user: UserRecord, trial_days: int) -> datetime | None:
    if user.trial_started_at is None:
        return None
    start = user.trial_started_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start + timedelta(days=trial_days)


def evaluate_entitlement(user: UserRecord, settings: Settings) -> Entitlement:
    upgrade = settings.billing_upgrade_url
    ends = trial_ends_at(user, settings.trial_days)
    status = user.plan_status or PLAN_TRIAL

    if status == PLAN_ACTIVE:
        if user.plan_period_end is not None:
            period_end = user.plan_period_end
            if period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)
            if period_end < utcnow():
                return Entitlement(
                    allowed=False,
                    reason=(
                        "Subscription period ended. "
                        f"Renew with kb_upgrade or visit {upgrade}"
                    ),
                    plan_status=status,
                    trial_ends_at=ends,
                    upgrade_url=upgrade,
                )
        return Entitlement(
            allowed=True,
            reason="active subscription",
            plan_status=status,
            trial_ends_at=ends,
            upgrade_url=upgrade,
        )

    if ends is not None and utcnow() < ends:
        return Entitlement(
            allowed=True,
            reason="trial",
            plan_status=PLAN_TRIAL,
            trial_ends_at=ends,
            upgrade_url=upgrade,
        )

    return Entitlement(
        allowed=False,
        reason=(
            "Trial ended. Run kb_upgrade in chat for a Stripe checkout link, "
            f"or visit {upgrade}"
        ),
        plan_status=status,
        trial_ends_at=ends,
        upgrade_url=upgrade,
    )


def require_entitlement(user: UserRecord, settings: Settings) -> None:
    result = evaluate_entitlement(user, settings)
    if not result.allowed:
        raise PermissionError(result.reason)
