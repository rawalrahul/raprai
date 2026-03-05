---
name: data-dictionary
description: "Create comprehensive data dictionaries from database schemas and datasets. Document field definitions, data types, valid ranges, business rules, and column lineage."
category: data
difficulty: beginner
model_boost: "Weak model creates incomplete or ambiguous data documentation"
---

# Data Dictionary

## Purpose
Data dictionaries provide authoritative documentation of what data means and how to use it correctly. They translate between technical schemas and business meaning, preventing misinterpretation and enabling self-service analytics. This skill systematizes dictionary creation from schema inspection through business rule documentation.

## When to Use
- Documenting new database schema
- Creating onboarding material for analysts
- Establishing data governance standards
- Supporting data quality and lineage tracking
- **Do NOT use when**: Dictionary already exists and current, or system is deprecated

## Instructions

### Step 1: Audit Database Schema
Systematically inspect tables and columns:

**Schema inspection process:**

```sql
-- Inspect table structure (PostgreSQL example)
SELECT
  table_name,
  column_name,
  data_type,
  is_nullable,
  column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('customers', 'orders', 'products')
ORDER BY table_name, ordinal_position;

-- Result example:
-- Table: customers
  column_name        | data_type                  | is_nullable | column_default
  ---|---|---|---
  customer_id        | uuid                       | NO          | gen_random_uuid()
  email              | character varying(255)    | NO          | NULL
  created_at         | timestamp with time zone  | NO          | now()
  lifetime_value     | numeric(10,2)             | YES         | NULL

-- Inspect constraints and keys
SELECT
  tc.table_name,
  kcu.column_name,
  tc.constraint_type
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
WHERE tc.table_schema = 'public'
  AND tc.table_name IN ('customers', 'orders')
ORDER BY tc.table_name, kcu.ordinal_position;

-- Result example:
-- Table: orders
  constraint_type  | column_name
  ---|---
  PRIMARY KEY      | order_id
  FOREIGN KEY      | customer_id (references customers)
  UNIQUE           | external_order_id

-- Inspect indexes (performance hints)
SELECT
  tablename,
  indexname,
  indexdef
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename;
```

**Data type reference:**

```
NUMERIC TYPES:
- INTEGER: Whole numbers (-2^31 to 2^31-1), 4 bytes
- BIGINT: Large whole numbers, 8 bytes
- NUMERIC(10, 2): Exact decimal (10 total digits, 2 after decimal)
  → Used for: Money, precise calculations
  → Example: 9999999.99 (max value with 10,2)
- FLOAT: Approximate decimal, 8 bytes
  → Used for: Scientific data, approximations acceptable
  → Caveat: 0.1 + 0.2 != 0.3 (floating point rounding)

STRING TYPES:
- VARCHAR(n): Variable-length string, up to n characters
- TEXT: Unlimited-length string
- CHAR(n): Fixed-length string, padded with spaces

TEMPORAL TYPES:
- DATE: Date only (YYYY-MM-DD)
- TIMESTAMP: Date and time with timezone
- TIMESTAMP WITHOUT TIME ZONE: Date and time, no timezone
- Caveat: Always document timezone convention (UTC? Local? Convert on read?)

BOOLEAN:
- true / false (stored as 1 bit)
- Nullable: TRUE, FALSE, or NULL (3 states)

JSON/ARRAY:
- JSONB: JSON binary, supports indexing
- Used for: Flexible nested data, avoiding normalization
- Query: Use -> operator: data->'field_name'
```

### Step 2: Document Each Field
Create entry for every column with complete information:

**Field documentation template:**

