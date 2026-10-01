# SQL Reporting Queries and Index Rationale

Illustrative MySQL 8 queries for the current table/column names. Bind `@business_date` as the current calendar date in `Africa/Kampala`; do not use the database server's timezone as an implicit substitute. Financial queries use completed sales only.

## Sellable stock by batch

```sql
SELECT b.id AS batch_id, d.generic_name, d.brand_name, b.batch_number,
       b.expiry_date, b.available_quantity, s.name AS supplier
FROM pharmacy_batch b
JOIN pharmacy_drug d ON d.id = b.drug_id
JOIN pharmacy_supplier s ON s.id = b.supplier_id
WHERE d.status = 'active' AND b.status = 'available'
  AND b.expiry_date >= @business_date AND b.available_quantity > 0
ORDER BY b.expiry_date, b.id;
```

## Low stock, based on sellable quantities only

```sql
SELECT d.id, d.generic_name, d.strength, d.reorder_level,
       COALESCE(SUM(CASE WHEN b.status = 'available'
                          AND b.expiry_date >= @business_date
                         THEN b.available_quantity ELSE 0 END), 0) AS sellable_units
FROM pharmacy_drug d
LEFT JOIN pharmacy_batch b ON b.drug_id = d.id
WHERE d.status = 'active'
GROUP BY d.id, d.generic_name, d.strength, d.reorder_level
HAVING sellable_units <= d.reorder_level
ORDER BY sellable_units, d.generic_name;
```

## Expired and expiring batches

```sql
SELECT d.generic_name, b.batch_number, b.expiry_date, b.available_quantity,
       CASE WHEN b.expiry_date < @business_date THEN 'expired' ELSE 'expiring' END AS alert
FROM pharmacy_batch b JOIN pharmacy_drug d ON d.id = b.drug_id
WHERE b.available_quantity > 0
  AND (b.expiry_date < @business_date OR b.expiry_date <= DATE_ADD(@business_date, INTERVAL 30 DAY))
ORDER BY b.expiry_date, d.generic_name;
```

## Daily sales and payment totals

```sql
SELECT DATE(CONVERT_TZ(s.completed_at, '+00:00', 'Africa/Kampala')) AS business_day,
       COUNT(*) AS completed_sales, SUM(s.total_amount) AS sales_total,
       SUM(p.amount) AS payment_total
FROM pharmacy_sale s JOIN pharmacy_payment p ON p.sale_id = s.id
WHERE s.status = 'completed'
  AND s.completed_at >= :utc_start AND s.completed_at < :utc_end
GROUP BY business_day ORDER BY business_day;
```

The application should compute Kampala day bounds and pass their UTC equivalents as `:utc_start` and `:utc_end`; this avoids relying on MySQL timezone tables being loaded.

## Sales by drug

```sql
SELECT d.id, d.generic_name, SUM(si.quantity) AS units_sold,
       SUM(si.line_total) AS gross_sales
FROM pharmacy_sale_item si
JOIN pharmacy_sale s ON s.id = si.sale_id
JOIN pharmacy_batch b ON b.id = si.batch_id
JOIN pharmacy_drug d ON d.id = b.drug_id
WHERE s.status = 'completed' AND s.completed_at >= :utc_start AND s.completed_at < :utc_end
GROUP BY d.id, d.generic_name ORDER BY gross_sales DESC;
```

## Payment totals by method

```sql
SELECT p.method, COUNT(*) AS payment_count, SUM(p.amount) AS total_amount
FROM pharmacy_payment p JOIN pharmacy_sale s ON s.id = p.sale_id
WHERE s.status = 'completed' AND s.completed_at >= :utc_start AND s.completed_at < :utc_end
GROUP BY p.method ORDER BY total_amount DESC;
```

## Outstanding purchase quantities

```sql
SELECT po.order_number, sup.name AS supplier, d.generic_name,
       poi.ordered_quantity - COALESCE(SUM(gri.received_quantity), 0) AS outstanding_units
FROM pharmacy_purchaseorder po
JOIN pharmacy_supplier sup ON sup.id = po.supplier_id
JOIN pharmacy_purchaseorderitem poi ON poi.purchase_order_id = po.id
JOIN pharmacy_drug d ON d.id = poi.drug_id
LEFT JOIN pharmacy_goodsreceiptitem gri ON gri.purchase_order_item_id = poi.id
WHERE po.status IN ('ordered', 'partially_received')
GROUP BY po.id, po.order_number, sup.name, d.generic_name, poi.id, poi.ordered_quantity
HAVING outstanding_units > 0
ORDER BY po.created_at, po.order_number;
```

## Index rationale

- `uq_batch_drug_number` enforces manufacturer number uniqueness within one Drug.
- `ix_batch_fefo(drug_id,status,expiry_date,id)` supports eligible-batch filtering and deterministic FEFO order.
- `pharmacy_batch.expiry_date` supports expiry monitoring.
- Drug generic/brand composite index supports lookup; category/status filters can be expanded after query-plan evidence.
- Purchase order status and sale completion timestamps are indexed for operational/report filtering.
- Unique sale idempotency and receipt request keys prevent duplicate requests; Payment's unique sale FK enforces one-to-one cardinality.

Before production, inspect MySQL `EXPLAIN ANALYZE` with representative volume and add indexes only when query evidence supports them.
