---
name: sql-query-builder
description: "Transform natural language into optimized SQL. Build CTEs, window functions, and complex joins with performance hints, EXPLAIN plans, and index recommendations."
category: data
difficulty: advanced
model_boost: "Weak model generates inefficient or syntactically incorrect SQL"
---

# SQL Query Builder

## Purpose
Converting business questions into SQL requires balancing correctness, readability, and performance. This skill systematizes the translation from natural language into optimized SQL, including use of Common Table Expressions (CTEs), window functions, and performance optimization techniques. Output includes executable SQL, execution plans, and recommendations for indexing to support future queries.

## When to Use
- Translating business questions into database queries
- Building reusable query templates for recurring analysis
- Optimizing slow-running analytical queries
- Generating reports with complex aggregations
- **Do NOT use when**: Simple single-table lookups, or query builder UI exists for that purpose

## Instructions

### Step 1: Interpret the Business Question
Extract the core requirements before writing SQL:

**Key elements to identify:**
- **What entities/metrics**: Which tables contain relevant data?
- **Filters/constraints**: Time windows, segments, exclusions?
- **Aggregations**: Count, sum, average, ratios?
- **Comparisons**: Year-over-year, before/after, cohort analysis?
- **Output granularity**: Daily, per-customer, per-product, overall?
- **Sorting/ranking**: Top 10 products, ranked by revenue?

Example interpretation:
```
Question: "What are our top 5 products by revenue last quarter,
excluding discounted items, ranked by profit margin?"

Requirements:
- Entities: orders, products, order_items
- Timeframe: Last quarter (Q4 2025)
- Filters: discount_amount = 0
- Metrics: revenue (sum of amount), profit_margin (revenue - cost) / revenue
- Ranking: Order by profit_margin DESC, limit 5
- Output grain: Per product
```

### Step 2: Design the Schema Relationships
Map the business logic to table joins:

```sql
-- Understand the schema first
/*
customers: customer_id, name, created_date, country
orders: order_id, customer_id, order_date, total_amount, status
order_items: order_item_id, order_id, product_id, quantity, unit_price, discount
products: product_id, name, category, cost_price, discontinued
*/

-- Identify join keys and relationships
-- orders.customer_id → customers.customer_id (1:N)
-- orders.order_id → order_items.order_id (1:N)
-- order_items.product_id → products.product_id (N:1)
```

### Step 3: Build Modular CTEs
Break complex logic into readable, reusable pieces:

```sql
WITH base_sales AS (
  -- Start with raw transactions, apply filters early
  SELECT
    oi.order_item_id,
    p.product_id,
    p.name AS product_name,
    p.category,
    oi.quantity,
    oi.unit_price,
    oi.discount,
    (oi.quantity * oi.unit_price * (1 - oi.discount)) AS revenue,
    (oi.quantity * p.cost_price) AS cost,
    o.order_date,
    EXTRACT(YEAR FROM o.order_date) AS year,
    EXTRACT(QUARTER FROM o.order_date) AS quarter
  FROM order_items oi
  JOIN products p ON oi.product_id = p.product_id
  JOIN orders o ON oi.order_id = o.order_id
  WHERE o.order_date >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')
    AND o.status = 'completed'
    AND oi.discount = 0
    AND p.discontinued = FALSE
),

product_metrics AS (
  -- Aggregate metrics per product
  SELECT
    product_id,
    product_name,
    category,
    SUM(revenue) AS total_revenue,
    SUM(cost) AS total_cost,
    COUNT(DISTINCT order_item_id) AS units_sold,
    ROUND(
      ((SUM(revenue) - SUM(cost)) / SUM(revenue) * 100)::NUMERIC,
      2
    ) AS profit_margin_pct
  FROM base_sales
  GROUP BY product_id, product_name, category
),

ranked_products AS (
  -- Rank products by profit margin
  SELECT
    *,
    ROW_NUMBER() OVER (ORDER BY profit_margin_pct DESC) AS rank
  FROM product_metrics
)

SELECT
  rank,
  product_name,
  category,
  total_revenue,
  total_cost,
  profit_margin_pct,
  units_sold
FROM ranked_products
WHERE rank <= 5
ORDER BY rank;
```

**CTE benefits:**
- Each CTE solves one logical problem
- Intermediate results cached by query planner
- Easy to test each layer independently
- Readable progression from raw to final result

### Step 4: Implement Window Functions
Use window functions for row-level calculations and comparisons:

