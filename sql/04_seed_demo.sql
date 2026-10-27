-- Run ONCE as INVENTORY_APP after the schema, package, triggers and views compile.
INSERT INTO branches (branch_id, branch_code, branch_name, city) VALUES (1, 'NORTH-01', 'North Market', 'Ludhiana');
INSERT INTO branches (branch_id, branch_code, branch_name, city) VALUES (2, 'CENTRAL-02', 'Central Plaza', 'Chandigarh');
INSERT INTO branches (branch_id, branch_code, branch_name, city) VALUES (3, 'SOUTH-03', 'South Point', 'Amritsar');
INSERT INTO app_users (user_id, username, full_name, role_name) VALUES (1, 'demo.admin', 'Demo Administrator', 'ADMIN');
INSERT INTO categories (category_id, category_name) VALUES (1, 'Electronics');
INSERT INTO categories (category_id, category_name) VALUES (2, 'Grocery');
INSERT INTO categories (category_id, category_name) VALUES (3, 'Home & Living');
INSERT INTO categories (category_id, category_name) VALUES (4, 'Personal Care');
INSERT INTO suppliers (supplier_id, supplier_name, phone, email) VALUES (1, 'Northstar Wholesale', '+91-9876500001', 'sales@northstar.example');
INSERT INTO suppliers (supplier_id, supplier_name, phone, email) VALUES (2, 'GreenField Distributors', '+91-9876500002', 'orders@greenfield.example');
COMMIT;

DECLARE
    l_id NUMBER;
BEGIN
    inventory_pkg.create_product('SKU-1001', 'Wireless Mouse', 1, 1, 499.00, 'STANDARD', NULL, 5, l_id);
    inventory_pkg.adjust_stock(1, l_id, 24, 'Opening stock', 1);
    inventory_pkg.adjust_stock(2, l_id, 12, 'Opening stock', 1);

    inventory_pkg.create_product('SKU-1002', 'USB-C Cable', 1, 1, 199.00, 'STANDARD', NULL, 8, l_id);
    inventory_pkg.adjust_stock(1, l_id, 3, 'Opening stock - deliberately low for demo', 1);
    inventory_pkg.adjust_stock(2, l_id, 18, 'Opening stock', 1);

    inventory_pkg.create_product('SKU-2001', 'Premium Tea Pack', 2, 2, 249.00, 'PERISHABLE', TRUNC(SYSDATE) + 90, 6, l_id);
    inventory_pkg.adjust_stock(1, l_id, 16, 'Opening stock', 1);
    inventory_pkg.adjust_stock(3, l_id, 9, 'Opening stock', 1);

    inventory_pkg.create_product('SKU-3001', 'Desk Lamp', 3, 1, 1299.00, 'STANDARD', NULL, 4, l_id);
    inventory_pkg.adjust_stock(1, l_id, 7, 'Opening stock', 1);
    inventory_pkg.adjust_stock(3, l_id, 2, 'Opening stock - deliberately low for demo', 1);

    inventory_pkg.create_product('SKU-4001', 'Hand Wash', 4, 2, 89.00, 'PERISHABLE', TRUNC(SYSDATE) + 180, 10, l_id);
    inventory_pkg.adjust_stock(1, l_id, 22, 'Opening stock', 1);
    inventory_pkg.adjust_stock(2, l_id, 14, 'Opening stock', 1);
    COMMIT;
END;
/

-- Quick verification queries
SELECT branch_name, product_name, quantity, reorder_level
FROM v_inventory_overview ORDER BY branch_name, product_name;
SELECT action_name, entity_name, entity_id, event_time FROM audit_log ORDER BY audit_id DESC FETCH FIRST 10 ROWS ONLY;
