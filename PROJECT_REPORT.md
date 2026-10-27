# StockPilot: Multi-Branch Inventory, Billing & Sales Analytics System

## 1. Abstract

StockPilot is a browser-based inventory and billing application for an organisation operating several branches. It maintains product catalogue information, tracks stock separately for each branch, creates sales bills, prevents invalid stock deductions, and presents sales and stock trends. The user interface is built with Python Flask, while Oracle Database stores the data and PL/SQL procedures perform important business operations. Pandas and NumPy prepare analytical data, and Matplotlib generates dashboard charts.

The application is designed as a localhost project for an MCA first-semester demonstration. Multiple branches share a single Oracle instance in this implementation; branch-wise records and consolidated views demonstrate multi-branch data management, not a physically distributed multi-node database.

## 2. Problem statement

When products, quantities and bills are tracked independently, stock counts can drift, an order can exceed available stock, and it can be difficult to compare branch performance. The system needs one consistent data store, central business rules, transaction-safe billing and a simple way to review inventory and sales.

## 3. Objectives

- Store product, category, supplier, branch, customer, inventory and sales records in Oracle.
- Maintain branch-specific stock quantities and reorder levels.
- Validate and record stock adjustments through a stored PL/SQL procedure.
- Complete a bill only when the selected branch has sufficient stock.
- Use database locking and transaction rollback to prevent partial stock deductions.
- Maintain stock-movement and audit records for traceability.
- Apply Python object-oriented programming, inheritance, Pandas, NumPy and Matplotlib.
- Present operational information in a responsive local website.

## 4. Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| User interface | HTML, CSS, JavaScript | Forms, navigation, responsive dashboard |
| Web server | Python, Flask | Routes, input validation, flash messages |
| Oracle driver | python-oracledb (Thin mode) | Python-to-Oracle connectivity |
| Database | Oracle Database Free / XE | Persistent relational data and constraints |
| Database logic | PL/SQL package and triggers | Product creation, stock adjustment, sale finalization and audits |
| Analytics | Pandas, NumPy, Matplotlib | Data cleaning, summaries and charts |

## 5. System modules

### 5.1 Dashboard

Displays active products, active branches, total stock units, current-month completed-sale revenue, recent bills and inventory rows at or below their reorder levels.

### 5.2 Product catalogue

Captures SKU, product name, category, supplier, price, product type, expiry date and reorder level. `INVENTORY_PKG.CREATE_PRODUCT` validates the submitted values and creates a zero-stock row for each active branch. `Product` is the base Python class; `PerishableProduct` inherits the shared fields and adds expiry-aware behaviour.

### 5.3 Branch inventory

Reads `V_INVENTORY_OVERVIEW` and supports branch and text filters. Stock adjustments use `INVENTORY_PKG.ADJUST_STOCK`, which locks the relevant inventory row, blocks a negative result, updates the stock value and inserts movement/audit records.

### 5.4 Billing and sales

A bill is staged with `PENDING` status. The web application inserts the bill lines and calls `INVENTORY_PKG.FINALIZE_SALE`. The PL/SQL procedure locks the sale header and relevant inventory rows, checks available quantities, deducts the quantities, calculates the bill total and records movements. Python commits only after the procedure succeeds; an error causes rollback.

### 5.5 Analytics

Oracle supplies database records and grouped totals. Pandas normalizes dates and numeric fields and handles missing/non-numeric values. NumPy supports numerical summaries and chart series. Matplotlib creates revenue trend, revenue-by-category and stock-by-branch charts.

## 6. Database design

| Table / view | Purpose |
|---|---|
| `BRANCHES` | Branch codes, names, cities and active flags |
| `APP_USERS` | Demo operator and role reference for movement attribution |
| `CATEGORIES` | Product classification |
| `SUPPLIERS` | Supplier contact details |
| `PRODUCTS` | SKU, price, category, product type and expiry details |
| `INVENTORY_STOCK` | Composite branch-product stock balance and reorder level |
| `CUSTOMERS` | Optional customer details for bills |
| `SALES` | Sale header, status, branch, time and total |
| `SALE_ITEMS` | Product, quantity, unit price and line total for each bill |
| `STOCK_MOVEMENTS` | Signed quantity changes and their references/reasons |
| `AUDIT_LOG` | Time, actor, action, entity and details |
| `V_INVENTORY_OVERVIEW` | Consolidated branch/product inventory query |
| `V_SALES_BY_CATEGORY` | Aggregated completed sales by category |

The schema uses primary and foreign keys, unique SKU and branch codes, numeric checks, active flags and a product expiry constraint. `INVENTORY_STOCK` has a composite primary key `(branch_id, product_id)` because each product has a separate stock balance at each branch.

## 7. Important PL/SQL logic

