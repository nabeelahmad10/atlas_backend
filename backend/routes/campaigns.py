"""
Campaign routes — create, trigger, and monitor campaigns.
Handles sending to the channel service and tracking status.
"""

from fastapi import APIRouter, Depends
import aiosqlite
import httpx
import os
from database import get_db
from models import CampaignCreate
import json

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

CHANNEL_SERVICE_URL = os.getenv("CHANNEL_SERVICE_URL", "http://localhost:8001")


@router.get("")
async def list_campaigns(db: aiosqlite.Connection = Depends(get_db)):
    """List all campaigns with their stats."""
    cursor = await db.execute("""
        SELECT c.*, s.name as segment_name
        FROM campaigns c
        LEFT JOIN segments s ON c.segment_id = s.id
        ORDER BY c.created_at DESC
    """)
    rows = await cursor.fetchall()
    return {"campaigns": [dict(r) for r in rows]}


@router.post("")
async def create_campaign(campaign: CampaignCreate, db: aiosqlite.Connection = Depends(get_db)):
    """Create and trigger a campaign. Sends messages to the channel service."""
    # Get customers in the segment
    cust_cursor = await db.execute(
        """SELECT c.id, c.name, c.email, c.phone FROM customers c
           JOIN segment_customers sc ON c.id = sc.customer_id
           WHERE sc.segment_id = ?""",
        (campaign.segment_id,)
    )
    customers = await cust_cursor.fetchall()

    if not customers:
        return {"error": "No customers in this segment"}

    from datetime import datetime
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO campaigns (name, segment_id, message_template, channel, status, total_sent, sent_at)
           VALUES (?, ?, ?, ?, 'sending', ?, ?)""",
        (campaign.name, campaign.segment_id, campaign.message_template, campaign.channel, len(customers), now)
    )
    campaign_id = cursor.lastrowid
    await db.commit()

    # Create individual communications and send to channel service
    communications = []
    for cust in customers:
        cust_dict = dict(cust)
        # Personalize message
        personalized_msg = campaign.message_template.replace("{{name}}", cust_dict["name"])

        comm_cursor = await db.execute(
            """INSERT INTO communications (campaign_id, customer_id, channel, message, status, sent_at)
               VALUES (?, ?, ?, ?, 'queued', ?)""",
            (campaign_id, cust_dict["id"], campaign.channel, personalized_msg, now)
        )
        comm_id = comm_cursor.lastrowid
        
        # Log QUEUED event
        await db.execute(
            "INSERT INTO event_log (event_type, communication_id, payload_json) VALUES (?, ?, ?)",
            ("MESSAGE_QUEUED", comm_id, json.dumps({"timestamp": now}))
        )

        communications.append({
            "communication_id": comm_id,
            "customer_id": cust_dict["id"],
            "customer_name": cust_dict["name"],
            "customer_email": cust_dict["email"],
            "customer_phone": cust_dict["phone"],
            "channel": campaign.channel,
            "message": personalized_msg,
        })

    await db.commit()

    # Send batch to channel service (fire and forget — async)
    crm_callback_url = os.getenv("CRM_CALLBACK_URL", "http://localhost:8000/api/receipts")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{CHANNEL_SERVICE_URL}/send",
                json={
                    "campaign_id": campaign_id,
                    "communications": communications,
                    "callback_url": crm_callback_url,
                },
            )
    except Exception as e:
        print(f"[WARN] Channel service error: {e}")
        # Update campaign status to reflect the error
        await db.execute(
            "UPDATE campaigns SET status = 'channel_error' WHERE id = ?",
            (campaign_id,)
        )
        await db.commit()

    return {
        "campaign_id": campaign_id,
        "name": campaign.name,
        "total_sent": len(customers),
        "status": "sending",
        "channel": campaign.channel,
    }


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get campaign details with communication breakdown."""
    cursor = await db.execute("""
        SELECT c.*, s.name as segment_name
        FROM campaigns c
        LEFT JOIN segments s ON c.segment_id = s.id
        WHERE c.id = ?
    """, (campaign_id,))
    campaign = await cursor.fetchone()
    if not campaign:
        return {"error": "Campaign not found"}

    camp_dict = dict(campaign)

    # Get communications
    comm_cursor = await db.execute("""
        SELECT co.*, cu.name as customer_name, cu.email as customer_email
        FROM communications co
        JOIN customers cu ON co.customer_id = cu.id
        WHERE co.campaign_id = ?
        ORDER BY co.created_at DESC
    """, (campaign_id,))
    comms = await comm_cursor.fetchall()
    camp_dict["communications"] = [dict(c) for c in comms]

    # Status breakdown
    status_cursor = await db.execute("""
        SELECT status, COUNT(*) as count
        FROM communications
        WHERE campaign_id = ?
        GROUP BY status
    """, (campaign_id,))
    statuses = await status_cursor.fetchall()
    camp_dict["status_breakdown"] = {row[0]: row[1] for row in statuses}

    return camp_dict
