# StockPilot — Multi-Branch Inventory, Billing & Sales Analytics

A college project that combines the Python syllabus with Advanced DBMS concepts using **Oracle PL/SQL as the actual database logic layer**. The interface runs as a local website in Chrome/Edge; it does not need a public domain or hosting service for a classroom demo.

## What it does

- Manages a product catalogue, suppliers, categories and standard/perishable product types.
- Tracks stock by branch, highlights products at or below their reorder level, and records stock adjustments.
- Creates multi-line bills, validates available stock, totals each bill and deducts inventory.
- Shows recent bills, low-stock items, month-to-date revenue, category mix, branch stock and sales trends.
- Includes an Audit Trail page for stock movements and trigger/package-generated audit events.
- Uses Oracle constraints, stored package procedures, row locking, triggers, views and audit/movement tables for data integrity.
- Uses Python classes and inheritance (`Product` / `PerishableProduct`), Flask routes, NumPy, Pandas and Matplotlib.

## Architecture

```text
Browser (HTML/CSS/JavaScript)
          |
       Flask app
          |  python-oracledb (thin mode)
          v
  Oracle Database (Free / XE)
          |
  INVENTORY_PKG (PL/SQL)
  - CREATE_PRODUCT
  - ADJUST_STOCK
  - FINALIZE_SALE
          |
  Tables + constraints + triggers + views + audit log
```

The app is intentionally configured to bind to `127.0.0.1`, so it is available only on your computer. **Localhost is the recommended first deployment target.** Hosting it online is optional and would require a securely reachable Oracle database, environment secrets and production server setup.

## Requirements

- Python 3.10 or newer
- Oracle Database Free or Oracle Database XE with a pluggable database open
- SQL Developer or SQL*Plus to run the SQL scripts
- A browser

Oracle connection DSNs commonly look like:

- Oracle Database Free: `localhost:1521/FREEPDB1`
- Oracle XE: `localhost:1521/XEPDB1`

Use the service name matching your own Oracle installation. These examples are not interchangeable on every machine.

## Setup

### 1. Create the Oracle application user

Open SQL Developer or SQL*Plus and connect as `SYSTEM` to the correct pluggable database. Run `sql/00_create_user.sql`. The example password is for a local classroom setup only; change it before using the project anywhere else.

### 2. Create schema, PL/SQL logic, triggers and views

Disconnect from `SYSTEM`; connect as `INVENTORY_APP` to the same PDB. Run these scripts **in order**:

1. `sql/01_schema.sql`
2. `sql/02_inventory_pkg.sql`
3. `sql/03_triggers_views.sql`
4. `sql/04_seed_demo.sql`

Run `04_seed_demo.sql` once. It creates three branches and sample products. It intentionally leaves a few products at low stock so the Restock Watch and stock-adjustment demonstration are visible. In SQL Developer, use **Run Script (F5)** so the `/` PL/SQL terminators are processed correctly. Check for compilation errors before continuing.

### 3. Configure Python

From the project directory, create a virtual environment and install dependencies.

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set `ORACLE_USER`, `ORACLE_PASSWORD` and `ORACLE_DSN` to your real local Oracle connection. The sample uses `INVENTORY_APP`, `ChangeMe_123` and `localhost:1521/FREEPDB1`. If your installation is XE, try `localhost:1521/XEPDB1` if that matches the configured service. Keep `.env` private; it is ignored by Git.

### 4. Run the website

```bash
python app.py
```

Open **http://127.0.0.1:5000**. Keep the terminal window running while you use the site. The `/health` route checks the Oracle connection. If Oracle is not configured, the app displays a database-setup screen instead of pretending to use a different database.

## Demo script for your viva

