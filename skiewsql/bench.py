"""bench.py — the view library (canonical skill-driven views) and the *sequential* question stream over the retail DB. Each question carries the top-level views it needs (`wants`), a final SELECT (placeholders {view} replaced by the actually-chosen view name), and an independent gold SQL over base tables for execution-accuracy. The library bodies stand in for what the AV-SQL CTEAgent/LLM would emit. Here they are authored once so that the *graph mechanism* (retrieve / reuse / generate / compose / validate) can be measured against real execution results — with no LLM or network."""
from skiewsql.core import ViewSpec, ViewRequest

# --------------------------------------------------------------------------- #
# View library (name -> canonical ViewSpec). depends_on wires the graph edges.
# --------------------------------------------------------------------------- #
LIBRARY = {
    "completed_orders": ViewSpec(
        name="completed_orders", category="SEM",
        body_sql="""SELECT order_id, customer_id, store_id, order_date, amount, status
FROM orders
WHERE status = 'completed'""",
        source_tables=["orders"],
        output_columns=["order_id", "customer_id", "store_id", "order_date", "amount", "status"],
        grain=["order_id"], semantic_filters={"status": "completed"},
        description="completed orders only: valid revenue-bearing transactions filtered to status = completed. Reusable for revenue, spend and order-count questions about completed orders",
    ),
    "customer_yearly_spend": ViewSpec(
        name="customer_yearly_spend", category="AGG",
        body_sql="""SELECT customer_id,
       CAST(strftime('%Y', order_date) AS INTEGER) AS order_year,
       SUM(amount) AS total_spend
FROM completed_orders
GROUP BY customer_id, CAST(strftime('%Y', order_date) AS INTEGER)""",
        source_tables=["orders"],
        output_columns=["customer_id", "order_year", "total_spend"],
        grain=["customer_id", "order_year"], semantic_filters={"status": "completed"},
        depends_on=["completed_orders"],
        description="total completed spend per customer per year. Reusable for top spender by year, average annual spend, year over year spend growth, above-average spenders",
    ),
    "monthly_sales": ViewSpec(
        name="monthly_sales", category="AGG",
        body_sql="""SELECT store_id,
       strftime('%Y-%m', order_date) AS month,
       SUM(amount) AS revenue
FROM orders
GROUP BY store_id, strftime('%Y-%m', order_date)""",
        source_tables=["orders"],
        output_columns=["store_id", "month", "revenue"],
        grain=["store_id", "month"], semantic_filters={},
        description="monthly revenue per store across all orders of any status. Reusable for monthly revenue trends, revenue by store, top stores, region rollups",
    ),
    "monthly_sales_by_region": ViewSpec(
        name="monthly_sales_by_region", category="AGG",
        body_sql="""SELECT s.region AS region, m.month AS month, SUM(m.revenue) AS revenue
FROM monthly_sales m JOIN stores s ON m.store_id = s.store_id
GROUP BY s.region, m.month""",
        source_tables=["orders", "stores"],
        output_columns=["region", "month", "revenue"],
        grain=["region", "month"], semantic_filters={},
        depends_on=["monthly_sales"],
        description="monthly revenue per region across all orders, rolled up from monthly_sales joined to stores",
    ),
    "monthly_completed_sales": ViewSpec(
        name="monthly_completed_sales", category="AGG",
        body_sql="""SELECT store_id,
       strftime('%Y-%m', order_date) AS month,
       SUM(amount) AS revenue
FROM completed_orders
GROUP BY store_id, strftime('%Y-%m', order_date)""",
        source_tables=["orders"],
        output_columns=["store_id", "month", "revenue"],
        grain=["store_id", "month"], semantic_filters={"status": "completed"},
        depends_on=["completed_orders"],
        description="monthly revenue per store from completed orders only. The completed-status counterpart of monthly_sales",
    ),
    "latest_order_per_customer": ViewSpec(
        name="latest_order_per_customer", category="RANK",
        body_sql="""SELECT customer_id, order_id, order_date,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) AS rn
FROM orders""",
        source_tables=["orders"],
        output_columns=["customer_id", "order_id", "order_date", "rn"],
        grain=["customer_id", "order_id"], semantic_filters={},
        description="orders ranked by recency within each customer. Rn = 1 is the latest order. Reusable for latest record per customer and top-k recent orders",
    ),
    "revenue_by_category_month": ViewSpec(
        name="revenue_by_category_month", category="AGG",
        body_sql="""SELECT p.category AS category,
       strftime('%Y-%m', o.order_date) AS month,
       SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN orders o   ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category, strftime('%Y-%m', o.order_date)""",
        source_tables=["order_items", "orders", "products"],
        output_columns=["category", "month", "revenue"],
        grain=["category", "month"], semantic_filters={},
        description="monthly revenue per product category from order line items. Reusable for category trends and category-by-month pivots",
    ),
    "daily_running_revenue": ViewSpec(
        name="daily_running_revenue", category="WIN",
        body_sql="""SELECT d AS order_date, daily_rev,
       SUM(daily_rev) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_total
FROM (SELECT order_date AS d, SUM(amount) AS daily_rev FROM orders GROUP BY order_date)""",
        source_tables=["orders"],
        output_columns=["order_date", "daily_rev", "running_total"],
        grain=["order_date"], semantic_filters={},
        description="daily revenue with a cumulative running total over time across all orders",
    ),
    "employee_hierarchy": ViewSpec(
        name="employee_hierarchy", category="REC",
        body_sql="""SELECT employee_id, manager_id, 0 AS level, CAST(employee_id AS TEXT) AS path
FROM employees WHERE manager_id IS NULL
UNION ALL
SELECT e.employee_id, e.manager_id, eh.level + 1, eh.path || '>' || e.employee_id
FROM employees e JOIN employee_hierarchy eh ON e.manager_id = eh.employee_id""",
        source_tables=["employees"],
        output_columns=["employee_id", "manager_id", "level", "path"],
        grain=["employee_id"], semantic_filters={},
        description="recursive traversal of the employee management hierarchy with depth level and root-to-node path",
    ),
    "cust_elec_not_books": ViewSpec(
        name="cust_elec_not_books", category="SET",
        body_sql="""SELECT DISTINCT o.customer_id AS customer_id
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id
WHERE p.category = 'Electronics'
EXCEPT
SELECT DISTINCT o.customer_id AS customer_id
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id JOIN products p ON oi.product_id = p.product_id
WHERE p.category = 'Books'""",
        source_tables=["orders", "order_items", "products"],
        output_columns=["customer_id"],
        grain=["customer_id"], semantic_filters={},
        description="customers who bought an Electronics product but never a Books product, via set difference of the two cohorts",
    ),
}