```
FIELD NAME: order_id
---|---
Business meaning | Unique identifier for each order
Data type | UUID (universally unique identifier)
Nullable? | No (NOT NULL constraint)
Primary key? | Yes
Default value | gen_random_uuid() (auto-generated)
Example values | 550e8400-e29b-41d4-a716-446655440000
Valid range | Any UUID format
Update frequency | Never (immutable)
Source system | Orders API → ETL → Warehouse
Lineage | sales.orders → stage.orders_raw → warehouse.orders
Sensitivity | Non-sensitive (public identifier)
Documentation | Generated client-side, guaranteed unique across all orders
Known issues | None

Related fields | customer_id (FK), product_id (FK)
Validation rules | Must match orders from source system


FIELD NAME: email
---|---
Business meaning | Customer email address (primary contact)
Data type | VARCHAR(255)
Nullable? | No (NOT NULL)
Primary key? | No (but unique constraint)
Default value | NULL (user provides)
Example values | john.smith@company.com, sarah+test@example.org
Valid range | Valid email format (abc@def.ghi)
Update frequency | Rarely (customer can update)
Source | Customer signup form
Lineage | Customers app → warehouse.customers
Sensitivity | PII (personally identifiable information) - restricted access
Validation | Email format enforced in application layer
Known issues | No validation that email is actively monitored (bounces not detected)
Data quality | 2% invalid format (malformed emails like "user@"), 0.5% duplicates
Related fields | None (primary contact, not linked to other tables)
Alternative contact | backup_email (for alternative contact)


FIELD NAME: amount
---|---
Business meaning | Total order value in customer currency
Data type | NUMERIC(12,2) [12 total digits, 2 after decimal]
Nullable? | No (orders must have amount)
Primary key? | No
Default value | NULL (user/system provides)
Example values | 1234.56, 9999999.99, 0.01
Valid range | 0.00 to 9999999.99 (non-negative, within data type)
Update frequency | Immutable (set at order creation)
Source | Orders API, calculated as SUM(line_item_amount)
Currency | Always customer currency (not USD or base currency)
Lineage | sales.orders → warehouse.orders
Sensitivity | Non-sensitive (business metric)
Validation rules | amount > 0 (non-negative), amount ≤ 1M (sanity check)
Known issues | 0.3% of orders have $0 amount (free trials, samples)
                Timezone effects: Order amount in customer's timezone conversion
Related fields | currency (which currency is this amount in)
Transformation | Normalized to USD in warehouse at load time (exchange_rate applied)


FIELD NAME: status
---|---
Business meaning | Current state of the order in fulfillment pipeline
Data type | VARCHAR(20)
Nullable? | No
Primary key? | No (but state machine constraint)
Default value | 'pending' (at creation)
Example values | pending, confirmed, shipped, delivered, cancelled
Valid range | ENUM: {pending, confirmed, shipped, delivered, cancelled, refunded}
Update frequency | Multiple times (state transitions during fulfillment)
Source | Orders service (state machine updates)
Lineage | sales.orders → warehouse.orders_snapshot (daily snapshot)
Sensitivity | Non-sensitive
State transition rules:
  pending → confirmed (when payment processed)
  confirmed → shipped (when warehouse processes)
  shipped → delivered (when carrier marks delivered)
  shipped → returned (if customer returns)
  (Any state) → cancelled (manual cancellation)
Valid transitions (business rules):
  - INVALID: confirmed → pending (can't go backwards, except cancelled)
  - INVALID: delivered → shipped (no reversion)
Known issues | 0.1% of orders stuck in "pending" >30 days (needs investigation)
                'refunded' status created ad-hoc, not guaranteed in all years
Related fields | created_at (when status=pending), shipped_at (when status=shipped)
Dimension table | dim_order_status (lookup of status descriptions)
```

### Step 3: Map Data Types and Constraints
Document valid ranges and business rules:

**Data type and constraint matrix:**