1. **Dashboard:** point out the active product / branch cards, monthly revenue, low-stock list and Matplotlib revenue trend.
2. **Products:** add a standard product, then try a perishable product without an expiry date. Python validation and the PL/SQL package/table constraint reject invalid data. A successful product gets a zero-stock row for each active branch.
3. **Branch inventory:** inspect the deliberately low USB-C Cable quantity at North Market. Add stock using a positive adjustment; show how the inventory and movement ledger change.
4. **Billing:** create a sale for one or more products. The PL/SQL procedure locks rows with `SELECT ... FOR UPDATE`, checks stock, reduces inventory, calculates totals and writes movement/audit records.
5. **Rollback test:** try to sell 4 USB-C Cables at North Market. The seeded quantity is 3, so the bill should fail. The app rolls back the transaction; there should be no partial stock deduction.
6. **Analytics:** open Analytics and explain how Oracle aggregates are cleaned/summarized using Pandas/NumPy, then charted using Matplotlib.
7. **ADBMS objects:** in SQL Developer, show `INVENTORY_PKG`, `TRG_INVENTORY_STOCK_GUARD`, `TRG_SALE_ITEM_PENDING_ONLY`, `V_INVENTORY_OVERVIEW`, `STOCK_MOVEMENTS`, and `AUDIT_LOG`.

## How this maps to the Python syllabus

| Syllabus area | Used in the project |
|---|---|
| Variables, conditions, loops, functions and data structures | Form validation, row iteration, request handling and chart preparation |
| Classes, inheritance and polymorphism | `models.py`: `Product` and `PerishableProduct` |
| NumPy | Numerical arrays, revenue summaries and chart series |
| Pandas | DataFrame preparation, date/numeric conversion and missing-value handling |
| Matplotlib | Revenue trend, category mix and branch-stock charts |
| Web interface | Flask routes and HTML templates are used instead of Tkinter because this project is a browser-based local website |

## How this maps to Advanced DBMS

- **DBLC / schema design:** separate master, inventory, sales and movement tables with keys and constraints.
- **Active database / triggers:** inventory non-negative guard, sale-line guard and automatic audit triggers.
- **Transaction management / atomicity:** sale creation and `INVENTORY_PKG.FINALIZE_SALE` run in one transaction; application rollback undoes all staged changes when validation fails.
- **Concurrency control:** `SELECT ... FOR UPDATE` locks the sale header and stock rows; inventory is checked after the row lock.
- **Recovery:** commit/rollback semantics are used, and stock movement plus audit history makes changes traceable.
- **Query processing:** reporting aggregates, filters, joins and database views.
- **Access control foundation:** a demo operator / role table is included, but this classroom build does not implement a production login/authorization system.
- **Multi-branch modelling:** stock is maintained separately for each branch and combined in network-wide views.

### Important scope note

Multiple branches inside one Oracle instance are **logical branch separation**, not a physically distributed database across multiple sites. This project demonstrates relevant distributed-database design ideas (branch-local inventory and consolidated reporting) but does not claim to implement multi-node DDBMS replication or distributed commit protocols.

## Troubleshooting

- **DPY-6005 / connection refused:** start Oracle, confirm the PDB is open, and verify host/port/service in `.env`.
- **ORA-01017:** the username or password is wrong, or the app user was created in a different PDB.
- **ORA-00942:** the schema scripts may not have been run as `INVENTORY_APP`, or the connection points at another PDB.
- **PL/SQL compilation errors:** run each SQL file using SQL Developer's **Run Script (F5)**; inspect the Script Output / compiler errors and correct the first reported error before re-running later scripts.
- **Port 5000 busy:** edit the port in the last line of `app.py` (for example, `port=5001`) and open the matching local URL.
- **Charts look blank:** complete at least one sale. Charts deliberately show an empty-state message until relevant Oracle data exists.

## Project structure

```text
multibranch_inventory_project/
├── app.py
├── analytics.py
├── db.py
├── models.py
├── requirements.txt
├── .env.example
├── README.md
├── PROJECT_REPORT.md
├── VIVA_PREP.md
├── sql/
│   ├── 00_create_user.sql
│   ├── 01_schema.sql
│   ├── 02_inventory_pkg.sql
│   ├── 03_triggers_views.sql
│   └── 04_seed_demo.sql
├── templates/
│   ├── base.html
│   ├── setup.html
│   ├── dashboard.html
│   ├── products.html
│   ├── inventory.html
│   ├── activity.html
│   ├── sales.html
│   └── reports.html
└── static/
    ├── app.js
    ├── style.css
    └── generated/
```
