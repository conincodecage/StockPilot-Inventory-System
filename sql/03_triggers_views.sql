-- Active database rules: integrity checks and automated audit entries.
CREATE OR REPLACE TRIGGER trg_inventory_stock_guard
BEFORE INSERT OR UPDATE OF quantity ON inventory_stock
FOR EACH ROW
BEGIN
    IF :NEW.quantity < 0 THEN
        RAISE_APPLICATION_ERROR(-20030, 'Inventory quantity cannot be negative.');
    END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_sale_item_total
BEFORE INSERT OR UPDATE OF quantity, unit_price ON sale_items
FOR EACH ROW
BEGIN
    IF :NEW.quantity <= 0 OR :NEW.unit_price < 0 THEN
        RAISE_APPLICATION_ERROR(-20031, 'Sale quantity must be positive and unit price non-negative.');
    END IF;
    :NEW.line_total := ROUND(:NEW.quantity * :NEW.unit_price, 2);
END;
/

CREATE OR REPLACE TRIGGER trg_sale_item_pending_only
BEFORE INSERT OR UPDATE OR DELETE ON sale_items
FOR EACH ROW
DECLARE
    l_sale_id NUMBER;
    l_status sales.status%TYPE;
BEGIN
    IF INSERTING OR UPDATING THEN
        l_sale_id := :NEW.sale_id;
    ELSE
        l_sale_id := :OLD.sale_id;
    END IF;

    -- Lock the parent header; modifications wait for a concurrent finalization to finish.
    SELECT status INTO l_status FROM sales WHERE sale_id = l_sale_id FOR UPDATE;
    IF l_status <> 'PENDING' THEN
        RAISE_APPLICATION_ERROR(-20032, 'Sale lines can only be changed while the sale is PENDING.');
    END IF;
END;
/

CREATE OR REPLACE TRIGGER trg_product_audit
AFTER INSERT OR UPDATE ON products
FOR EACH ROW
DECLARE
    l_action VARCHAR2(10);
BEGIN
    IF INSERTING THEN
        l_action := 'INSERT';
    ELSE
        l_action := 'UPDATE';
    END IF;
    INSERT INTO audit_log (actor, action_name, entity_name, entity_id, details)
    VALUES (USER, l_action, 'PRODUCT', :NEW.product_id,
            'SKU=' || :NEW.sku || '; name=' || :NEW.name || '; price=' || TO_CHAR(:NEW.unit_price));
END;
/

CREATE OR REPLACE TRIGGER trg_sale_status_audit
AFTER UPDATE OF status ON sales
FOR EACH ROW
WHEN (OLD.status <> NEW.status)
BEGIN
    INSERT INTO audit_log (actor, action_name, entity_name, entity_id, details)
    VALUES (USER, 'STATUS_CHANGE', 'SALE', :NEW.sale_id,
            'Sale status changed from ' || :OLD.status || ' to ' || :NEW.status);
END;
/

CREATE OR REPLACE VIEW v_inventory_overview AS
SELECT b.branch_id, b.branch_code, b.branch_name,
       p.product_id, p.sku, p.name AS product_name, c.category_name,
       sp.supplier_name, p.product_type, p.expiry_date, p.unit_price,
       i.quantity, i.reorder_level, p.is_active
FROM inventory_stock i
JOIN branches b ON b.branch_id = i.branch_id
JOIN products p ON p.product_id = i.product_id
JOIN categories c ON c.category_id = p.category_id
LEFT JOIN suppliers sp ON sp.supplier_id = p.supplier_id;

CREATE OR REPLACE VIEW v_sales_by_category AS
SELECT c.category_id, c.category_name,
       SUM(CASE WHEN s.status = 'COMPLETED' THEN si.line_total ELSE 0 END) AS revenue
FROM categories c
LEFT JOIN products p ON p.category_id = c.category_id
LEFT JOIN sale_items si ON si.product_id = p.product_id
LEFT JOIN sales s ON s.sale_id = si.sale_id
GROUP BY c.category_id, c.category_name;
/