```
TABLE: warehouse.orders

Column | Data Type | NOT NULL | PK | FK | UNIQUE | Check | Default
---|---|---|---|---|---|---|---
order_id | UUID | ✓ | ✓ | | ✓ | | gen_random_uuid()
customer_id | UUID | ✓ | | ✓ | | | NULL
amount | NUMERIC(12,2) | ✓ | | | | amount > 0 | NULL
currency | VARCHAR(3) | ✓ | | | | currency IN ('USD','EUR','GBP') | 'USD'
status | VARCHAR(20) | ✓ | | | | status IN ('pending','confirmed',...) | 'pending'
created_at | TIMESTAMP | ✓ | | | | created_at ≤ NOW() | now()
updated_at | TIMESTAMP | ✓ | | | | | now()

Interpretation:
- order_id: Auto-generated, must exist, uniquely identifies order
- customer_id: Must reference existing customer, same UUID type ensures join integrity
- amount: Must be positive, at least $0.01
- currency: Restricted to 3-letter ISO codes
- status: Restricted to enumerated values
- created_at: Cannot be future date (catches data errors)


BUSINESS RULES (enforced outside database):

1. Order immutability: Once created, order_id, customer_id, amount cannot change
   → Enforcement: Application layer (no UPDATE on these columns)
   → Rationale: Audit trail, financial compliance

2. Status flow: Status must follow valid state transitions
   → Valid: pending → confirmed → shipped → delivered
   → Invalid: delivered → shipped (no reversion except cancel)
   → Enforcement: Application state machine (not database constraint)
   → Rationale: Workflow integrity

3. Currency consistency: Within order, all line items must use same currency
   → Enforcement: Database trigger or application validation
   → Rationale: Avoid accidental currency mixing (leads to reconciliation errors)

4. Reconciliation: order.amount = SUM(order_items.amount * quantity)
   → Enforcement: Calculated column or post-load validation
   → Rationale: Prevents arithmetic errors

5. Timezone handling: All timestamps stored as UTC
   → Enforcement: Application must convert to UTC before insert
   → Rationale: Consistent time basis across regions
```

### Step 4: Define Column Lineage
Track where data originates and how it transforms:

**Lineage documentation:**

```
COLUMN: warehouse.orders.amount

SOURCE SYSTEM: Orders API (REST endpoint)
├─ API endpoint: GET /v2/orders
├─ Field name: order_total (different name in source!)
├─ Data type in source: String (e.g., "USD 1234.56")
└─ Extraction: Daily batch at 2am UTC

TRANSFORMATION PIPELINE:
1. Extract:
   Source: orders_api.orders_raw (raw JSON from API)
   SQL: SELECT data->'order_total' as amount_raw
   Type: String

2. Clean:
   SQL: CAST(REGEXP_REPLACE(amount_raw, '[^\d.]', '') as NUMERIC)
   Result: Remove currency prefix, convert to number
   Output type: NUMERIC

3. Normalize (if multi-currency):
   SQL: amount_numeric * exchange_rates.rate
   where order_currency = exchange_rates.currency
   and exchange_rates.date = order_date
   Result: Convert all to USD for comparison
   Output: NUMERIC(12,2)

4. Load:
   Target: warehouse.orders.amount
   Update strategy: Upsert on order_id
   Output: NUMERIC(12,2)

LINEAGE DIAGRAM:
orders_api.orders_raw.data->'order_total' (string)
         ↓ (transform: remove currency, cast to numeric)
stage.orders_transformed.amount (numeric)
         ↓ (upsert on order_id)
warehouse.orders.amount (numeric, final)
         ↓ (used by)
mart.orders_summary (aggregations, reporting)

DEPENDENCIES:
- Depends on: exchange_rates table (for currency conversion)
- Depends on: order_date field (for exchange rate lookup)
- Used by: revenue reporting, margin calculations
- Downstream tables: 47 views and dashboards

VALIDATION:
- Pre-load: amount > 0 (sanity check)
- Post-load: COUNT(warehouse.orders) = COUNT(stage.orders_raw) ±5% tolerance
- Data quality metric: 99.8% of amounts within expected range

OWNER: Data Platform team
Documentation: https://wiki.company.com/columns/orders-amount
Last updated: 2026-03-05
```

### Step 5: Document Sensitive and Quality Metadata
Flag sensitive data and known quality issues:

**Sensitivity and quality matrix:**