### `INVENTORY_PKG.CREATE_PRODUCT`

Checks price, reorder level, product type and expiry date; inserts the product; creates its zero-quantity inventory rows for active branches; and records an audit event. The product audit trigger supplies an additional automatic audit record.

### `INVENTORY_PKG.ADJUST_STOCK`

Uses `SELECT ... FOR UPDATE` to lock the branch-product row before reading and changing its quantity. A negative resulting balance is rejected. Successful adjustments write `STOCK_MOVEMENTS` and `AUDIT_LOG` records.

### `INVENTORY_PKG.FINALIZE_SALE`

Locks the sale header so the same bill cannot be finalized twice. It changes the status to `PROCESSING`, processes sale lines in product-ID order, locks each stock row, rejects quantities exceeding availability, deducts stock, and records movements. It finally calculates the total and marks the bill `COMPLETED`. The Python layer commits after success; on a PL/SQL exception it rolls back all staged work.

### Triggers

- `TRG_INVENTORY_STOCK_GUARD`: blocks negative stock.
- `TRG_SALE_ITEM_TOTAL`: calculates line totals and validates positive quantity/non-negative price.
- `TRG_SALE_ITEM_PENDING_ONLY`: prevents line edits after the sale leaves `PENDING`; it locks the parent bill while checking status.
- `TRG_PRODUCT_AUDIT`: automatically logs product inserts and updates.
- `TRG_SALE_STATUS_AUDIT`: logs sales status changes.

## 8. Transaction flow

1. Python validates the form and inserts a `PENDING` bill plus its line items.
2. The line-item trigger confirms the bill is still pending.
3. Python calls the PL/SQL finalization procedure within the same connection/transaction.
4. PL/SQL obtains row locks, validates stock and performs stock, bill-total, movement and audit changes.
5. If every step succeeds, Python commits. If any step raises an error, Python rolls back; pending header, line items and any uncommitted stock changes are removed together.

This is the core atomicity demonstration. A useful test is attempting to sell four USB-C Cables at North Market when the seed script provides only three.

## 9. Syllabus alignment

### Python Programming

- Functions and conditions: form validation, business workflows and request handling.
- Lists and dictionaries: processing line items and database query results.
- Classes, inheritance and polymorphism: `Product`, `PerishableProduct` and `product_from_row()`.
- NumPy: numerical arrays and summary values.
- Pandas: DataFrame conversion, date parsing and numeric missing-value handling.
- Matplotlib: line, bar and pie charts.
- Web programming: Flask request/response routes and HTML templates are used for the browser-based interface. Tkinter is not used in this version because the chosen interface is a website.

### Advanced Database Management System

- Relational schema design, primary/foreign keys, constraints and views.
- Query processing through joins, filters and grouped reporting queries.
- Transaction management and atomic commit/rollback.
- Locking-based concurrency control with `SELECT ... FOR UPDATE`.
- Active database concepts using PL/SQL triggers.
- Recovery/traceability through transaction rollback, stock movements and audit logs.
- Multi-branch design with branch-level inventory and consolidated reporting.

## 10. Test cases

| Test | Action | Expected result |
|---|---|---|
| TC-01 | Add a standard product | Product saved; zero-stock row created at each active branch |
| TC-02 | Add a perishable product without an expiry date | Rejected by Python and PL/SQL/table validation |
| TC-03 | Add a positive stock adjustment | Quantity, movement ledger and audit record updated |
| TC-04 | Apply a negative adjustment greater than current stock | PL/SQL rejects the adjustment; no negative stock is committed |
| TC-05 | Complete a bill with available stock | Sale becomes `COMPLETED`, total is calculated and stock is reduced |
| TC-06 | Sell four seeded USB-C Cables from North Market | Sale fails because only three were seeded; transaction is rolled back |
| TC-07 | Attempt to modify lines after completion | Trigger rejects the change |
| TC-08 | Open Analytics after a completed bill | Revenue/category/branch charts use Oracle data |

## 11. Limitations and future work

This classroom version does not include production login and role-based authorization, purchasing, barcode scanning, invoice PDF export, supplier receiving, branch transfers, or public cloud hosting. Although the schema models branch-level data, all branch records are stored in one Oracle database. A physically distributed database would require separate database nodes and an explicit replication/distributed-transaction design. Possible future additions include authenticated roles, purchase orders, transfer approval, barcode support, alert notifications and a production deployment behind HTTPS.

## 12. Conclusion

StockPilot combines a practical inventory workflow with core Python analytics and database-side business rules. The key design choice is to keep critical quantity validation and sale finalization in PL/SQL, with Python controlling the interface and transaction boundary. This makes the application suitable for demonstrating OOP, analytics, relational modelling, triggers, row locking, audit trails and atomic transaction behaviour in an MCA project viva.