def request_for(want: str, text: str = "") -> ViewRequest:
    """Derive the planner sub-goal (request) from the canonical spec it asks for."""
    s = LIBRARY[want]
    return ViewRequest(
        want_name=want, category=s.category,
        required_outputs=list(s.output_columns), required_grain=list(s.grain),
        required_filters=dict(s.semantic_filters),
        text=text or s.description,
    )


# --------------------------------------------------------------------------- #
# Sequential question stream. Each: id, text, wants(list of library keys), final_select (with {key} placeholders), gold_sql, order_sensitive.
# --------------------------------------------------------------------------- #
QUESTIONS = [
    dict(id="Q01", text="Which customer had the highest total completed-order spend in 2025?",
         wants=["customer_yearly_spend"],
         final="SELECT customer_id FROM {customer_yearly_spend} WHERE order_year = 2025 ORDER BY total_spend DESC LIMIT 1",
         gold="""SELECT customer_id FROM (
                   SELECT customer_id, SUM(amount) ts FROM orders
                   WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2025
                   GROUP BY customer_id) ORDER BY ts DESC LIMIT 1""",
         order_sensitive=True),

    dict(id="Q02", text="Which customer had the highest total completed-order spend in 2024?",
         wants=["customer_yearly_spend"],
         final="SELECT customer_id FROM {customer_yearly_spend} WHERE order_year = 2024 ORDER BY total_spend DESC LIMIT 1",
         gold="""SELECT customer_id FROM (
                   SELECT customer_id, SUM(amount) ts FROM orders
                   WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2024
                   GROUP BY customer_id) ORDER BY ts DESC LIMIT 1""",
         order_sensitive=True),

    dict(id="Q03", text="What is the average annual completed-spend per customer?",
         wants=["customer_yearly_spend"],
         final="SELECT customer_id, AVG(total_spend) AS avg_spend FROM {customer_yearly_spend} GROUP BY customer_id",
         gold="""SELECT customer_id, AVG(ts) FROM (
                   SELECT customer_id, CAST(strftime('%Y',order_date) AS INTEGER) y, SUM(amount) ts
                   FROM orders WHERE status='completed' GROUP BY customer_id, y) GROUP BY customer_id""",
         order_sensitive=False),

    dict(id="Q04", text="List customers whose completed spend in 2025 exceeded their 2024 spend.",
         wants=["customer_yearly_spend"],
         final="""SELECT a.customer_id FROM {customer_yearly_spend} a JOIN {customer_yearly_spend} b
                  ON a.customer_id=b.customer_id
                  WHERE a.order_year=2025 AND b.order_year=2024 AND a.total_spend > b.total_spend""",
         gold="""SELECT a.customer_id FROM
                   (SELECT customer_id, SUM(amount) ts FROM orders WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2025 GROUP BY customer_id) a
                   JOIN
                   (SELECT customer_id, SUM(amount) ts FROM orders WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2024 GROUP BY customer_id) b
                   ON a.customer_id=b.customer_id WHERE a.ts > b.ts""",
         order_sensitive=False),

    dict(id="Q05", text="What was the total completed revenue in 2025?",
         wants=["completed_orders"],
         final="SELECT SUM(amount) AS total FROM {completed_orders} WHERE CAST(strftime('%Y', order_date) AS INTEGER)=2025",
         gold="SELECT SUM(amount) FROM orders WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2025",
         order_sensitive=False),

    dict(id="Q06", text="Monthly revenue per store across all orders.",
         wants=["monthly_sales"],
         final="SELECT store_id, month, revenue FROM {monthly_sales}",
         gold="SELECT store_id, strftime('%Y-%m',order_date), SUM(amount) FROM orders GROUP BY store_id, strftime('%Y-%m',order_date)",
         order_sensitive=False),

    dict(id="Q07", text="Monthly revenue per region across all orders.",
         wants=["monthly_sales_by_region"],
         final="SELECT region, month, revenue FROM {monthly_sales_by_region}",
         gold="""SELECT s.region, strftime('%Y-%m',o.order_date), SUM(o.amount)
                 FROM orders o JOIN stores s ON o.store_id=s.store_id
                 GROUP BY s.region, strftime('%Y-%m',o.order_date)""",
         order_sensitive=False),

    dict(id="Q08", text="Total monthly revenue across all stores (all orders).",
         wants=["monthly_sales"],
         final="SELECT month, SUM(revenue) AS revenue FROM {monthly_sales} GROUP BY month",
         gold="SELECT strftime('%Y-%m',order_date), SUM(amount) FROM orders GROUP BY strftime('%Y-%m',order_date)",
         order_sensitive=False),

    dict(id="Q09", text="For each customer, the order_id of their most recent order.",
         wants=["latest_order_per_customer"],
         final="SELECT customer_id, order_id FROM {latest_order_per_customer} WHERE rn=1",
         gold="""SELECT customer_id, order_id FROM (
                   SELECT customer_id, order_id,
                   ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC, order_id DESC) rn
                   FROM orders) WHERE rn=1""",
         order_sensitive=False),

    dict(id="Q10", text="Monthly revenue per product category from line items.",
         wants=["revenue_by_category_month"],
         final="SELECT category, month, revenue FROM {revenue_by_category_month}",
         gold="""SELECT p.category, strftime('%Y-%m',o.order_date), SUM(oi.quantity*oi.unit_price)
                 FROM order_items oi JOIN orders o ON oi.order_id=o.order_id JOIN products p ON oi.product_id=p.product_id
                 GROUP BY p.category, strftime('%Y-%m',o.order_date)""",
         order_sensitive=False),

    dict(id="Q11", text="Customers who bought Electronics but never Books.",
         wants=["cust_elec_not_books"],
         final="SELECT customer_id FROM {cust_elec_not_books}",
         gold="""SELECT DISTINCT o.customer_id FROM orders o JOIN order_items oi ON o.order_id=oi.order_id JOIN products p ON oi.product_id=p.product_id WHERE p.category='Electronics'
                 EXCEPT
                 SELECT DISTINCT o.customer_id FROM orders o JOIN order_items oi ON o.order_id=oi.order_id JOIN products p ON oi.product_id=p.product_id WHERE p.category='Books'""",
         order_sensitive=False),

    dict(id="Q12", text="For each employee, their depth in the management hierarchy.",
         wants=["employee_hierarchy"],
         final="SELECT employee_id, level FROM {employee_hierarchy}",
         gold="""WITH RECURSIVE eh(employee_id, manager_id, level) AS (
                   SELECT employee_id, manager_id, 0 FROM employees WHERE manager_id IS NULL
                   UNION ALL
                   SELECT e.employee_id, e.manager_id, eh.level+1 FROM employees e JOIN eh ON e.manager_id=eh.employee_id)
                 SELECT employee_id, level FROM eh""",
         order_sensitive=False),

    dict(id="Q13", text="Monthly revenue per store from COMPLETED orders only. [negative-reuse trap]",
         wants=["monthly_completed_sales"],
         final="SELECT store_id, month, revenue FROM {monthly_completed_sales}",
         gold="""SELECT store_id, strftime('%Y-%m',order_date), SUM(amount) FROM orders WHERE status='completed'
                 GROUP BY store_id, strftime('%Y-%m',order_date)""",
         order_sensitive=False),

    dict(id="Q14", text="Daily revenue with a cumulative running total (all orders).",
         wants=["daily_running_revenue"],
         final="SELECT order_date, daily_rev, running_total FROM {daily_running_revenue}",
         gold="""SELECT d, daily_rev, SUM(daily_rev) OVER (ORDER BY d ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
                 FROM (SELECT order_date d, SUM(amount) daily_rev FROM orders GROUP BY order_date)""",
         order_sensitive=False),

    dict(id="Q15", text="Top 3 stores by total revenue across all orders.",
         wants=["monthly_sales"],
         final="SELECT store_id FROM (SELECT store_id, SUM(revenue) tr FROM {monthly_sales} GROUP BY store_id) ORDER BY tr DESC LIMIT 3",
         gold="SELECT store_id FROM (SELECT store_id, SUM(amount) tr FROM orders GROUP BY store_id) ORDER BY tr DESC LIMIT 3",
         order_sensitive=True),

    dict(id="Q16", text="Customers whose 2025 completed spend is above the 2025 average.",
         wants=["customer_yearly_spend"],
         final="""SELECT customer_id FROM {customer_yearly_spend}
                  WHERE order_year=2025 AND total_spend > (SELECT AVG(total_spend) FROM {customer_yearly_spend} WHERE order_year=2025)""",
         gold="""SELECT customer_id FROM
                   (SELECT customer_id, SUM(amount) ts FROM orders WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2025 GROUP BY customer_id)
                 WHERE ts > (SELECT AVG(ts) FROM (SELECT customer_id, SUM(amount) ts FROM orders WHERE status='completed' AND CAST(strftime('%Y',order_date) AS INTEGER)=2025 GROUP BY customer_id))""",
         order_sensitive=False),
]
