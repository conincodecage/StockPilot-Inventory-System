"""Multi-Branch Inventory, Billing & Sales Analytics System.

Run locally with: python app.py
The application stores all business data in Oracle; Python never substitutes SQLite.
"""
from __future__ import annotations
import os
from datetime import datetime
from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, flash, g
from dotenv import load_dotenv
import oracledb
from db import get_db, close_db, fetch_all, fetch_one, DatabaseNotConfiguredError
from models import product_from_row
from analytics import line_chart, category_chart, branch_stock_chart, summary_stats

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-development-key-change-me")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024
ACTOR_ID = int(os.getenv("APP_ACTOR_ID", "1"))


@app.teardown_appcontext
def teardown_db(exception=None):
    close_db(exception)


@app.template_filter("money")
def money(value):
    try:
        return f"₹{float(value or 0):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


@app.template_filter("number")
def number(value):
    try:
        return f"{int(value or 0):,}"
    except (TypeError, ValueError):
        return "0"


def setup_message(error):
    text = str(error)
    if isinstance(error, DatabaseNotConfiguredError):
        return text
    return f"Could not connect to Oracle. Check that Oracle Database is running and ORACLE_DSN, ORACLE_USER and ORACLE_PASSWORD in .env are correct. Oracle says: {text}"


@app.errorhandler(DatabaseNotConfiguredError)
@app.errorhandler(oracledb.Error)
def database_problem(error):
    return render_template("setup.html", page_title="Connect Oracle", error=setup_message(error)), 503


@app.route("/")
def dashboard():
    stats = fetch_one("""
        SELECT
          (SELECT COUNT(*) FROM products WHERE is_active = 'Y') AS active_products,
          (SELECT COUNT(*) FROM branches WHERE is_active = 'Y') AS active_branches,
          (SELECT NVL(SUM(quantity), 0) FROM inventory_stock) AS stock_units,
          (SELECT NVL(SUM(total_amount), 0) FROM sales
             WHERE status = 'COMPLETED' AND sold_at >= TRUNC(SYSDATE, 'MM')) AS month_revenue
        FROM dual
    """) or {}
    low_stock = fetch_all("""
        SELECT branch_name, sku, product_name, quantity, reorder_level, category_name
        FROM v_inventory_overview
        WHERE is_active = 'Y' AND quantity <= reorder_level
        ORDER BY quantity ASC, product_name
        FETCH FIRST 7 ROWS ONLY
    """)
    trend = fetch_all("""
        SELECT TRUNC(sold_at) AS sale_day, SUM(total_amount) AS revenue
        FROM sales
        WHERE status = 'COMPLETED' AND sold_at >= TRUNC(SYSDATE) - 6
        GROUP BY TRUNC(sold_at)
        ORDER BY sale_day
    """)
    recent = fetch_all("""
        SELECT s.sale_id, b.branch_name, c.customer_name,
               s.total_amount, s.status, s.sold_at,
               (SELECT COUNT(*) FROM sale_items i WHERE i.sale_id = s.sale_id) AS item_count
        FROM sales s
        JOIN branches b ON b.branch_id = s.branch_id
        LEFT JOIN customers c ON c.customer_id = s.customer_id
        ORDER BY s.sale_id DESC FETCH FIRST 6 ROWS ONLY
    """)
    chart = line_chart(trend, "Revenue · last 7 days")
    return render_template("dashboard.html", page_title="Overview", stats=stats, low_stock=low_stock,
                           recent=recent, trend_chart=chart)