```
Column | Sensitivity | PII? | Encryption | Retention | Known Issues
---|---|---|---|---|---
customer_id | Non-sensitive | No | No | Permanent | None
email | Sensitive | Yes | At rest | Per customer request | 2% invalid format
payment_method | Highly sensitive | Yes | At rest + transit | N/A (not stored) | None
order_amount | Non-sensitive | No | No | 7 years (legal) | 0.3% $0 (free trials)
product_name | Non-sensitive | No | No | Permanent | 5 names deprecated, variants used
created_at | Non-sensitive | No | No | Permanent | 1.2% in future (data entry error)
customer_feedback | Sensitive | Possibly | No | 2 years | 15% missing (not mandatory)

SENSITIVITY DEFINITIONS:

Non-sensitive: Public information, no privacy/security risk
├─ Examples: Product names, order amounts, order status
├─ Access: Any analyst
└─ Storage: Standard databases acceptable

Sensitive: Personally identifiable, privacy risk if exposed
├─ Examples: Names, emails, addresses
├─ Access: Restricted to authorized analysts
├─ Storage: Encrypted at rest, limited retention
└─ Deletion: Support customer right-to-forget (GDPR, CCPA)

Highly sensitive: Financial/auth data, critical if compromised
├─ Examples: Credit card numbers, passwords, SSN, bank accounts
├─ Access: Only system admin, never in warehouse
├─ Storage: Tokenized or encrypted, minimal retention
├─ Transmission: HTTPS only, encrypted end-to-end
├─ Deletion: Immediately after transaction
└─ Audit: All access logged

KNOWN DATA QUALITY ISSUES:

Column: created_at
Issue: 1.2% of values are future dates (past midnight)
Severity: Medium (breaks analysis of "recent orders")
Root cause: Timezone mismatch (client sends local time, not UTC)
Mitigation: Validation rule added 2025-12-01, future issues prevented
Remediation: NULL future dates in historical data, or cap at NOW()
Identified: 2025-10-15
Status: Monitoring (check quarterly)

Column: product_id
Issue: 5 product IDs deprecated, customers still reference them
Severity: High (joins fail, missing products)
Root cause: Legacy data not migrated
Mitigation: Map deprecated IDs to current product via lookup table
Lookup: product_id_mapping (old_id → new_id)
Remediation: N/A (historical, immutable)
Identified: 2025-08-01
Status: Ongoing (use lookup for analysis)

DATA QUALITY METRICS:

Column | Completeness | Uniqueness | Validity | Freshness
---|---|---|---|---
customer_id | 100% | 100% | 100% | Hourly
email | 99.8% | 99.2% | 98% | Real-time
amount | 100% | N/A | 99.7% | Daily
status | 100% | N/A | 100% | Daily
```

### Step 6: Create Data Dictionary Artifact
Compile into maintainable reference document:

