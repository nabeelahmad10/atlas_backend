"""
Database setup and connection management for the CRM API.
Uses aiosqlite for async SQLite operations.
"""

import aiosqlite
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), "crm.db")


async def get_db():
    """Dependency that provides a database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Initialize database tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                age INTEGER,
                gender TEXT,
                city TEXT,
                joined_at TEXT NOT NULL,
                total_spent REAL DEFAULT 0,
                total_orders INTEGER DEFAULT 0,
                last_order_date TEXT,
                tags TEXT DEFAULT '[]',
                health_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'New',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                quantity INTEGER DEFAULT 1,
                ordered_at TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                rules_json TEXT NOT NULL DEFAULT '{}',
                customer_count INTEGER DEFAULT 0,
                created_by TEXT DEFAULT 'ai',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS segment_customers (
                segment_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                PRIMARY KEY (segment_id, customer_id),
                FOREIGN KEY (segment_id) REFERENCES segments(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                segment_id INTEGER NOT NULL,
                message_template TEXT NOT NULL,
                channel TEXT NOT NULL DEFAULT 'email',
                status TEXT DEFAULT 'draft',
                total_sent INTEGER DEFAULT 0,
                total_delivered INTEGER DEFAULT 0,
                total_failed INTEGER DEFAULT 0,
                total_opened INTEGER DEFAULT 0,
                total_clicked INTEGER DEFAULT 0,
                predicted_outcomes_json TEXT,
                post_analysis_json TEXT,
                scheduled_at TEXT,
                sent_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (segment_id) REFERENCES segments(id)
            );

            CREATE TABLE IF NOT EXISTS communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                sent_at TEXT,
                delivered_at TEXT,
                opened_at TEXT,
                clicked_at TEXT,
                failed_reason TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                communication_id INTEGER NOT NULL,
                payload_json TEXT DEFAULT '{}',
                timestamp TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS ai_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER,
                learning_text TEXT NOT NULL,
                category TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
            CREATE INDEX IF NOT EXISTS idx_orders_category ON orders(category);
            CREATE INDEX IF NOT EXISTS idx_communications_campaign ON communications(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_communications_status ON communications(status);
            CREATE INDEX IF NOT EXISTS idx_segment_customers_segment ON segment_customers(segment_id);
        """)
        await db.commit()
        print("[OK] Database tables initialized")
