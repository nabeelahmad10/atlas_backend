"""
Segment routes — create, list, and manage audience segments.
"""

from fastapi import APIRouter, Depends
import aiosqlite
import json
from database import get_db
from models import SegmentCreate

router = APIRouter(prefix="/api/segments", tags=["Segments"])


@router.get("")
async def list_segments(db: aiosqlite.Connection = Depends(get_db)):
    """List all segments."""
    cursor = await db.execute("SELECT * FROM segments ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    segments = []
    for row in rows:
        seg = dict(row)
        seg["rules_json"] = json.loads(seg.get("rules_json", "{}"))
        segments.append(seg)
    return {"segments": segments}


@router.post("")
async def create_segment(segment: SegmentCreate, db: aiosqlite.Connection = Depends(get_db)):
    """Create a new segment with specified customer IDs."""
    cursor = await db.execute(
        """INSERT INTO segments (name, description, rules_json, customer_count, created_by)
           VALUES (?, ?, ?, ?, ?)""",
        (
            segment.name,
            segment.description,
            segment.rules_json,
            len(segment.customer_ids),
            "manual",
        )
    )
    segment_id = cursor.lastrowid

    # Link customers to segment
    for cid in segment.customer_ids:
        await db.execute(
            "INSERT OR IGNORE INTO segment_customers (segment_id, customer_id) VALUES (?, ?)",
            (segment_id, cid)
        )

    await db.commit()

    return {
        "id": segment_id,
        "name": segment.name,
        "description": segment.description,
        "customer_count": len(segment.customer_ids),
        "created_by": "manual",
    }


@router.get("/{segment_id}")
async def get_segment(segment_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get segment details with its customers."""
    cursor = await db.execute("SELECT * FROM segments WHERE id = ?", (segment_id,))
    segment = await cursor.fetchone()
    if not segment:
        return {"error": "Segment not found"}

    seg = dict(segment)
    seg["rules_json"] = json.loads(seg.get("rules_json", "{}"))

    # Get customers in this segment
    cust_cursor = await db.execute(
        """SELECT c.* FROM customers c
           JOIN segment_customers sc ON c.id = sc.customer_id
           WHERE sc.segment_id = ?
           ORDER BY c.total_spent DESC""",
        (segment_id,)
    )
    customers = await cust_cursor.fetchall()
    seg["customers"] = []
    for c in customers:
        cd = dict(c)
        cd["tags"] = json.loads(cd.get("tags", "[]"))
        seg["customers"].append(cd)

    return seg


@router.delete("/{segment_id}")
async def delete_segment(segment_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Delete a segment."""
    await db.execute("DELETE FROM segment_customers WHERE segment_id = ?", (segment_id,))
    await db.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
    await db.commit()
    return {"message": "Segment deleted"}
