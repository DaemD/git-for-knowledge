"""Lemon Squeezy Checkout + webhook helpers for grphly billing."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.db import ControlStore, UserRecord

logger = logging.getLogger(__name__)

LEMON_API = "https://api.lemonsqueezy.com/v1"


class BillingNotConfiguredError(RuntimeError):
    pass


def _require_configured(settings: Settings) -> None:
    if not settings.lemon_configured:
        raise BillingNotConfiguredError(
            "Lemon Squeezy is not configured. Set LEMON_SQUEEZY_API_KEY, "
            "LEMON_SQUEEZY_STORE_ID, and LEMON_SQUEEZY_VARIANT_ID."
        )


async def create_checkout_session(
    settings: Settings,
    user: UserRecord,
) -> str:
    _require_configured(settings)
    landing = (settings.billing_landing_url or str(settings.public_base_url)).rstrip(
        "/"
    )
    assert settings.lemon_squeezy_api_key is not None
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user.email or "",
                    "custom": {"user_id": user.id},
                },
                "product_options": {
                    "redirect_url": f"{landing}/#pricing?checkout=success",
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(settings.lemon_squeezy_store_id),
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(settings.lemon_squeezy_variant_id),
                    }
                },
            },
        }
    }
    headers = {
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
        "Authorization": (
            f"Bearer {settings.lemon_squeezy_api_key.get_secret_value()}"
        ),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{LEMON_API}/checkouts",
            json=payload,
            headers=headers,
        )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Lemon Squeezy checkout failed ({response.status_code}): "
            f"{response.text[:300]}"
        )
    data = response.json().get("data") or {}
    url = (data.get("attributes") or {}).get("url")
    if not url:
        raise RuntimeError("Lemon Squeezy checkout did not return a URL")
    return str(url)


def verify_webhook_signature(
    settings: Settings,
    payload: bytes,
    signature: str,
) -> None:
    if not settings.lemon_squeezy_webhook_secret:
        raise BillingNotConfiguredError("LEMON_SQUEEZY_WEBHOOK_SECRET is not set")
    secret = settings.lemon_squeezy_webhook_secret.get_secret_value().encode("utf-8")
    digest = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, signature or ""):
        raise ValueError("Invalid Lemon Squeezy webhook signature")


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (OSError, ValueError, OverflowError):
            return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _subscription_status(status: str | None) -> str:
    mapping = {
        "active": "active",
        "on_trial": "active",
        "paused": "past_due",
        "past_due": "past_due",
        "unpaid": "past_due",
        "cancelled": "canceled",
        "expired": "canceled",
    }
    return mapping.get(str(status or "").lower(), "canceled")


async def handle_lemon_webhook_event(
    control: ControlStore,
    event: dict[str, Any],
) -> None:
    meta = event.get("meta") or {}
    event_name = str(
        meta.get("event_name") or event.get("event_name") or ""
    )
    custom = meta.get("custom_data") or {}
    user_id = custom.get("user_id")
    data = event.get("data") or {}
    attrs = data.get("attributes") or {}
    resource_id = data.get("id")

    if event_name in {"subscription_created", "subscription_updated"}:
        customer_id = attrs.get("customer_id")
        status = _subscription_status(attrs.get("status"))
        period_end = _parse_dt(
            attrs.get("renews_at") or attrs.get("ends_at")
        )
        await control.apply_stripe_subscription(
            user_id=str(user_id) if user_id else None,
            stripe_customer_id=str(customer_id) if customer_id else None,
            stripe_subscription_id=str(resource_id) if resource_id else None,
            plan_status=status,
            plan_period_end=period_end,
        )
        return

    if event_name in {"subscription_cancelled", "subscription_expired"}:
        customer_id = attrs.get("customer_id")
        period_end = _parse_dt(attrs.get("ends_at") or attrs.get("renews_at"))
        await control.apply_stripe_subscription(
            user_id=str(user_id) if user_id else None,
            stripe_customer_id=str(customer_id) if customer_id else None,
            stripe_subscription_id=str(resource_id) if resource_id else None,
            plan_status="canceled",
            plan_period_end=period_end,
        )
        return

    if event_name == "order_created" and user_id:
        # One-time fallback; subscriptions should prefer subscription_* events.
        customer_id = attrs.get("customer_id")
        await control.apply_stripe_subscription(
            user_id=str(user_id),
            stripe_customer_id=str(customer_id) if customer_id else None,
            plan_status="active",
        )
        return

    logger.info("Ignoring Lemon Squeezy event type=%s", event_name)