```sql
-- Cohort analysis: Customer acquisition month and monthly retention
WITH cohorts AS (
  SELECT
    customer_id,
    DATE_TRUNC('month', MIN(order_date)) AS cohort_month
  FROM orders
  GROUP BY customer_id
),

monthly_activity AS (
  SELECT
    c.customer_id,
    c.cohort_month,
    DATE_TRUNC('month', o.order_date) AS activity_month,
    DATEDIFF(month, c.cohort_month, DATE_TRUNC('month', o.order_date)) AS months_since_cohort,
    SUM(o.total_amount) AS monthly_revenue
  FROM orders o
  JOIN cohorts c ON o.customer_id = c.customer_id
  WHERE o.status = 'completed'
  GROUP BY c.customer_id, c.cohort_month, DATE_TRUNC('month', o.order_date)
),

cohort_size AS (
  SELECT
    cohort_month,
    COUNT(DISTINCT customer_id) AS cohort_customers
  FROM cohorts
  GROUP BY cohort_month
),

retention AS (
  SELECT
    ma.cohort_month,
    ma.months_since_cohort,
    COUNT(DISTINCT ma.customer_id) AS active_customers,
    cs.cohort_customers,
    ROUND(
      (COUNT(DISTINCT ma.customer_id)::FLOAT / cs.cohort_customers * 100)::NUMERIC,
      1
    ) AS retention_pct
  FROM monthly_activity ma
  JOIN cohort_size cs ON ma.cohort_month = cs.cohort_month
  GROUP BY ma.cohort_month, ma.months_since_cohort, cs.cohort_customers
)

SELECT * FROM retention
ORDER BY cohort_month DESC, months_since_cohort ASC;
```

**Common window functions:**
- `ROW_NUMBER()`: Unique rank, even for ties
- `RANK()`: Skip numbers after ties
- `DENSE_RANK()`: No gaps after ties
- `LAG()` / `LEAD()`: Previous/next row value
- `SUM() OVER (PARTITION BY ... ORDER BY ...)`: Running totals
- `NTILE()`: Quartiles, deciles, percentiles

### Step 5: Apply Performance Optimization
Transform correct but slow queries into efficient ones:

```sql
-- INEFFICIENT: Subquery in SELECT clause (runs per row)
SELECT
  customer_id,
  (SELECT COUNT(*) FROM orders o2 WHERE o2.customer_id = o.customer_id) AS order_count
FROM orders o;

-- OPTIMIZED: Single scan with window function
SELECT DISTINCT
  customer_id,
  COUNT(*) OVER (PARTITION BY customer_id) AS order_count
FROM orders;

-- INEFFICIENT: JOIN then aggregate (many duplicate rows)
SELECT
  c.customer_id,
  c.name,
  COUNT(o.order_id) AS order_count,
  SUM(o.total_amount) AS lifetime_value
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name;

-- OPTIMIZED: Aggregate first, then join
WITH customer_metrics AS (
  SELECT
    customer_id,
    COUNT(*) AS order_count,
    SUM(total_amount) AS lifetime_value
  FROM orders
  GROUP BY customer_id
)
SELECT
  c.customer_id,
  c.name,
  COALESCE(cm.order_count, 0) AS order_count,
  COALESCE(cm.lifetime_value, 0) AS lifetime_value
FROM customers c
LEFT JOIN customer_metrics cm ON c.customer_id = cm.customer_id;
```

**Optimization rules:**
- Filter early (WHERE before JOIN)
- Aggregate before JOINing large tables
- Avoid N+1 patterns (subqueries in SELECT)
- Use appropriate JOIN types (INNER vs. LEFT)
- Partition large aggregations (GROUP BY is expensive)

### Step 6: Generate EXPLAIN Plan and Index Recommendations
Validate performance and suggest optimizations:

```sql
-- Run EXPLAIN to see execution plan
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT
  product_id,
  SUM(amount) AS revenue
FROM order_items
WHERE order_date >= '2025-01-01'
GROUP BY product_id
ORDER BY revenue DESC
LIMIT 10;

/* Output indicates:
  - Sequential scan on order_items (no index used)
  - 45 million rows scanned for 50K relevant
  - 2.4GB of buffers read
*/

-- RECOMMENDED INDEXES:
CREATE INDEX idx_order_items_date ON order_items(order_date);
-- Index on filter column accelerates WHERE clause

CREATE INDEX idx_orders_customer_date ON orders(customer_id, order_date DESC);
-- Multi-column index optimizes common query pattern

CREATE INDEX idx_order_items_product_date
ON order_items(product_id, order_date)
INCLUDE (quantity, unit_price);
-- INCLUDE clause adds columns without enlarging index

-- After indexing, rerun EXPLAIN
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
-- Shows: Index scan instead of sequential scan, <100ms instead of 45s
```

