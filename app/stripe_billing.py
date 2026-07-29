"""Stripe Checkout + webhook helpers for grphly billing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import stripe

from app.config import Settings
from app.db import ControlStore, UserRecord

logger = logging.getLogger(__name__)


class BillingNotConfiguredError(RuntimeError):
    pass


def _configure_stripe(settings: Settings) -> None:
    if not settings.stripe_configured:
        raise BillingNotConfiguredError(
            "Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_ID."
        )
    stripe.api_key = settings.stripe_secret_key.get_secret_value()


async def create_checkout_session(
    settings: Settings,
    user: UserRecord,
) -> str:
    _configure_stripe(settings)
    landing = (settings.billing_landing_url or str(settings.public_base_url)).rstrip(
        "/"
    )
    params: dict[str, Any] = {
        "mode": "subscription",
        "line_items": [{"price": settings.stripe_price_id, "quantity": 1}],
        "success_url": f"{landing}/#pricing?checkout=success",
        "cancel_url": f"{landing}/#pricing?checkout=cancel",
        "client_reference_id": user.id,
        "metadata": {"user_id": user.id},
        "subscription_data": {"metadata": {"user_id": user.id}},
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    elif user.email:
        params["customer_email"] = user.email

    session = stripe.checkout.Session.create(**params)
    if not session.url:
        raise RuntimeError("Stripe Checkout Session did not return a URL")
    return str(session.url)


def _ts_to_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _subscription_status(status: str | None) -> str:
    mapping = {
        "active": "active",
        "trialing": "active",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
    }
    return mapping.get(str(status or ""), "canceled")


async def handle_stripe_webhook_event(
    control: ControlStore,
    event: dict[str, Any],
) -> None:
    event_type = str(event.get("type") or "")
    data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id") or (data.get("metadata") or {}).get(
            "user_id"
        )
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id")
        if isinstance(subscription_id, dict):
            subscription_id = subscription_id.get("id")
        await control.apply_stripe_subscription(
            user_id=str(user_id) if user_id else None,
            stripe_customer_id=str(customer_id) if customer_id else None,
            stripe_subscription_id=(
                str(subscription_id) if subscription_id else None
            ),
            plan_status="active",
        )
        return

    if event_type in {
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        subscription_id = data.get("id")
        customer_id = data.get("customer")
        status = _subscription_status(data.get("status"))
        if event_type == "customer.subscription.deleted":
            status = "canceled"
        period_end = _ts_to_dt(data.get("current_period_end"))
        await control.apply_stripe_subscription(
            stripe_customer_id=str(customer_id) if customer_id else None,
            stripe_subscription_id=(
                str(subscription_id) if subscription_id else None
            ),
            plan_status=status,
            plan_period_end=period_end,
        )
        return

    logger.info("Ignoring Stripe event type=%s", event_type)


def construct_webhook_event(
    settings: Settings,
    payload: bytes,
    signature: str,
) -> dict[str, Any]:
    if not settings.stripe_webhook_secret:
        raise BillingNotConfiguredError("STRIPE_WEBHOOK_SECRET is not set")
    event = stripe.Webhook.construct_event(
        payload,
        signature,
        settings.stripe_webhook_secret.get_secret_value(),
    )
    if hasattr(event, "to_dict"):
        return event.to_dict()
    return dict(event)
