from __future__ import annotations

import hashlib
import hmac
import json
import os
import time

import requests

from app.core.config import settings

webhook_url = "http://localhost:8000/webhook"
webhook_secret = settings.STRIPE_WEBHOOK_SECRET

if not webhook_secret:
    raise RuntimeError("Missing STRIPE_WEBHOOK_SECRET in environment")

event_payload = {
    "id": "evt_1TCgpM3gjmVC61ALvWaE2wXl",
    "object": "event",
    "api_version": "2026-01-28",
    "created": 1773927691,
    "type": "invoice.payment_failed",
    "data": {
        "object": {
            "id": "in_1TCgiD3gjmVC61ALfSeAqsmj",
            "object": "invoice",
            "amount_due": 2000,
            "amount_paid": 0,
            "amount_remaining": 2000,
            "attempt_count": 1,
            "attempted": True,
            "billing_reason": "subscription_cycle",
            "collection_method": "charge_automatically",
            "currency": "usd",
            "customer": "cus_UCUBRlvh37BUWI",
            "customer_email": "kraiemwassim1@gmail.com",
            "customer_name": "azeaze",
            "status": "open",
            "subscription": "sub_1TCgiD3gjmVC61ALtest",
            "lines": {
                "object": "list",
                "data": [
                    {
                        "id": "il_1TCgiE3gjmVC61ALdyCE3nKD",
                        "amount": 2000,
                        "currency": "usd",
                        "description": "Test subscription payment",
                        "period": {
                            "end": 1776603836,
                            "start": 1773925436
                        }
                    }
                ]
            }
        }
    }
}

# Stripe signs the exact raw payload: "{timestamp}.{payload}"
payload = json.dumps(event_payload, separators=(",", ":"))
timestamp = int(time.time())
signed_payload = f"{timestamp}.{payload}".encode("utf-8")
signature = hmac.new(
    webhook_secret.encode("utf-8"),
    signed_payload,
    hashlib.sha256,
).hexdigest()
stripe_signature = f"t={timestamp},v1={signature}"

response = requests.post(
    webhook_url,
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Stripe-Signature": stripe_signature,
    },
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