@app.route("/products", methods=["GET", "POST"])
def products():
    if request.method == "POST":
        conn = get_db()
        try:
            sku = request.form.get("sku", "").strip().upper()
            name = request.form.get("name", "").strip()
            category_id = int(request.form.get("category_id", "0"))
            supplier_raw = request.form.get("supplier_id", "").strip()
            supplier_id = int(supplier_raw) if supplier_raw else None
            unit_price = Decimal(request.form.get("unit_price", "0"))
            product_type = request.form.get("product_type", "STANDARD").upper()
            expiry_raw = request.form.get("expiry_date", "").strip()
            expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d") if expiry_raw else None
            reorder_level = int(request.form.get("reorder_level", "5"))
            if not sku or not name or unit_price < 0 or reorder_level < 0:
                raise ValueError("Enter a SKU, name, valid price and non-negative reorder level.")
            if product_type == "PERISHABLE" and expiry_date is None:
                raise ValueError("Perishable products need an expiry date.")
            with conn.cursor() as cursor:
                out_id = cursor.var(oracledb.DB_TYPE_NUMBER)
                cursor.callproc("INVENTORY_PKG.CREATE_PRODUCT", [sku, name, category_id, supplier_id,
                    unit_price, product_type, expiry_date, reorder_level, out_id])
                product_id = int(out_id.getvalue())
            conn.commit()
            flash(f"Product created. Product ID: {product_id}. Opening stock is set to zero for each branch.", "success")
            return redirect(url_for("products"))
        except (ValueError, oracledb.Error) as exc:
            conn.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else f"Product was not saved. Check SKU uniqueness and the selected category/supplier. Details: {exc}", "error")
            return redirect(url_for("products"))
    categories = fetch_all("SELECT category_id, category_name FROM categories ORDER BY category_name")
    suppliers = fetch_all("SELECT supplier_id, supplier_name FROM suppliers WHERE is_active = 'Y' ORDER BY supplier_name")
    rows = fetch_all("""
        SELECT p.product_id, p.sku, p.name, c.category_name, sp.supplier_name,
               p.unit_price, p.product_type, p.expiry_date, p.reorder_level, p.is_active
        FROM products p
        JOIN categories c ON c.category_id = p.category_id
        LEFT JOIN suppliers sp ON sp.supplier_id = p.supplier_id
        ORDER BY p.product_id DESC
    """)
    product_models = [product_from_row(row) for row in rows]
    return render_template("products.html", page_title="Product catalogue", products=product_models,
                           categories=categories, suppliers=suppliers)


@app.route("/inventory", methods=["GET", "POST"])
def inventory():
    if request.method == "POST":
        conn = get_db()
        try:
            branch_id = int(request.form.get("branch_id", "0"))
            product_id = int(request.form.get("product_id", "0"))
            delta = int(request.form.get("quantity_delta", "0"))
            reason = request.form.get("reason", "Manual stock adjustment").strip() or "Manual stock adjustment"
            if delta == 0:
                raise ValueError("The stock change must not be zero.")
            with conn.cursor() as cursor:
                cursor.callproc("INVENTORY_PKG.ADJUST_STOCK", [branch_id, product_id, delta, reason, ACTOR_ID])
            conn.commit()
            flash(f"Stock updated by {delta:+d} units. The movement and audit trail were recorded by PL/SQL.", "success")
        except (ValueError, oracledb.Error) as exc:
            conn.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else f"Stock was not changed. Check branch, product and available stock. Details: {exc}", "error")
        return redirect(url_for("inventory", branch_id=request.form.get("branch_id", "")))

    branches = fetch_all("SELECT branch_id, branch_code, branch_name FROM branches WHERE is_active='Y' ORDER BY branch_name")
    products_list = fetch_all("SELECT product_id, sku, name FROM products WHERE is_active='Y' ORDER BY name")
    branch_arg = request.args.get("branch_id", "").strip()
    search = request.args.get("q", "").strip()
    branch_id = int(branch_arg) if branch_arg.isdigit() else None
    rows = fetch_all("""
        SELECT branch_id, branch_code, branch_name, product_id, sku, product_name,
               category_name, product_type, expiry_date, unit_price, quantity, reorder_level, is_active
        FROM v_inventory_overview
        WHERE (:branch_id IS NULL OR branch_id = :branch_id)
          AND (:search_text IS NULL OR LOWER(product_name) LIKE '%' || LOWER(:search_text) || '%'
               OR LOWER(sku) LIKE '%' || LOWER(:search_text) || '%')
        ORDER BY branch_name, product_name
    """, {"branch_id": branch_id, "search_text": search or None})
    return render_template("inventory.html", page_title="Branch inventory", branches=branches,
                           products=products_list, rows=rows, selected_branch=branch_id, search=search)


