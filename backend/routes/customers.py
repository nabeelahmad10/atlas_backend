"""
Customer routes — fetch, list, and search customers.
"""

from fastapi import APIRouter, Depends, Query
import aiosqlite
import json
from database import get_db

router = APIRouter(prefix="/api/customers", tags=["Customers"])


@router.get("")
async def list_customers(
    search: str = Query(None, description="Search by name or email"),
    city: str = Query(None),
    tag: str = Query(None),
    min_spent: float = Query(None),
    max_spent: float = Query(None),
    sort_by: str = Query("total_spent", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    limit: int = Query(50),
    offset: int = Query(0),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all customers with optional filtering and sorting."""
    query = "SELECT * FROM customers WHERE 1=1"
    params = []

    if search:
        query += " AND (name LIKE ? OR email LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if city:
        query += " AND city = ?"
        params.append(city)

    if tag:
        query += " AND tags LIKE ?"
        params.append(f'%"{tag}"%')

    if min_spent is not None:
        query += " AND total_spent >= ?"
        params.append(min_spent)

    if max_spent is not None:
        query += " AND total_spent <= ?"
        params.append(max_spent)

    # Validate sort field
    allowed_sorts = ["total_spent", "total_orders", "name", "joined_at", "last_order_date", "age"]
    if sort_by not in allowed_sorts:
        sort_by = "total_spent"
    sort_order = "ASC" if sort_order.lower() == "asc" else "DESC"
    query += f" ORDER BY {sort_by} {sort_order} LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # Get total count
    count_query = "SELECT COUNT(*) FROM customers WHERE 1=1"
    count_params = []
    if search:
        count_query += " AND (name LIKE ? OR email LIKE ?)"
        count_params.extend([f"%{search}%", f"%{search}%"])
    if city:
        count_query += " AND city = ?"
        count_params.append(city)

    count_cursor = await db.execute(count_query, count_params)
    total = (await count_cursor.fetchone())[0]

    customers = []
    for row in rows:
        customer = dict(row)
        customer["tags"] = json.loads(customer.get("tags", "[]"))
        customers.append(customer)

    return {"customers": customers, "total": total, "limit": limit, "offset": offset}


@router.get("/stats")
async def customer_stats(db: aiosqlite.Connection = Depends(get_db)):
    """Get aggregate customer statistics."""
    cursor = await db.execute("""
        SELECT
            COUNT(*) as total_customers,
            ROUND(AVG(total_spent), 2) as avg_spent,
            ROUND(MAX(total_spent), 2) as max_spent,
            ROUND(SUM(total_spent), 2) as total_revenue,
            SUM(total_orders) as total_orders,
            COUNT(CASE WHEN total_orders >= 5 THEN 1 END) as frequent_buyers,
            COUNT(CASE WHEN julianday('now') - julianday(last_order_date) > 90 THEN 1 END) as dormant_customers
        FROM customers
    """)
    row = await cursor.fetchone()
    return dict(row)


@router.get("/cities")
async def get_cities(db: aiosqlite.Connection = Depends(get_db)):
    """Get distinct cities for filtering."""
    cursor = await db.execute("SELECT DISTINCT city FROM customers ORDER BY city")
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


@router.get("/{customer_id}")
async def get_customer(customer_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Get a single customer with their order history."""
    cursor = await db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
    customer = await cursor.fetchone()
    if not customer:
        return {"error": "Customer not found"}, 404

    customer_dict = dict(customer)
    customer_dict["tags"] = json.loads(customer_dict.get("tags", "[]"))

    # Get orders
    order_cursor = await db.execute(
        "SELECT * FROM orders WHERE customer_id = ? ORDER BY ordered_at DESC",
        (customer_id,)
    )
    orders = await order_cursor.fetchall()
    customer_dict["orders"] = [dict(o) for o in orders]

    # Get category breakdown
    cat_cursor = await db.execute(
        """SELECT category, COUNT(*) as count, ROUND(SUM(amount), 2) as total
           FROM orders WHERE customer_id = ? GROUP BY category ORDER BY total DESC""",
        (customer_id,)
    )
    categories = await cat_cursor.fetchall()
    customer_dict["category_breakdown"] = [dict(c) for c in categories]

    return customer_dict
