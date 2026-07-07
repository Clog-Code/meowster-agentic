"""
Order placement + payment tool — STUB.

TODO(you): wire this up to:
  1. A real retailer/e-commerce API (or a checkout automation flow) to
     actually place the order.
  2. A payment gateway — the doc calls out Touch 'n Go eWallet
     (TNG_MERCHANT_ID / TNG_API_KEY / TNG_API_SECRET in .env) but this
     could equally be Stripe, a card token flow, etc.

Until then, `place_order` returns a mocked order + payment confirmation so
the rest of the agent (subagent prompts, status reporting) can be built and
tested end-to-end.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.tools import tool


@tool
def place_order(
    retailer_name: str,
    item_name: str,
    quantity: int,
    unit_price: float,
    delivery_address: str,
    currency: str = "MYR",
) -> dict[str, Any]:
    """
    Place an order for pet supplies (e.g. food) with a physical or online
    retailer, and pay for it via the configured payment gateway.

    Args:
        retailer_name: Name of the store or online retailer.
        item_name: Product name/brand to order.
        quantity: Number of units to order.
        unit_price: Price per unit in `currency`.
        delivery_address: Where the order should be delivered.
        currency: ISO currency code, defaults to MYR.

    Returns:
        An order + payment record. Until a real payment gateway is wired
        in (see TODO in order_tool.py), `status` will always be 'stubbed'
        and no real order or payment is made.
    """
    merchant_id = os.getenv("TNG_MERCHANT_ID")
    api_key = os.getenv("TNG_API_KEY")

    total = round(quantity * unit_price, 2)
    eta = (datetime.now(UTC) + timedelta(days=3)).date().isoformat()

    if not (merchant_id and api_key):
        return {
            "order_id": f"stub-{uuid.uuid4().hex[:8]}",
            "status": "stubbed",
            "retailer_name": retailer_name,
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total": total,
            "currency": currency,
            "delivery_address": delivery_address,
            "estimated_delivery_date": eta,
            "payment_status": "stubbed",
            "timestamp": datetime.now(UTC).isoformat(),
            "note": (
                "Payment gateway not configured. Set TNG_MERCHANT_ID and "
                "TNG_API_KEY in .env, then implement the real order + "
                "payment flow in order_tool.py."
            ),
        }

    # ------------------------------------------------------------------
    # TODO(you): real implementation, e.g.:
    #
    #   1. Call the retailer's order/checkout API (or scrape+submit a form
    #      via a headless browser if no public API exists) to create the
    #      order and get a retailer order_id.
    #   2. Call the TnG (or chosen gateway) payment API with merchant_id/
    #      api_key/api_secret to charge `total` and get a payment_status.
    #   3. Return the combined order + payment record below.
    # ------------------------------------------------------------------
    raise NotImplementedError("Real order + payment integration not yet implemented.")


COMMERCE_ORDER_TOOLS = [place_order]
