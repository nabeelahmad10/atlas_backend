"""
Analytics routes — campaign performance metrics and insights.
"""

from fastapi import APIRouter, Depends
import aiosqlite
from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("")
async def get_overall_analytics(db: aiosqlite.Connection = Depends(get_db)):
    """Get overall analytics across all campaigns."""
    # Campaign-level stats
    cursor = await db.execute("""
        SELECT
            id, name, channel, status, total_sent, total_delivered,
            total_failed, total_opened, total_clicked, sent_at, created_at
        FROM campaigns
        ORDER BY created_at DESC
    """)
    campaigns = await cursor.fetchall()

    campaign_analytics = []
    total_sent_all = 0
    total_delivered_all = 0
    total_opened_all = 0
    total_clicked_all = 0
    total_failed_all = 0

    for c in campaigns:
        cd = dict(c)
        sent = cd["total_sent"] or 0
        delivered = cd["total_delivered"] or 0
        opened = cd["total_opened"] or 0
        clicked = cd["total_clicked"] or 0
        failed = cd["total_failed"] or 0

        cd["delivery_rate"] = round((delivered / sent * 100) if sent > 0 else 0, 1)
        cd["open_rate"] = round((opened / delivered * 100) if delivered > 0 else 0, 1)
        cd["click_rate"] = round((clicked / opened * 100) if opened > 0 else 0, 1)
        cd["failure_rate"] = round((failed / sent * 100) if sent > 0 else 0, 1)

        campaign_analytics.append(cd)

        total_sent_all += sent
        total_delivered_all += delivered
        total_opened_all += opened
        total_clicked_all += clicked
        total_failed_all += failed

    # Overall rates
    overall_delivery_rate = round((total_delivered_all / total_sent_all * 100) if total_sent_all > 0 else 0, 1)
    overall_open_rate = round((total_opened_all / total_delivered_all * 100) if total_delivered_all > 0 else 0, 1)
    overall_click_rate = round((total_clicked_all / total_opened_all * 100) if total_opened_all > 0 else 0, 1)

    # Channel breakdown
    channel_cursor = await db.execute("""
        SELECT channel, COUNT(*) as campaigns,
            SUM(total_sent) as sent, SUM(total_delivered) as delivered,
            SUM(total_opened) as opened, SUM(total_clicked) as clicked
        FROM campaigns
        GROUP BY channel
    """)
    channels = await channel_cursor.fetchall()

    # Customer engagement stats
    engagement_cursor = await db.execute("""
        SELECT
            COUNT(DISTINCT customer_id) as customers_reached,
            COUNT(*) as total_communications
        FROM communications
    """)
    engagement = dict(await engagement_cursor.fetchone())

    # Recent activity (last 10 status updates)
    activity_cursor = await db.execute("""
        SELECT co.id, co.status, co.customer_id, cu.name as customer_name,
               ca.name as campaign_name, co.delivered_at, co.opened_at, co.clicked_at
        FROM communications co
        JOIN customers cu ON co.customer_id = cu.id
        JOIN campaigns ca ON co.campaign_id = ca.id
        ORDER BY co.rowid DESC
        LIMIT 10
    """)
    recent_activity = [dict(r) for r in await activity_cursor.fetchall()]

    return {
        "overview": {
            "total_campaigns": len(campaign_analytics),
            "total_sent": total_sent_all,
            "total_delivered": total_delivered_all,
            "total_opened": total_opened_all,
            "total_clicked": total_clicked_all,
            "total_failed": total_failed_all,
            "delivery_rate": overall_delivery_rate,
            "open_rate": overall_open_rate,
            "click_rate": overall_click_rate,
        },
        "campaigns": campaign_analytics,
        "channels": [dict(c) for c in channels],
        "engagement": engagement,
        "recent_activity": recent_activity,
    }


@router.get("/campaigns/{campaign_id}")
async def get_campaign_analytics(campaign_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get detailed analytics for a specific campaign."""
    # Campaign info
    cursor = await db.execute("""
        SELECT c.*, s.name as segment_name
        FROM campaigns c
        LEFT JOIN segments s ON c.segment_id = s.id
        WHERE c.id = ?
    """, (campaign_id,))
    campaign = await cursor.fetchone()
    if not campaign:
        return {"error": "Campaign not found"}

    cd = dict(campaign)
    sent = cd["total_sent"] or 0
    delivered = cd["total_delivered"] or 0
    opened = cd["total_opened"] or 0
    clicked = cd["total_clicked"] or 0

    cd["delivery_rate"] = round((delivered / sent * 100) if sent > 0 else 0, 1)
    cd["open_rate"] = round((opened / delivered * 100) if delivered > 0 else 0, 1)
    cd["click_rate"] = round((clicked / opened * 100) if opened > 0 else 0, 1)

    # Delivery funnel
    cd["funnel"] = [
        {"stage": "Sent", "count": sent},
        {"stage": "Delivered", "count": delivered},
        {"stage": "Opened", "count": opened},
        {"stage": "Clicked", "count": clicked},
    ]

    # Communication status timeline
    timeline_cursor = await db.execute("""
        SELECT status, COUNT(*) as count
        FROM communications WHERE campaign_id = ?
        GROUP BY status
    """, (campaign_id,))
    cd["status_breakdown"] = {r[0]: r[1] for r in await timeline_cursor.fetchall()}

    # Per-customer breakdown
    cust_cursor = await db.execute("""
        SELECT co.*, cu.name as customer_name, cu.email
        FROM communications co
        JOIN customers cu ON co.customer_id = cu.id
        WHERE co.campaign_id = ?
        ORDER BY co.status DESC
    """, (campaign_id,))
    cd["communications"] = [dict(r) for r in await cust_cursor.fetchall()]

    return cd
