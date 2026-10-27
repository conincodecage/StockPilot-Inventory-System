# Viva preparation — StockPilot

## Questions with concise answers

**1. Why did you choose Oracle PL/SQL instead of putting all business rules in Python?**  
The critical rules are closer to the data and can be enforced consistently for any client. PL/SQL procedures control product creation, stock adjustment and sale finalization.

**2. What is the role of `INVENTORY_PKG`?**  
It groups the procedures `CREATE_PRODUCT`, `ADJUST_STOCK` and `FINALIZE_SALE` into one database-side API.

**3. What does ACID mean in this project?**  
Atomicity is demonstrated by committing the entire bill or rolling it back. Consistency is supported by constraints and PL/SQL validation. Isolation is supported by row locks. Durability is provided by Oracle after commit.

**4. Why use `SELECT ... FOR UPDATE`?**  
It locks a row until the transaction ends so two sessions cannot both act on a stale stock quantity and oversell the same branch's inventory.

**5. What is the purpose of a trigger?**  
A trigger runs automatically in response to a database event. Here, triggers guard non-negative inventory, calculate line totals, restrict sale-line edits and write audit events.

**6. What happens when a bill exceeds available stock?**  
`FINALIZE_SALE` raises an application error. Python catches the database error and rolls back the transaction, so partial stock deductions are not committed.

**7. What are `STOCK_MOVEMENTS` and `AUDIT_LOG` for?**  
The movement ledger records signed stock changes and references; the audit log records important business or data events for traceability.

**8. Why is `INVENTORY_STOCK` keyed by branch and product?**  
A product can have different quantities at different branches, so the composite key uniquely identifies each branch-product balance.

**9. Where are inheritance and polymorphism used?**  
`PerishableProduct` inherits common fields and behaviour from `Product`. `product_from_row()` returns the class appropriate to the database product type.

**10. What do Pandas and NumPy do?**  
Pandas creates DataFrames and normalizes date/numeric values from Oracle results. NumPy creates numeric arrays and calculates summaries used by the charts and report cards.

**11. Why is Flask used?**  
Flask provides Python routes and HTML responses for a browser-based local site. The user can demonstrate the system in Chrome without deploying a public website.

**12. Is this a fully distributed database?**  
No. It models separate branch inventory within one Oracle instance and provides consolidated queries. A physically distributed DDBMS would need multiple database nodes and explicit distribution/replication protocols.

**13. What is the difference between a procedure and a trigger?**  
A procedure is explicitly invoked by an application or SQL call. A trigger fires automatically when the configured table event occurs.

**14. What is the role of a database view?**  
`V_INVENTORY_OVERVIEW` hides repeated joins and supplies a unified inventory view for the application.

**15. How would you extend the project?**  
Add authenticated users and role checks, purchase orders, branch transfers, invoice export and a properly secured production deployment.

## Suggested live demonstration

1. Show the Dashboard and identify the low-stock row.
2. Open Branch inventory; adjust stock by a small positive quantity.
3. Create a valid bill and show that quantity drops.
4. Attempt the seeded over-sale case and point out the rollback message.
5. Open SQL Developer and show the package, triggers, views, movement table and audit log.
6. Open Analytics and explain the Pandas/NumPy/Matplotlib pipeline.
