import logging

import stripe
from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.core.kafka import publish

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Verify webhook signature when secret is configured
    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError:
            logger.warning("Invalid Stripe webhook signature")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    else:
        import json
        event = json.loads(payload)
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature verification")

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook received: %s", event_type)

    if event_type == "payment_intent.succeeded":
        order_id = data.get("metadata", {}).get("order_id")
        amount_cents = data.get("amount_received", data.get("amount", 0))
        await publish("payment.succeeded", {
            "order_id": order_id,
            "amount": amount_cents / 100,
            "stripe_payment_id": data.get("id"),
            "status": "succeeded",
        })

    elif event_type == "payment_intent.payment_failed":
        order_id = data.get("metadata", {}).get("order_id")
        error = data.get("last_payment_error", {}).get("message", "unknown error")
        logger.error("Payment failed for order_id=%s: %s", order_id, error)
        await publish("payment.failed", {
            "order_id": order_id,
            "reason": error,
            "stripe_payment_id": data.get("id"),
        })

    return {"received": True}
