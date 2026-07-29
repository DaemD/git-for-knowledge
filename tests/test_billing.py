from datetime import datetime, timedelta, timezone

import pytest

from app.billing import evaluate_entitlement, require_entitlement
from app.config import Settings
from app.db import InMemoryControlStore, UserRecord, utcnow
from app.service import KnowledgeService
from app.stripe_billing import handle_stripe_webhook_event
from tests.test_service import FakeNamsStore


def _settings(**overrides) -> Settings:
    base = dict(
        memory_api_key="test",
        memory_workspace_id="ws-test",
        auth_disabled=True,
        public_base_url="http://test.local",
        trial_days=14,
        billing_landing_url="https://landing.test",
        stripe_price_id="",
    )
    base.update(overrides)
    return Settings(**base)


def _user(**overrides) -> UserRecord:
    now = utcnow()
    data = dict(
        id="user-1",
        email="a@example.com",
        display_name="A",
        created_at=now,
        updated_at=now,
        trial_started_at=now,
        plan_status="trial",
    )
    data.update(overrides)
    return UserRecord(**data)


def test_entitlement_allows_active_trial() -> None:
    user = _user()
    result = evaluate_entitlement(user, _settings())
    assert result.allowed is True
    assert result.reason == "trial"


def test_entitlement_blocks_expired_trial() -> None:
    started = utcnow() - timedelta(days=20)
    user = _user(trial_started_at=started, plan_status="trial")
    result = evaluate_entitlement(user, _settings())
    assert result.allowed is False
    assert "Trial ended" in result.reason
    assert "#pricing" in result.upgrade_url


def test_entitlement_allows_active_subscription() -> None:
    started = utcnow() - timedelta(days=40)
    user = _user(
        trial_started_at=started,
        plan_status="active",
        plan_period_end=utcnow() + timedelta(days=20),
    )
    result = evaluate_entitlement(user, _settings())
    assert result.allowed is True


def test_require_entitlement_raises() -> None:
    user = _user(
        trial_started_at=utcnow() - timedelta(days=30),
        plan_status="canceled",
    )
    with pytest.raises(PermissionError, match="Trial ended"):
        require_entitlement(user, _settings())


@pytest.mark.asyncio
async def test_webhook_checkout_activates_user() -> None:
    control = InMemoryControlStore()
    user = await control.upsert_user("sub-1", email="pay@example.com")
    # Expire trial so only subscription unlocks.
    control.users[user.id] = UserRecord(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
        trial_started_at=utcnow() - timedelta(days=30),
        plan_status="trial",
    )
    await handle_stripe_webhook_event(
        control,
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": user.id,
                    "customer": "cus_123",
                    "subscription": "sub_123",
                }
            },
        },
    )
    updated = await control.get_user(user.id)
    assert updated is not None
    assert updated.plan_status == "active"
    assert updated.stripe_customer_id == "cus_123"
    assert updated.stripe_subscription_id == "sub_123"


@pytest.mark.asyncio
async def test_expired_user_cannot_push(monkeypatch) -> None:
    monkeypatch.setenv("TRIAL_DAYS", "14")
    from app.config import get_settings

    get_settings.cache_clear()
    control = InMemoryControlStore()
    service = KnowledgeService(FakeNamsStore(), control)
    user = await control.upsert_user("sub-exp", email="exp@example.com")
    control.users[user.id] = UserRecord(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        updated_at=user.updated_at,
        trial_started_at=utcnow() - timedelta(days=30),
        plan_status="trial",
    )
    with pytest.raises(PermissionError, match="Trial ended"):
        await service.remember(
            user.id,
            "kb1",
            "secret",
            idempotency_key="k1",
        )


@pytest.mark.asyncio
async def test_kb_upgrade_without_stripe_returns_message() -> None:
    control = InMemoryControlStore()
    service = KnowledgeService(FakeNamsStore(), control)
    user = await control.upsert_user("sub-up", email="up@example.com")
    result = await service.create_upgrade_checkout(user.id)
    assert result.checkout_url is None
    assert "Stripe is not configured" in result.message or "pricing" in result.message
