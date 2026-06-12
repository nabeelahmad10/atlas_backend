"""
Seed data generator for the CRM database.
Creates 50 realistic customers for a fashion/lifestyle D2C brand with purchase history.
"""

import asyncio
import aiosqlite
import random
import json
from datetime import datetime, timedelta
from database import DATABASE_PATH, init_db

# ─── Realistic Data Pools ──────────────────────────────────────

FIRST_NAMES_F = [
    "Aaradhya", "Priya", "Sneha", "Ananya", "Diya", "Kavya", "Meera", "Isha",
    "Riya", "Tanvi", "Neha", "Pooja", "Shreya", "Aisha", "Sakshi", "Nikita",
    "Aditi", "Simran", "Kriti", "Zara"
]

FIRST_NAMES_M = [
    "Arjun", "Rohan", "Vihaan", "Aditya", "Kabir", "Dev", "Ishaan", "Reyansh",
    "Arnav", "Dhruv", "Karan", "Aarav", "Vivaan", "Sahil", "Nikhil", "Rahul",
    "Ayaan", "Shaurya", "Yash", "Kartik"
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Singh", "Kumar", "Mehta", "Joshi", "Reddy",
    "Nair", "Kapoor", "Malhotra", "Chatterjee", "Desai", "Iyer", "Bose",
    "Agarwal", "Verma", "Khanna", "Chopra", "Banerjee"
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune",
    "Kolkata", "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Kochi",
    "Goa", "Indore", "Noida"
]

# Product catalog for a fashion/lifestyle brand called "Atlas"
PRODUCTS = {
    "Winter Collection": [
        ("Cashmere Sweater", 3499, 5999),
        ("Wool Overcoat", 7999, 12999),
        ("Thermal Jacket", 4999, 8999),
        ("Fleece Hoodie", 1999, 3499),
        ("Knit Beanie", 599, 1299),
        ("Leather Gloves", 1499, 2999),
    ],
    "Summer Collection": [
        ("Linen Shirt", 1499, 2999),
        ("Cotton Maxi Dress", 2499, 4999),
        ("Beach Shorts", 999, 1999),
        ("Sundress", 1999, 3999),
        ("Crop Top", 799, 1599),
        ("Floral Kaftan", 2999, 5499),
    ],
    "Accessories": [
        ("Leather Tote Bag", 3999, 6999),
        ("Silk Scarf", 1299, 2499),
        ("Aviator Sunglasses", 2499, 4999),
        ("Statement Watch", 5999, 11999),
        ("Pearl Earrings", 999, 2499),
        ("Chain Necklace", 1499, 3499),
    ],
    "Footwear": [
        ("Chelsea Boots", 4999, 8999),
        ("White Sneakers", 2999, 5499),
        ("Stiletto Heels", 3499, 6999),
        ("Leather Loafers", 2999, 4999),
        ("Canvas Slip-Ons", 1299, 2499),
        ("Ankle Boots", 3999, 6999),
    ],
    "Basics": [
        ("Organic Cotton Tee", 699, 1499),
        ("Slim Fit Jeans", 1999, 3499),
        ("Classic Polo", 1299, 2499),
        ("Joggers", 1499, 2999),
        ("Tank Top", 499, 999),
        ("Chino Pants", 1799, 3299),
    ],
}

TAGS_POOL = [
    "high-value", "frequent-buyer", "new-customer", "at-risk", "dormant",
    "vip", "deal-seeker", "brand-loyal", "seasonal-buyer", "impulse-buyer"
]


