---
name: database-schema
description: "Design normalized database schemas from requirements with normalization analysis, strategic indexing, migration scripts, ERD generation, and query optimization hints for performance."
category: coding
difficulty: advanced
model_boost: "Weak models create denormalized schemas, miss indexes, don't plan migrations, and ignore query performance implications"
---

# Database Schema Designer

## Purpose
Database schema design determines application performance, data consistency, and future scalability. Well-designed schemas minimize duplication, support queries efficiently with strategic indexes, and accommodate evolution without full rewrites. This skill produces normalized schemas with ERDs, migration strategies, and performance analysis.

## When to Use
- Designing new application data models
- Planning data migrations (schema changes)
- Optimizing slow query performance via schema redesign
- Evaluating whether to denormalize for performance
- Establishing data consistency rules (foreign keys, constraints)
- **Do NOT use when**: Existing schema is stable and performing fine, or designing in-memory caches (different rules)

## Instructions

### Step 1: Extract Entities and Attributes from Requirements
Read requirements and identify nouns as entities (User, Product, Order). For each entity, list attributes and their types:
```
User:
  - id (UUID, primary key)
  - email (VARCHAR 255, unique)
  - passwordHash (VARCHAR 255)
  - createdAt (TIMESTAMP)

Product:
  - id (UUID, primary key)
  - name (VARCHAR 255)
  - price (DECIMAL 10,2)
  - stockQuantity (INTEGER)
```

Identify relationships: one-to-one, one-to-many, many-to-many. Example: User has many Orders, Product has many Reviews.

### Step 2: Apply Normalization Rules
Normalize to 3NF (Third Normal Form):
- **1NF**: Each column has atomic (non-repeating) values. No comma-separated lists in a cell.
- **2NF**: All non-key columns depend on the entire primary key (not partial).
- **3NF**: Non-key columns depend only on the primary key, not on other non-key columns.

Example violation (not 1NF):
```sql
-- BAD: reviewer_ids is a list
CREATE TABLE products (
  id INT PRIMARY KEY,
  name VARCHAR(255),
  reviewer_ids VARCHAR(255)  -- '1,2,3,4' violates 1NF
);

-- GOOD: separate table
CREATE TABLE reviews (
  id INT PRIMARY KEY,
  product_id INT,
  reviewer_id INT,
  FOREIGN KEY (product_id) REFERENCES products(id)
);
```

Example violation (not 3NF):
```sql
-- BAD: price_in_usd depends on currency, not order
CREATE TABLE orders (
  id INT PRIMARY KEY,
  user_id INT,
  currency VARCHAR(3),
  price_in_usd DECIMAL(10,2)  -- Violates 3NF
);

-- GOOD: store amount and currency, calculate on query
CREATE TABLE orders (
  id INT PRIMARY KEY,
  user_id INT,
  amount DECIMAL(10,2),
  currency VARCHAR(3)
);
```

### Step 3: Design Foreign Keys and Constraints
Define referential integrity:
```sql
CREATE TABLE orders (
  id INT PRIMARY KEY,
  user_id INT NOT NULL,
  status VARCHAR(50) DEFAULT 'pending',
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CHECK (status IN ('pending', 'completed', 'cancelled'))
);
```

