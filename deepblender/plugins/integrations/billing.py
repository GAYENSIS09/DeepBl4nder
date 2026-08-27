"""BillingPlugin : integration Stripe pour la facturation.

Gere les abonnements, credits, et facturation des utilisateurs.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from deepblender.plugins.base import Plugin

logger = logging.getLogger("deepblender.plugins.billing")


@dataclass
class BillingPlan:
    """Plan d'abonnement."""

    name: str
    price_usd: float
    credits_per_month: int
    max_concurrent_renders: int
    max_duration_seconds: int
    features: list[str] = field(default_factory=list)


BUILTIN_PLANS = {
    "free": BillingPlan(
        name="Gratuit",
        price_usd=0.0,
        credits_per_month=50,
        max_concurrent_renders=1,
        max_duration_seconds=30,
        features=["basic_render"],
    ),
    "pro": BillingPlan(
        name="Pro",
        price_usd=29.0,
        credits_per_month=500,
        max_concurrent_renders=3,
        max_duration_seconds=120,
        features=["basic_render", "music_gen", "tts", "color_grading"],
    ),
    "studio": BillingPlan(
        name="Studio",
        price_usd=99.0,
        credits_per_month=2000,
        max_concurrent_renders=10,
        max_duration_seconds=600,
        features=[
            "basic_render", "music_gen", "tts", "color_grading",
            "batch_render", "priority_queue", "custom_agents",
        ],
    ),
}


@dataclass
class BillingPlugin(Plugin):
    """Gestion de la facturation via Stripe."""

    name: str = "billing"
    description: str = "Facturation Stripe : abonnements, credits, plans."
    _stripe_client: Any = field(default=None, repr=False)

    def __post_init__(self) -> None:
        stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if stripe_key:
            try:
                import stripe
                stripe.api_key = stripe_key
                self._stripe_client = stripe
                logger.info("Stripe connecte")
            except ImportError:
                logger.warning("stripe non installe")
        else:
            logger.info("Stripe non configure, facturation desactivee")

    def available(self) -> bool:
        return self._stripe_client is not None

    def get_plans(self) -> dict[str, BillingPlan]:
        """Retourne les plans disponibles."""
        return BUILTIN_PLANS

    def create_checkout_session(
        self,
        user_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str | None:
        """Cree une session de paiement Stripe Checkout."""
        if not self._stripe_client:
            return None

        plan = BUILTIN_PLANS.get(plan_id)
        if not plan:
            return None

        try:
            # En prod, on utiliserait des Price IDs Stripe
            # Ici, simulation pour le dev
            session = self._stripe_client.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"DeepBlender {plan.name}"},
                        "unit_amount": int(plan.price_usd * 100),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"user_id": user_id, "plan_id": plan_id},
            )
            return session.url
        except Exception as exc:
            logger.error("Stripe checkout error: %s", exc)
            return None

    def check_credits(self, user_id: str, plan_id: str, credits_used: int) -> bool:
        """Verifie si l'utilisateur a assez de credits."""
        plan = BUILTIN_PLANS.get(plan_id, BUILTIN_PLANS["free"])
        return credits_used < plan.credits_per_month

    def get_usage(self, user_id: str) -> dict[str, Any]:
        """Recupere l'utilisation d'un utilisateur."""
        return {
            "user_id": user_id,
            "credits_used": 0,
            "credits_limit": 50,
            "concurrent_renders": 0,
            "renders_this_month": 0,
        }