@app.route("/sales", methods=["GET", "POST"])
def sales():
    if request.method == "POST":
        conn = get_db()
        try:
            branch_id = int(request.form.get("branch_id", "0"))
            customer_name = request.form.get("customer_name", "").strip()
            customer_email = request.form.get("customer_email", "").strip() or None
            product_ids = request.form.getlist("product_id")
            quantities = request.form.getlist("quantity")
            line_items = []
            for product_raw, qty_raw in zip(product_ids, quantities):
                if not product_raw.strip() and not qty_raw.strip():
                    continue
                product_id, quantity = int(product_raw), int(qty_raw)
                if product_id <= 0 or quantity <= 0:
                    raise ValueError("Choose a product and a positive quantity for every sale line.")
                line_items.append((product_id, quantity))
            if not line_items:
                raise ValueError("Add at least one product to the bill.")
            with conn.cursor() as cursor:
                customer_id = None
                if customer_name:
                    customer_var = cursor.var(oracledb.DB_TYPE_NUMBER)
                    cursor.execute("""INSERT INTO customers (customer_name, email)
                                      VALUES (:name, :email) RETURNING customer_id INTO :out_id""",
                                   {"name": customer_name, "email": customer_email, "out_id": customer_var})
                    customer_id = int(customer_var.getvalue())
                sale_var = cursor.var(oracledb.DB_TYPE_NUMBER)
                cursor.execute("""INSERT INTO sales (branch_id, customer_id, status, total_amount)
                                  VALUES (:branch_id, :customer_id, 'PENDING', 0)
                                  RETURNING sale_id INTO :out_id""",
                               {"branch_id": branch_id, "customer_id": customer_id, "out_id": sale_var})
                sale_id = int(sale_var.getvalue())
                for product_id, quantity in line_items:
                    cursor.execute("SELECT unit_price FROM products WHERE product_id=:id AND is_active='Y'", {"id": product_id})
                    row = cursor.fetchone()
                    if row is None:
                        raise ValueError(f"Product ID {product_id} is missing or inactive.")
                    cursor.execute("""INSERT INTO sale_items (sale_id, product_id, quantity, unit_price)
                                      VALUES (:sale_id, :product_id, :quantity, :unit_price)""",
                                   {"sale_id": sale_id, "product_id": product_id,
                                    "quantity": quantity, "unit_price": row[0]})
                # PL/SQL locks stock rows, validates quantities, updates stock and finalizes the bill atomically.
                cursor.callproc("INVENTORY_PKG.FINALIZE_SALE", [sale_id, ACTOR_ID])
            conn.commit()
            flash(f"Bill #{sale_id} completed. Stock deduction, total calculation and audit logging ran in PL/SQL.", "success")
        except (ValueError, oracledb.Error) as exc:
            conn.rollback()
            flash(str(exc) if isinstance(exc, ValueError) else f"Bill was rolled back; no partial stock deduction was committed. Details: {exc}", "error")
        return redirect(url_for("sales"))

    branches = fetch_all("SELECT branch_id, branch_name FROM branches WHERE is_active='Y' ORDER BY branch_name")
    products_list = fetch_all("SELECT product_id, sku, name, unit_price FROM products WHERE is_active='Y' ORDER BY name")
    recent = fetch_all("""
        SELECT s.sale_id, b.branch_name, c.customer_name, s.total_amount, s.status,
               s.sold_at, (SELECT COUNT(*) FROM sale_items i WHERE i.sale_id=s.sale_id) AS item_count
        FROM sales s JOIN branches b ON b.branch_id=s.branch_id
        LEFT JOIN customers c ON c.customer_id=s.customer_id
        ORDER BY s.sale_id DESC FETCH FIRST 20 ROWS ONLY
    """)
    return render_template("sales.html", page_title="Billing & sales", branches=branches,
                           products=products_list, recent=recent)