```markdown
# Data Dictionary: Production Warehouse

**Version**: 2.1
**Last Updated**: 2026-03-05
**Owner**: Data Platform team
**Contact**: #data-platform Slack

## Table of Contents
1. Overview
2. Table Schemas
3. Sensitive Data Classification
4. Known Quality Issues
5. Column Lineage
6. Change Log

---

## 1. Overview

Database: warehouse (PostgreSQL)
Schema: public
Purpose: Analytical data warehouse for business intelligence
Update frequency: Daily (nightly batch) + Real-time for critical tables
Access control: Role-based (see access_control.md)
Partitioning: Tables > 100M rows partitioned by date

---

## 2. Table Schemas

### Table: orders

**Purpose**: Fact table of customer orders

**Grain**: One row per order

**Key metrics**:
- Total orders: 50M+ rows
- Daily growth: 45K orders/day
- Partitioning: By created_date (monthly)
- Storage: 12GB

| Column | Type | Nullable | Description | Example |
|--------|------|----------|-------------|---------|
| order_id | UUID | No | Primary key, auto-generated | 550e8400-e29b-41d4 |
| customer_id | UUID | No | Foreign key to customers | (same format) |
| amount | NUMERIC(12,2) | No | Total order value | 1234.56 |
| currency | VARCHAR(3) | No | ISO currency code | USD |
| status | VARCHAR(20) | No | Fulfillment state | pending / confirmed |
| created_at | TIMESTAMP | No | Order creation time (UTC) | 2026-03-05 14:23:45 |
| updated_at | TIMESTAMP | No | Last update time | 2026-03-05 15:01:22 |

**Business rules**:
- amount must be > 0
- status follows valid transitions (see business rules in field docs)
- created_at cannot be future date
- customer_id must exist in customers table

**Known issues**:
- 0.3% of orders have amount=$0 (free trials) - expected, not error
- 1.2% have created_at > NOW() (timezone issue) - planned remediation Q2 2026

---

## 3. Sensitive Data Classification

| Column | Table | Classification | Retention | Encryption |
|--------|-------|-----------------|-----------|------------|
| email | customers | Sensitive | Customer deletion + 30d | At rest |
| payment_method | payments | Highly sensitive | 0 days (not stored) | N/A |
| credit_score | customers | Sensitive | 3 years | At rest |

Access restricted to: Analytics Manager role and above
Audit logging: All access logged in audit_trail table

---

## 4. Known Quality Issues

See quality_issues.md for full tracking

**Issue**: Deprecated products still in orders
Status: Open
Mitigation: Use product_id_mapping lookup
ETA: Q3 2026 (legacy data cleanup)

**Issue**: Email format validation (2% invalid)
Status: In remediation
Fix: Email validation added to customer signup Jan 2026
Affects: emails before 2026-01-01

---

## 5. Column Lineage

### orders.amount
Source: orders_api.order_total (string, includes currency)
Transform: Remove currency, cast to NUMERIC
Final: warehouse.orders.amount (NUMERIC(12,2), USD)
Used by: Revenue reports, margin calculations

[Complete lineage for all columns...]

---

## 6. Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-03-05 | Added customer_segment column | GTM segmentation analysis |
| 2026-02-20 | Deprecated product_type column | Replaced with product_category |
| 2026-01-15 | Updated email validation | Privacy compliance |
```

## Output Template

**Data Dictionary Document** (typical structure):
```
- Schema overview (tables, relationships)
- Each table documented (purpose, grain, key metrics)
- Each column documented (type, meaning, examples, rules)
- Sensitive data flagged (classification, access controls)
- Known quality issues listed (with mitigations)
- Lineage for major columns (source → warehouse)
- Business rules and constraints
- Access control by role
- Contact for questions
```

## Quality Gates

1. **Completeness**: Every column documented (no missing entries)
2. **Clarity**: Definitions clear enough that analyst can use without asking
3. **Accuracy**: Examples match actual data, business rules correct
4. **Currency**: Last updated < 3 months ago
5. **Lineage**: Source system and transformations documented for key metrics
6. **Sensitivity**: All PII/sensitive columns flagged and classified

## Examples

**Good: Complete, clear, actionable**
```
Column: customer_segment
Data type: VARCHAR(20)
Values: Enterprise | Mid-market | SMB | None
Update: When customer upgrades (weekly refresh from billing system)
Sensitivity: Non-sensitive (used for segmentation, not private)
Quality: 100% populated, validated against customer_size
Lineage: billing.customer → dim_customers.customer_segment → orders view
Used by: Revenue reports, marketing analysis, sales dashboards
Known issue: None
```

**Bad: Vague, incomplete**
```
Column: category
Data type: "text"
Values: "various categories"
Quality: "checked"
Notes: "ask Sarah if unclear"
```

## Common Mistakes

1. **No sensitivity flagging**: PII in dictionary but not marked as restricted
2. **Outdated documentation**: Dictionary not updated when schema changes
3. **No examples**: Type documented but no sample values shown
4. **Vague descriptions**: "customer data" instead of "email of paying customer"
5. **Missing lineage**: No indication where data comes from or how it transforms
6. **No quality notes**: Known issues not documented (analysts waste time investigating)

## Anti-Patterns

1. **"See code for definition"**: Pointing to SQL instead of explaining meaning
2. **Copy-paste from schema**: "VARCHAR(255)" without business context
3. **No validation rules**: Types documented but business constraints missing
4. **Dictionary as spreadsheet**: Hard to maintain, versions diverge
5. **Build during incident**: Writing dictionary after analyst finds inconsistency