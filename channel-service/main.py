"""
Channel Service — Stubbed Messaging Provider
Simulates message delivery with realistic async delays and outcomes.

This is a SEPARATE service that:
1. Receives send requests from the CRM API
2. Simulates delivery with random delays (1-5 seconds)
3. Assigns realistic outcomes (delivered, failed, opened, clicked)
4. Asynchronously calls back to the CRM receipt API with results
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import httpx
import random
from datetime import datetime, timedelta

app = FastAPI(
    title="Atlas Channel Service",
    description="Stubbed messaging provider for CRM campaign delivery simulation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Communication(BaseModel):
    communication_id: int
    customer_id: int
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    channel: str
    message: str


class SendRequest(BaseModel):
    campaign_id: int
    communications: List[Communication]
    callback_url: str


# Delivery simulation configuration
DELIVERY_RATES = {
    "email": {"delivered": 0.95, "opened": 0.45, "clicked": 0.15},
    "sms": {"delivered": 0.98, "opened": 0.85, "clicked": 0.25},
    "whatsapp": {"delivered": 0.99, "opened": 0.90, "clicked": 0.35},
}

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for independent microservice deployment."""
    return {"status": "healthy"}

# Track delivery stats
delivery_stats = {
    "total_received": 0,
    "total_processed": 0,
    "total_callbacks_sent": 0,
    "total_callback_failures": 0,
}


@app.get("/")
async def root():
    return {
        "name": "Atlas Channel Service",
        "version": "1.0.0",
        "status": "healthy",
        "stats": delivery_stats,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stats")
async def get_stats():
    """Get delivery simulation statistics."""
    return delivery_stats


@app.post("/send")
async def receive_send_request(request: SendRequest):
    """
    Receive a batch of communications from the CRM.
    Immediately returns 202 Accepted, then processes asynchronously.
    """
    delivery_stats["total_received"] += len(request.communications)

    # Fire off async processing — don't block the response
    asyncio.create_task(
        process_communications(
            request.campaign_id,
            request.communications,
            request.callback_url,
        )
    )

    return {
        "status": "accepted",
        "campaign_id": request.campaign_id,
        "total_queued": len(request.communications),
        "message": "Communications queued for simulated delivery",
    }


async def process_communications(
    campaign_id: int,
    communications: List[Communication],
    callback_url: str,
):
    """
    Simulate message delivery for each communication.
    Processes in small batches to simulate realistic delivery patterns.
    """
    batch_size = 5
    for i in range(0, len(communications), batch_size):
        batch = communications[i : i + batch_size]
        tasks = [
            simulate_delivery(comm, callback_url)
            for comm in batch
        ]
        await asyncio.gather(*tasks)

        # Small inter-batch delay to simulate processing time
        if i + batch_size < len(communications):
            await asyncio.sleep(random.uniform(0.3, 1.0))

    print(f"[DONE] Campaign {campaign_id}: Finished processing {len(communications)} communications")


async def simulate_delivery(comm: Communication, callback_url: str):
    """
    Simulate the full lifecycle of a single communication:
    1. Initial delivery delay (1-3 seconds)
    2. Determine delivery outcome (delivered or failed)
    3. If delivered, simulate open after delay
    4. If opened, simulate click after delay
    """
    now = datetime.now()

    # ─── Step 0: Sent (Dispatched to network) ───────────────
    await asyncio.sleep(random.uniform(0.1, 0.5))
    sent_time = now + timedelta(seconds=random.uniform(0.1, 0.5))
    await send_callback(callback_url, {
        "communication_id": comm.communication_id,
        "status": "sent",
        "timestamp": sent_time.isoformat(),
    })

    # ─── Step 1: Delivery ────────────────────────────────────
    await asyncio.sleep(random.uniform(0.5, 2.0))

    # 90% delivery rate, 10% failure
    is_delivered = random.random() < 0.90

    if not is_delivered:
        # Failed delivery
        failure_reasons = [
            "Invalid phone number",
            "Recipient inbox full",
            "Network timeout",
            "Blocked by recipient",
            "Invalid email address",
            "Rate limit exceeded",
        ]
        await send_callback(callback_url, {
            "communication_id": comm.communication_id,
            "status": "failed",
            "timestamp": (now + timedelta(seconds=random.randint(1, 3))).isoformat(),
            "failure_reason": random.choice(failure_reasons),
        })
        delivery_stats["total_processed"] += 1
        return

    # Delivered!
    delivered_time = now + timedelta(seconds=random.randint(1, 5))
    await send_callback(callback_url, {
        "communication_id": comm.communication_id,
        "status": "delivered",
        "timestamp": delivered_time.isoformat(),
    })

    # ─── Step 2: Open simulation ─────────────────────────────
    # 65% of delivered messages get opened
    if random.random() < 0.65:
        await asyncio.sleep(random.uniform(1.0, 3.0))
        opened_time = delivered_time + timedelta(seconds=random.randint(30, 3600))
        await send_callback(callback_url, {
            "communication_id": comm.communication_id,
            "status": "opened",
            "timestamp": opened_time.isoformat(),
        })

        # ─── Step 3: Click simulation ────────────────────────
        # 35% of opened messages get clicked
        if random.random() < 0.35:
            await asyncio.sleep(random.uniform(0.5, 1.5))
            clicked_time = opened_time + timedelta(seconds=random.randint(10, 600))
            await send_callback(callback_url, {
                "communication_id": comm.communication_id,
                "status": "clicked",
                "timestamp": clicked_time.isoformat(),
            })

    delivery_stats["total_processed"] += 1


async def send_callback(callback_url: str, receipt: dict):
    """Send a delivery receipt back to the CRM API."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(callback_url, json=receipt)
                response.raise_for_status()
                delivery_stats["total_callbacks_sent"] += 1
                return
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                print(f"[RETRY] Callback retry {attempt + 1} for comm {receipt['communication_id']}: {e}")
            else:
                print(f"[FAIL] Callback failed after {max_retries} attempts for comm {receipt['communication_id']}: {e}")
                delivery_stats["total_callback_failures"] += 1
