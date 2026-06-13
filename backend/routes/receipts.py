"""
Receipt routes — webhook endpoint for channel service delivery callbacks.
Updates communication status and campaign aggregate stats.
"""

from fastapi import APIRouter, Depends
import aiosqlite
from datetime import datetime
from database import get_db
from models import DeliveryReceipt
from typing import List
import json

router = APIRouter(prefix="/api/receipts", tags=["Receipts"])


@router.post("")
async def receive_receipt(receipt: DeliveryReceipt, db: aiosqlite.Connection = Depends(get_db)):
    """
    Receive a single delivery receipt from the channel service.
    Updates the communication record and campaign aggregate stats.
    """
    now = datetime.now().isoformat()

    # Get current communication status
    cursor = await db.execute(
        "SELECT campaign_id, status FROM communications WHERE id = ?",
        (receipt.communication_id,)
    )
    comm = await cursor.fetchone()
    if not comm:
        return {"error": "Communication not found", "communication_id": receipt.communication_id}

    campaign_id = comm[0]
    old_status = comm[1]
    new_status = receipt.status

    # Status progression: sent → delivered → opened → clicked
    # Also: sent → failed
    status_hierarchy = {"pending": 0, "sent": 1, "delivered": 2, "opened": 3, "clicked": 4, "failed": -1}

    # Idempotency check: Have we already processed this event for this communication?
    event_type = f"MESSAGE_{new_status.upper()}"
    idempotency_cursor = await db.execute(
        "SELECT 1 FROM event_log WHERE communication_id = ? AND event_type = ?",
        (receipt.communication_id, event_type)
    )
    if await idempotency_cursor.fetchone():
        return {"message": "Idempotent request ignored", "current_status": old_status}

    # Only progress forward (don't regress from 'opened' to 'delivered')
    if new_status != "failed":
        if status_hierarchy.get(new_status, 0) <= status_hierarchy.get(old_status, 0):
            return {"message": "Status already at or past this stage", "current_status": old_status}

    # Log immutable event
    payload = json.dumps({"timestamp": receipt.timestamp, "failure_reason": receipt.failure_reason})
    await db.execute(
        "INSERT INTO event_log (event_type, communication_id, payload_json) VALUES (?, ?, ?)",
        (event_type, receipt.communication_id, payload)
    )

    # Update communication record
    update_fields = {"status": new_status}
    if new_status == "delivered":
        update_fields["delivered_at"] = receipt.timestamp
    elif new_status == "opened":
        update_fields["opened_at"] = receipt.timestamp
        if old_status in ("queued", "sent"):
            update_fields["delivered_at"] = receipt.timestamp
    elif new_status == "clicked":
        update_fields["clicked_at"] = receipt.timestamp
        if old_status in ("queued", "sent", "delivered"):
            update_fields["opened_at"] = receipt.timestamp
        if old_status in ("queued", "sent"):
            update_fields["delivered_at"] = receipt.timestamp
    elif new_status == "failed":
        update_fields["failed_reason"] = receipt.failure_reason

    set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
    await db.execute(
        f"UPDATE communications SET {set_clause} WHERE id = ?",
        (*update_fields.values(), receipt.communication_id)
    )

    # Recalculate campaign aggregates
    await _update_campaign_stats(db, campaign_id)
    await db.commit()

    return {
        "message": "Receipt processed",
        "communication_id": receipt.communication_id,
        "new_status": new_status,
    }


@router.post("/batch")
async def receive_batch_receipts(receipts: List[DeliveryReceipt], db: aiosqlite.Connection = Depends(get_db)):
    """
    Receive multiple delivery receipts at once.
    More efficient for the channel service to batch callbacks.
    """
    results = []
    campaign_ids = set()

    for receipt in receipts:
        cursor = await db.execute(
            "SELECT campaign_id, status FROM communications WHERE id = ?",
            (receipt.communication_id,)
        )
        comm = await cursor.fetchone()
        if not comm:
            results.append({"communication_id": receipt.communication_id, "status": "not_found"})
            continue

        campaign_id = comm[0]
        campaign_ids.add(campaign_id)
        old_status = comm[1]
        new_status = receipt.status

        event_type = f"MESSAGE_{new_status.upper()}"
        idempotency_cursor = await db.execute(
            "SELECT 1 FROM event_log WHERE communication_id = ? AND event_type = ?",
            (receipt.communication_id, event_type)
        )
        if await idempotency_cursor.fetchone():
            results.append({"communication_id": receipt.communication_id, "status": "idempotent_skip"})
            continue

        payload = json.dumps({"timestamp": receipt.timestamp, "failure_reason": receipt.failure_reason})
        await db.execute(
            "INSERT INTO event_log (event_type, communication_id, payload_json) VALUES (?, ?, ?)",
            (event_type, receipt.communication_id, payload)
        )

        # Update communication
        update_fields = {"status": new_status}
        if new_status == "delivered":
            update_fields["delivered_at"] = receipt.timestamp
        elif new_status == "opened":
            update_fields["opened_at"] = receipt.timestamp
        elif new_status == "clicked":
            update_fields["clicked_at"] = receipt.timestamp
        elif new_status == "failed":
            update_fields["failed_reason"] = receipt.failure_reason

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        await db.execute(
            f"UPDATE communications SET {set_clause} WHERE id = ?",
            (*update_fields.values(), receipt.communication_id)
        )

        results.append({
            "communication_id": receipt.communication_id,
            "status": "processed",
            "new_status": new_status,
        })

    # Update all affected campaign stats
    for cid in campaign_ids:
        await _update_campaign_stats(db, cid)

    await db.commit()

    return {"processed": len(results), "results": results}


async def _update_campaign_stats(db: aiosqlite.Connection, campaign_id: int):
    """Recalculate campaign aggregate stats from communications."""
    cursor = await db.execute("""
        SELECT
            COUNT(*) as total_sent,
            COUNT(CASE WHEN status IN ('delivered', 'opened', 'clicked') THEN 1 END) as total_delivered,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as total_failed,
            COUNT(CASE WHEN status IN ('opened', 'clicked') THEN 1 END) as total_opened,
            COUNT(CASE WHEN status = 'clicked' THEN 1 END) as total_clicked
        FROM communications WHERE campaign_id = ?
    """, (campaign_id,))
    stats = await cursor.fetchone()

    # Determine campaign status
    total = stats[0]
    delivered = stats[1]
    failed = stats[2]
    if delivered + failed >= total:
        status = "completed"
    else:
        status = "sending"

    await db.execute("""
        UPDATE campaigns
        SET total_sent = ?, total_delivered = ?, total_failed = ?,
            total_opened = ?, total_clicked = ?, status = ?
        WHERE id = ?
    """, (stats[0], stats[1], stats[2], stats[3], stats[4], status, campaign_id))