def generate_email(first, last):
    """Generate a realistic email address."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
    sep = random.choice([".", "_", ""])
    suffix = random.choice(["", str(random.randint(1, 99))])
    return f"{first.lower()}{sep}{last.lower()}{suffix}@{random.choice(domains)}"


def generate_phone():
    """Generate an Indian phone number."""
    return f"+91{random.randint(7000000000, 9999999999)}"


def assign_tags(total_spent, total_orders, days_since_last):
    """Intelligently assign tags based on customer behavior."""
    tags = []
    if total_spent > 30000:
        tags.append("high-value")
    if total_spent > 50000:
        tags.append("vip")
    if total_orders > 8:
        tags.append("frequent-buyer")
    if total_orders <= 2:
        tags.append("new-customer")
    if days_since_last > 120:
        tags.append("dormant")
    elif days_since_last > 60:
        tags.append("at-risk")
    if total_orders > 3 and total_spent / total_orders < 2000:
        tags.append("deal-seeker")
    return tags if tags else [random.choice(["brand-loyal", "seasonal-buyer"])]


async def seed():
    """Main seeding function."""
    await init_db()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if already seeded
        cursor = await db.execute("SELECT COUNT(*) FROM customers")
        count = (await cursor.fetchone())[0]
        if count > 0:
            print(f"[SKIP] Database already has {count} customers. Skipping seed.")
            return

        print("[SEED] Seeding database with 50 customers...")

        now = datetime.now()
        customers_data = []
        used_emails = set()

        for i in range(50):
            is_female = random.random() < 0.55
            first = random.choice(FIRST_NAMES_F if is_female else FIRST_NAMES_M)
            last = random.choice(LAST_NAMES)
            name = f"{first} {last}"

            # Guarantee unique email using index
            domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
            email = f"{first.lower()}.{last.lower()}{i}@{domains[i % len(domains)]}"
            while email in used_emails:
                email = f"{first.lower()}{random.randint(100,999)}@{random.choice(domains)}"
            used_emails.add(email)

            phone = generate_phone()
            age = random.randint(18, 55)
            gender = "Female" if is_female else "Male"
            city = random.choice(CITIES)

            # Varied join dates (6 months to 3 years ago)
            days_ago = random.randint(60, 1095)
            joined_at = (now - timedelta(days=days_ago)).strftime("%Y-%m-%d")

            customers_data.append({
                "name": name,
                "email": email,
                "phone": phone,
                "age": age,
                "gender": gender,
                "city": city,
                "joined_at": joined_at,
            })

        # Insert customers
        for c in customers_data:
            await db.execute(
                """INSERT INTO customers (name, email, phone, age, gender, city, joined_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (c["name"], c["email"], c["phone"], c["age"], c["gender"], c["city"], c["joined_at"])
            )
        await db.commit()

        # Generate orders for each customer
        print("[ORDERS] Generating purchase history...")
        total_orders_generated = 0

        for cust_id in range(1, 51):
            c = customers_data[cust_id - 1]
            joined = datetime.strptime(c["joined_at"], "%Y-%m-%d")
            days_since_join = (now - joined).days

            # Customer archetype determines order frequency
            archetype = random.choice(["whale", "regular", "occasional", "one-timer"])
            if archetype == "whale":
                num_orders = random.randint(10, 20)
            elif archetype == "regular":
                num_orders = random.randint(5, 10)
            elif archetype == "occasional":
                num_orders = random.randint(2, 5)
            else:
                num_orders = random.randint(1, 2)

            total_spent = 0
            last_order_date = None

            # Preferred categories (some customers have affinities)
            preferred_cats = random.sample(list(PRODUCTS.keys()), k=random.randint(1, 3))

            for _ in range(num_orders):
                # Pick category (70% from preferred, 30% random)
                if random.random() < 0.7:
                    category = random.choice(preferred_cats)
                else:
                    category = random.choice(list(PRODUCTS.keys()))

                product_name, min_price, max_price = random.choice(PRODUCTS[category])
                amount = round(random.uniform(min_price, max_price), 2)
                quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]

                # Order date between join date and now
                order_days_ago = random.randint(0, days_since_join)
                ordered_at = (now - timedelta(days=order_days_ago)).strftime("%Y-%m-%d %H:%M:%S")

                await db.execute(
                    """INSERT INTO orders (customer_id, product_name, category, amount, quantity, ordered_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (cust_id, product_name, category, amount * quantity, quantity, ordered_at)
                )

                total_spent += amount * quantity
                if last_order_date is None or ordered_at > last_order_date:
                    last_order_date = ordered_at
                total_orders_generated += 1

            # Calculate tags, health score, and status
            days_since_last = (now - datetime.strptime(last_order_date, "%Y-%m-%d %H:%M:%S")).days if last_order_date else 999
            tags = assign_tags(total_spent, num_orders, days_since_last)
            
            health_score = max(0, min(100, int((total_spent / 1000) * 1.5 + num_orders * 5 - days_since_last * 0.1)))
            if health_score >= 80:
                status = "VIP Loyal Customer"
            elif health_score >= 50:
                status = "Active Purchaser"
            elif health_score >= 20:
                status = "At Risk"
            else:
                status = "Likely To Churn"

            # Update customer aggregates
            await db.execute(
                """UPDATE customers SET total_spent=?, total_orders=?, last_order_date=?, tags=?, health_score=?, status=?
                   WHERE id=?""",
                (round(total_spent, 2), num_orders, last_order_date, json.dumps(tags), health_score, status, cust_id)
            )

        await db.commit()
        print(f"[OK] Seeded 50 customers with {total_orders_generated} orders")

        # Print some stats
        cursor = await db.execute("SELECT AVG(total_spent), MAX(total_spent), SUM(total_orders) FROM customers")
        row = await cursor.fetchone()
        print(f"[STATS] Avg spend: Rs.{row[0]:.0f} | Max spend: Rs.{row[1]:.0f} | Total orders: {row[2]}")


if __name__ == "__main__":
    asyncio.run(seed())