Use ON DELETE CASCADE for natural parent-child relationships (user deleted → orders deleted). Use ON DELETE RESTRICT for important references (can't delete product if orders exist). Plan carefully: cascading deletes can be destructive.

### Step 4: Identify Query Patterns and Index Candidates
List the most common queries (from API endpoints):
- "Get user by email" → Index on `users(email)`
- "Get orders by user in date range" → Index on `orders(user_id, created_at)`
- "Search products by name" → Full-text index on `products(name)`

Rules for effective indexes:
- **Single-column index**: Query filters on one column frequently
- **Composite index**: Query filters on multiple columns together. Order matters: filter columns first, then sort columns.
  - Query: `SELECT * FROM orders WHERE user_id = ? AND created_at > ? ORDER BY created_at DESC`
  - Index: `CREATE INDEX idx_orders_user_date ON orders(user_id, created_at DESC)`
- **Covering index**: Include columns needed in SELECT to avoid table lookups
  - Query returns only `(id, user_id, amount)`, create covering index: `CREATE INDEX idx_orders_covering ON orders(user_id, amount) INCLUDE (id)`

Avoid over-indexing: each index costs write performance. Balance reads vs. writes.

### Step 5: Plan for Scale and Denormalization
At small scale (< 1M rows), perfect normalization is ideal. At scale, consider strategic denormalization:

Example: User has 10,000 orders. Query "get user with order count" requires JOIN or COUNT.
```sql
-- Normalized: requires COUNT every time
SELECT users.id, users.name, COUNT(orders.id) as order_count
FROM users
LEFT JOIN orders ON users.id = orders.user_id
GROUP BY users.id;

-- Denormalized: fast but requires maintaining counter
ALTER TABLE users ADD COLUMN order_count INT DEFAULT 0;
-- Trigger or application logic updates this on each new order
UPDATE users SET order_count = order_count + 1 WHERE id = ?;
```

Denormalize only if: (1) the counter/value is expensive to compute, (2) it's queried frequently, (3) writes are infrequent compared to reads. Add comments explaining why denormalization exists.

### Step 6: Design Migration Strategy
Write SQL migrations for schema changes:
```sql
-- Migration: 001_create_users.sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Migration: 002_add_phone_to_users.sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
-- Add index if phone is searchable
CREATE INDEX idx_users_phone ON users(phone);

-- Migration: 003_drop_unused_column.sql
ALTER TABLE users DROP COLUMN legacy_field;
```

Plan zero-downtime migrations: add column, populate data, backfill defaults, then deprecate old code. Never drop columns immediately; deprecate first.

### Step 7: Generate ERD and Query Optimization Hints
Create Entity-Relationship Diagram (visual or text):
```
User (1) ──→ (M) Orders
User (1) ──→ (M) Reviews
Product (1) ──→ (M) Reviews
Order (1) ──→ (M) OrderItems
Product (1) ──→ (M) OrderItems
```

For each complex query, provide hints:
```sql
-- Query: "Get user's total spending with product details"
-- Hint: Use SUM(amount) and JOIN, not N+1 (loop + separate queries)
SELECT
  users.name,
  SUM(orders.amount) as total_spent
FROM users
JOIN orders ON users.id = orders.user_id
WHERE users.id = ?
GROUP BY users.id;

-- Index: CREATE INDEX idx_orders_user_amount ON orders(user_id, amount);
-- Execution: ~1ms with index, ~500ms full table scan without
```

## Output Template

```
# Database Schema: [System Name]

## Entity-Relationship Diagram
\`\`\`
User (1) ──→ (M) Orders
...
\`\`\`

## Normalization Analysis
[Each entity and its normal form compliance]

## Schema Definition

### Users Table
\`\`\`sql
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  ...
);
\`\`\`

[Repeat for other tables]

## Indexes and Performance
- **idx_users_email**: Covers "find user by email" queries (~50ms → ~1ms)
- **idx_orders_user_date**: Composite for range queries, covers 'get user orders'

## Denormalization Decisions
[If any, justify with query patterns]

## Migration Plan
[Script for each version]

## Scale Considerations
[Partitioning, sharding strategy if needed for 100M+ rows]
```

## Quality Gates
- [ ] Schema is normalized to 3NF (or justified denormalization documented)
- [ ] Every table has a primary key
- [ ] Foreign keys defined for all relationships
- [ ] Every index is tied to a specific query pattern
- [ ] Over-indexing avoided (< 1 index per 2 columns on average)
- [ ] Migrations are reversible (can rollback)

## Examples

### Good Output (excerpt)
```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Orders table
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  total_amount DECIMAL(10, 2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CHECK (status IN ('pending', 'shipped', 'delivered', 'cancelled')),
  CHECK (total_amount >= 0)
);

-- Index for common query: "get user's orders"
CREATE INDEX idx_orders_user_created ON orders(user_id, created_at DESC);

-- Covering index to avoid table lookup
CREATE INDEX idx_orders_user_total ON orders(user_id, total_amount) INCLUDE (id, created_at);
```

### Bad Output (what to avoid)
```sql
CREATE TABLE orders (
  id INT,
  user_ids VARCHAR(255),  -- NOT 1NF: list of IDs as string
  amounts VARCHAR(255),   -- NOT 1NF: list of amounts
  total_amount DECIMAL(10, 2)  -- NOT 3NF: depends on amounts, not just order
);
```

## Common Mistakes

1. **Mistake**: Over-indexing every column; indexes slow writes and waste space
   → **Fix**: Index only columns in WHERE, JOIN, and ORDER BY of actual queries. Measure write cost.

2. **Mistake**: Using INT for IDs, running out at 2 billion records
   → **Fix**: Use UUID or BIGINT. Even if you don't expect huge scale, allows merging databases later.

3. **Mistake**: Denormalizing without a maintenance strategy; counter gets out of sync
   → **Fix**: Use triggers or application logic to keep denormalized values consistent. Document the rule.

4. **Mistake**: Forgetting ON DELETE behavior; deleting a user orphans orders
   → **Fix**: Explicitly choose CASCADE (delete orders too) or RESTRICT (prevent deletion). Document the choice.

5. **Mistake**: Not partitioning tables by time; 100M-row table scan becomes slow
   → **Fix**: For time-series data (orders, logs), partition by date range. Queries on recent data are much faster.

## Anti-Patterns

- Never store lists in a single column (`phone_numbers VARCHAR(255)` as "555-1234,555-5678"); normalize to a junction table
- Never use string IDs (UUID as TEXT) without proper indexing; UUIDs need explicit handling for performance
- Never add a column that depends on other columns instead of computing on query; this violates 3NF and creates maintenance burden
- Never ignore query patterns when designing indexes; blindly indexing all columns is wasteful
- Never migrate without a rollback plan; always write reversible migrations in case deployment fails