## Output Template

**SQL Query** (production-ready):
```sql
-- Query Name: Top Products by Profit Margin
-- Business Owner: [Name]
-- Created: 2026-03-05
-- Performance Target: <5 seconds on 100M+ rows

[Complete CTE structure with detailed comments]
```

**EXPLAIN Analysis**:
```
Query Plan:
- Planning time: 0.3ms
- Execution time: 1,234ms (with 5M rows scanned)
- Buffers: 45GB hit, 12MB read
- Bottleneck: Sequential scan on order_items (recommend index on order_date)
```

**Index Recommendations**:
```
1. idx_orders_customer_date (orders table)
   - Reason: Filters 95% of rows in typical queries
   - Estimated query speedup: 40x
   - Storage cost: 2.3GB

2. idx_order_items_product_date (order_items table)
   - Reason: GROUP BY product_id on large fact table
   - Estimated query speedup: 25x
   - Storage cost: 5.1GB
```

## Quality Gates

1. **Correctness**: Query produces expected row count (validate against known answers)
2. **Syntax validation**: Query runs without errors in target database
3. **Performance**: Executes within SLA (document SLA target)
4. **Data completeness**: No missing or duplicate data in results
5. **Filter validation**: Sample results manually verify WHERE conditions applied
6. **Join validation**: Check for Cartesian products (row count explosion)

## Examples

**Good: Well-structured, documented, optimized**
```sql
-- Monthly revenue by product category with YoY growth
-- Uses CTEs for clarity, window function for comparison
WITH monthly_metrics AS (
  SELECT
    DATE_TRUNC('month', o.order_date) AS month,
    p.category,
    SUM(oi.quantity * oi.unit_price) AS revenue
  FROM orders o
  JOIN order_items oi ON o.order_id = oi.order_id
  JOIN products p ON oi.product_id = p.product_id
  WHERE o.status = 'completed'
    AND o.order_date >= DATE_TRUNC('year', CURRENT_DATE)
  GROUP BY DATE_TRUNC('month', o.order_date), p.category
)
SELECT
  month,
  category,
  revenue,
  LAG(revenue) OVER (PARTITION BY category ORDER BY month) AS prev_month_revenue,
  ROUND(((revenue - LAG(revenue) OVER (PARTITION BY category ORDER BY month))
         / LAG(revenue) OVER (PARTITION BY category ORDER BY month) * 100)::NUMERIC, 1) AS mom_growth_pct
FROM monthly_metrics
ORDER BY month DESC, category;
```

**Bad: Nested subqueries, inefficient, unclear**
```sql
SELECT * FROM (
  SELECT * FROM (
    SELECT o.*, (SELECT SUM(amount) FROM order_items WHERE order_id = o.order_id) AS total
    FROM orders o
  ) WHERE total > 100
) WHERE EXTRACT(YEAR FROM order_date) = 2025;
-- Multiple nested layers, subquery in SELECT, no CTEs, hard to optimize
```

## Common Mistakes

1. **Missing filters in JOINs**: Joining raw order_items to customers without filtering on order status causes inflation
2. **Implicit type conversions**: Comparing string '123' to integer 123; forces full table scan (indexes ignored)
3. **GROUP BY without aggregation**: Adding unaggregated columns in GROUP BY produces unpredictable results
4. **Ignoring NULL handling**: LEFT JOINs producing unexpected counts; need COALESCE() for zero cases
5. **Date filtering on computed columns**: `WHERE YEAR(order_date) = 2025` prevents index use; use `WHERE order_date >= '2025-01-01'`

## Anti-Patterns

1. **Stored procedure for every query**: Embeds SQL in application layer; version control nightmare
2. **SELECT \* in production**: Retrieves unnecessary columns; bloats memory and network
3. **No query documentation**: Business logic embedded in WHERE clause; months later, no one knows why
4. **Hardcoded magic numbers**: `WHERE amount > 999.99` with no context; should be named parameters or constants
5. **Complex case statements instead of CTEs**: Readability decreases; refactoring becomes error-prone