CREATE OR REPLACE PACKAGE inventory_pkg AS
    PROCEDURE create_product(
        p_sku IN VARCHAR2,
        p_name IN VARCHAR2,
        p_category_id IN NUMBER,
        p_supplier_id IN NUMBER,
        p_unit_price IN NUMBER,
        p_product_type IN VARCHAR2,
        p_expiry_date IN DATE,
        p_reorder_level IN NUMBER,
        p_product_id OUT NUMBER
    );

    PROCEDURE adjust_stock(
        p_branch_id IN NUMBER,
        p_product_id IN NUMBER,
        p_quantity_delta IN NUMBER,
        p_reason IN VARCHAR2,
        p_actor_id IN NUMBER
    );

    PROCEDURE finalize_sale(
        p_sale_id IN NUMBER,
        p_actor_id IN NUMBER
    );
END inventory_pkg;
/

CREATE OR REPLACE PACKAGE BODY inventory_pkg AS
    PROCEDURE create_product(
        p_sku IN VARCHAR2,
        p_name IN VARCHAR2,
        p_category_id IN NUMBER,
        p_supplier_id IN NUMBER,
        p_unit_price IN NUMBER,
        p_product_type IN VARCHAR2,
        p_expiry_date IN DATE,
        p_reorder_level IN NUMBER,
        p_product_id OUT NUMBER
    ) IS
        l_type VARCHAR2(15) := UPPER(NVL(p_product_type, 'STANDARD'));
    BEGIN
        IF p_unit_price < 0 OR p_reorder_level < 0 THEN
            RAISE_APPLICATION_ERROR(-20001, 'Price and reorder level must be non-negative.');
        END IF;
        IF l_type NOT IN ('STANDARD', 'PERISHABLE') THEN
            RAISE_APPLICATION_ERROR(-20002, 'Product type must be STANDARD or PERISHABLE.');
        END IF;
        IF l_type = 'PERISHABLE' AND p_expiry_date IS NULL THEN
            RAISE_APPLICATION_ERROR(-20003, 'A perishable product requires an expiry date.');
        END IF;

        INSERT INTO products (sku, name, category_id, supplier_id, unit_price,
                              product_type, expiry_date, reorder_level)
        VALUES (UPPER(TRIM(p_sku)), TRIM(p_name), p_category_id, p_supplier_id,
                p_unit_price, l_type, p_expiry_date, p_reorder_level)
        RETURNING product_id INTO p_product_id;

        -- Create an explicit zero-stock row for every active branch.
        FOR b IN (SELECT branch_id FROM branches WHERE is_active = 'Y') LOOP
            INSERT INTO inventory_stock (branch_id, product_id, quantity, reorder_level)
            VALUES (b.branch_id, p_product_id, 0, p_reorder_level);
        END LOOP;

        INSERT INTO audit_log (actor, action_name, entity_name, entity_id, details)
        VALUES (USER, 'CREATE', 'PRODUCT', p_product_id,
                'Created SKU=' || UPPER(TRIM(p_sku)) || '; type=' || l_type);
    END create_product;

    PROCEDURE adjust_stock(
        p_branch_id IN NUMBER,
        p_product_id IN NUMBER,
        p_quantity_delta IN NUMBER,
        p_reason IN VARCHAR2,
        p_actor_id IN NUMBER
    ) IS
        l_current NUMBER;
    BEGIN
        IF p_quantity_delta IS NULL OR p_quantity_delta = 0 THEN
            RAISE_APPLICATION_ERROR(-20010, 'Stock adjustment must not be zero.');
        END IF;

        SELECT quantity INTO l_current
        FROM inventory_stock
        WHERE branch_id = p_branch_id AND product_id = p_product_id
        FOR UPDATE;

        IF l_current + p_quantity_delta < 0 THEN
            RAISE_APPLICATION_ERROR(-20011, 'Insufficient stock: adjustment would make inventory negative.');
        END IF;

        UPDATE inventory_stock
        SET quantity = quantity + p_quantity_delta, updated_at = SYSTIMESTAMP
        WHERE branch_id = p_branch_id AND product_id = p_product_id;

        INSERT INTO stock_movements (branch_id, product_id, movement_type, quantity_delta,
                                     reference_type, note, created_by)
        VALUES (p_branch_id, p_product_id, 'ADJUSTMENT', p_quantity_delta,
                'MANUAL', SUBSTR(p_reason, 1, 500), p_actor_id);

        INSERT INTO audit_log (actor, action_name, entity_name, entity_id, details)
        VALUES (USER, 'ADJUST_STOCK', 'INVENTORY_STOCK', p_product_id,
                'Branch=' || p_branch_id || '; delta=' || p_quantity_delta || '; reason=' || SUBSTR(p_reason,1,300));
    END adjust_stock;

    PROCEDURE finalize_sale(
        p_sale_id IN NUMBER,
        p_actor_id IN NUMBER
    ) IS
        l_branch_id NUMBER;
        l_status VARCHAR2(15);
        l_available NUMBER;
        l_total NUMBER(14,2) := 0;
    BEGIN
        -- Lock the sale header so concurrent attempts cannot finalize the same bill twice.
        SELECT branch_id, status INTO l_branch_id, l_status
        FROM sales WHERE sale_id = p_sale_id FOR UPDATE;

        IF l_status <> 'PENDING' THEN
            RAISE_APPLICATION_ERROR(-20020, 'Only a PENDING sale can be finalized.');
        END IF;
        UPDATE sales SET status = 'PROCESSING' WHERE sale_id = p_sale_id;

        -- Consistent product-id ordering reduces the chance of deadlocks for multi-line bills.
        FOR item IN (
            SELECT product_id, quantity, unit_price
            FROM sale_items WHERE sale_id = p_sale_id
            ORDER BY product_id, sale_item_id
        ) LOOP
            SELECT quantity INTO l_available
            FROM inventory_stock
            WHERE branch_id = l_branch_id AND product_id = item.product_id
            FOR UPDATE;

            IF l_available < item.quantity THEN
                RAISE_APPLICATION_ERROR(-20021,
                    'Insufficient stock for product ID ' || item.product_id ||
                    '. Available=' || l_available || ', requested=' || item.quantity || '.');
            END IF;

            UPDATE inventory_stock
            SET quantity = quantity - item.quantity, updated_at = SYSTIMESTAMP
            WHERE branch_id = l_branch_id AND product_id = item.product_id;

            INSERT INTO stock_movements (branch_id, product_id, movement_type, quantity_delta,
                                         reference_type, reference_id, note, created_by)
            VALUES (l_branch_id, item.product_id, 'SALE', -item.quantity,
                    'SALE', p_sale_id, 'Stock deducted by finalized bill', p_actor_id);

            l_total := l_total + (item.quantity * item.unit_price);
        END LOOP;

        UPDATE sales
        SET total_amount = l_total, status = 'COMPLETED', completed_at = SYSTIMESTAMP
        WHERE sale_id = p_sale_id;

        INSERT INTO audit_log (actor, action_name, entity_name, entity_id, details)
        VALUES (USER, 'FINALIZE_SALE', 'SALE', p_sale_id,
                'Branch=' || l_branch_id || '; total=' || TO_CHAR(l_total));
    END finalize_sale;
END inventory_pkg;
/