@app.route("/reports")
def reports():
    trend = fetch_all("""
        SELECT TRUNC(sold_at) AS sale_day, SUM(total_amount) AS revenue
        FROM sales WHERE status='COMPLETED' AND sold_at >= TRUNC(SYSDATE)-29
        GROUP BY TRUNC(sold_at) ORDER BY sale_day
    """)
    category_rows = fetch_all("""
        SELECT c.category_name,
               SUM(CASE WHEN s.status='COMPLETED' THEN si.line_total ELSE 0 END) AS revenue
        FROM categories c
        LEFT JOIN products p ON p.category_id=c.category_id
        LEFT JOIN sale_items si ON si.product_id=p.product_id
        LEFT JOIN sales s ON s.sale_id=si.sale_id
        GROUP BY c.category_name ORDER BY revenue DESC
    """)
    branch_rows = fetch_all("""
        SELECT b.branch_name, NVL(SUM(i.quantity),0) AS units
        FROM branches b LEFT JOIN inventory_stock i ON i.branch_id=b.branch_id
        GROUP BY b.branch_name ORDER BY b.branch_name
    """)
    top_products = fetch_all("""
        SELECT p.sku, p.name, SUM(si.quantity) AS units_sold, SUM(si.line_total) AS revenue
        FROM sale_items si JOIN sales s ON s.sale_id=si.sale_id
        JOIN products p ON p.product_id=si.product_id
        WHERE s.status='COMPLETED'
        GROUP BY p.sku, p.name ORDER BY units_sold DESC, revenue DESC
        FETCH FIRST 8 ROWS ONLY
    """)
    trend_chart = line_chart(trend, "Revenue · last 30 days")
    cat_chart = category_chart(category_rows)
    stock_chart = branch_stock_chart(branch_rows)
    stats = summary_stats(trend)
    # Use the database as the source of truth; Pandas/NumPy clean and summarize the returned records.
    return render_template("reports.html", page_title="Sales analytics", trend_chart=trend_chart,
                           category_chart=cat_chart, stock_chart=stock_chart, stats=stats,
                           category_rows=category_rows, top_products=top_products)


@app.route("/activity")
def activity():
    movements = fetch_all("""
        SELECT m.movement_id, m.created_at, m.movement_type, m.quantity_delta,
               b.branch_name, p.sku, p.name AS product_name,
               m.reference_type, m.reference_id, m.note, u.username
        FROM stock_movements m
        JOIN branches b ON b.branch_id = m.branch_id
        JOIN products p ON p.product_id = m.product_id
        LEFT JOIN app_users u ON u.user_id = m.created_by
        ORDER BY m.movement_id DESC FETCH FIRST 25 ROWS ONLY
    """)
    audits = fetch_all("""
        SELECT audit_id, event_time, actor, action_name, entity_name, entity_id, details
        FROM audit_log ORDER BY audit_id DESC FETCH FIRST 25 ROWS ONLY
    """)
    totals = fetch_one("""
        SELECT (SELECT COUNT(*) FROM stock_movements) AS movement_count,
               (SELECT COUNT(*) FROM audit_log) AS audit_count,
               (SELECT NVL(SUM(CASE WHEN quantity_delta > 0 THEN quantity_delta ELSE 0 END),0)
                  FROM stock_movements) AS units_received,
               (SELECT NVL(ABS(SUM(CASE WHEN quantity_delta < 0 THEN quantity_delta ELSE 0 END)),0)
                  FROM stock_movements) AS units_removed
        FROM dual
    """) or {}
    return render_template("activity.html", page_title="Audit trail", movements=movements,
                           audits=audits, totals=totals)


@app.route("/health")
def health():
    row = fetch_one("SELECT 'OK' AS status, SYSTIMESTAMP AS database_time FROM dual") or {}
    return {"application": "ok", "database": row.get("status", "unknown"), "database_time": str(row.get("database_time", ""))}


if __name__ == "__main__":
    # Localhost only. For a college demo, open http://127.0.0.1:5000 in a browser.
    app.run(host="127.0.0.1", port=5000, debug=True)
