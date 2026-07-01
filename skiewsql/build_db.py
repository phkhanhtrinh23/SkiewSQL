"""
build_db.py — construct a real, deterministic SQLite retail+HR database used to
evaluate the SkiewSQL view graph end to end (no LLM, no network).

The schema is intentionally relational and "joinful" so that skill-driven views
(SEL/SEM, AGG, JOIN, RANK, WIN, RESHAPE, SET, REC) are genuinely reusable across a
sequence of questions. All data is seeded -> identical on every run.
"""
import os
import random
import sqlite3
from datetime import date, timedelta

SEED = 17
DB_DEFAULT = os.path.join(os.path.dirname(__file__), "data", "retail.sqlite")

REGIONS = ["North", "South", "East"]
COUNTRIES = ["Australia", "USA", "UK", "Germany"]
CATEGORIES = ["Electronics", "Books", "Grocery", "Clothing", "Toys"]
STATUSES = ["completed", "completed", "completed", "cancelled", "pending"]  # ~60% completed


def _daterange(start: date, end: date) -> int:
    return (end - start).days


def build(db_path: str = DB_DEFAULT) -> str:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    rng = random.Random(SEED)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE stores (
            store_id   INTEGER PRIMARY KEY,
            store_name TEXT NOT NULL,
            region     TEXT NOT NULL
        );
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            country     TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            category   TEXT NOT NULL,
            unit_price REAL NOT NULL
        );
        CREATE TABLE orders (
            order_id    INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            store_id    INTEGER NOT NULL,
            order_date  TEXT NOT NULL,
            status      TEXT NOT NULL,
            amount      REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (store_id)    REFERENCES stores(store_id)
        );
        CREATE TABLE order_items (
            order_id   INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity   INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            manager_id  INTEGER,
            store_id    INTEGER,
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id),
            FOREIGN KEY (store_id)   REFERENCES stores(store_id)
        );
        """
    )

    # stores
    stores = []
    for sid in range(1, 7):
        stores.append((sid, f"Store_{sid}", REGIONS[(sid - 1) % len(REGIONS)]))
    cur.executemany("INSERT INTO stores VALUES (?,?,?)", stores)

    # customers
    customers = []
    base = date(2021, 1, 1)
    for cid in range(1, 201):
        signup = base + timedelta(days=rng.randint(0, 900))
        customers.append((cid, f"Cust_{cid}", rng.choice(COUNTRIES), signup.isoformat()))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?)", customers)

    # products
    products = []
    for pid in range(1, 31):
        cat = CATEGORIES[(pid - 1) % len(CATEGORIES)]
        products.append((pid, f"Prod_{pid}", cat, round(rng.uniform(5, 500), 2)))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

    # orders + order_items, spanning 2023-01-01 .. 2025-12-31
    start, end = date(2023, 1, 1), date(2025, 12, 31)
    span = _daterange(start, end)
    orders, items = [], []
    oid = 0
    for _ in range(3000):
        oid += 1
        cid = rng.randint(1, 200)
        sid = rng.randint(1, 6)
        odate = start + timedelta(days=rng.randint(0, span))
        status = rng.choice(STATUSES)
        n_items = rng.randint(1, 4)
        amount = 0.0
        for _ in range(n_items):
            pid = rng.randint(1, 30)
            qty = rng.randint(1, 5)
            up = round(rng.uniform(5, 500), 2)
            amount += qty * up
            items.append((oid, pid, qty, up))
        orders.append((oid, cid, sid, odate.isoformat(), status, round(amount, 2)))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?)", items)

    # employees: a 3-level hierarchy per store (1 director -> managers -> staff)
    employees = []
    eid = 0
    eid += 1
    director = eid
    employees.append((director, "Director", None, None))
    for sid in range(1, 7):
        eid += 1
        mgr = eid
        employees.append((mgr, f"Manager_{sid}", director, sid))
        for _ in range(rng.randint(2, 4)):
            eid += 1
            employees.append((eid, f"Staff_{eid}", mgr, sid))
    cur.executemany("INSERT INTO employees VALUES (?,?,?,?)", employees)

    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    p = build()
    con = sqlite3.connect(p)
    cur = con.cursor()
    for t in ["stores", "customers", "products", "orders", "order_items", "employees"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"{t:12s} {n}")
    con.close()
    print("built:", p)
