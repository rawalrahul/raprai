---
name: etl-pipeline
description: "Design production ETL/ELT pipelines with source profiling, transformation logic, error handling, idempotency, and monitoring for reliable data integration."
category: data
difficulty: advanced
model_boost: "Weak model designs brittle pipelines that fail silently or lack reproducibility"
---

# ETL Pipeline

## Purpose
Data pipelines are the nervous system of analytics—they move, transform, and combine data reliably at scale. This skill systematizes pipeline design from source profiling through monitoring, ensuring data flows reliably, transformations are correct, and failures are caught quickly. The output is a documented, production-ready pipeline specification with error handling and observability.

## When to Use
- Building new data integrations (databases, APIs, files)
- Designing recurring data ingestion workflows
- Establishing data warehousing pipelines
- Creating real-time or scheduled data synchronization
- **Do NOT use when**: One-time data export, or dedicated pipeline tool exists (e.g., managed integrations)

## Instructions

### Step 1: Profile Source Data
Understand data structure, quality, and volume before building pipeline:

**Source investigation checklist:**
```
Data Characteristics:
□ Format: CSV, JSON, database tables, API, log files?
□ Volume: Rows? File size? Daily growth rate?
□ Update frequency: Daily, hourly, real-time?
□ Uniqueness: Primary key defined? Natural key available?
□ Completeness: Missing values common? Where?
□ Consistency: Same schema every load? Encoding issues?

Data Quality Baseline:
□ Null percentage per column (flag if >10%)
□ Duplicate records? (if primary key duplicated, investigate)
□ Data types consistent? (are numbers stored as strings?)
□ Ranges valid? (ages 0-150, prices positive?)
□ Timeliness: How fresh is data? (hourly? daily? 30 days old?)

Example source profile:

SOURCE: orders_api (REST endpoint)
Format: JSON (paginated, 10K records per page)
Volume: 2.5M records/day, ~300MB gzipped
Update freq: Real-time (new records added continuously)
PK: order_id (UUID)
Natural keys: (customer_id, order_date, sequence) for idempotent matching
Schema stability: 2 new fields added last quarter, stable for 3 months
Data quality:
  - Missing values: customer_name (0.2%), discount_code (15%, valid null)
  - Duplicates: 0.1% (transient API failures cause retries)
  - Type issues: amount sometimes string "USD 123.45", sometimes float
  - Latency: Data available 15min after order, complete at 2 hours

Implications for pipeline:
- Need pagination logic (10K batch size)
- Idempotency critical (handle duplicates from retries)
- Type coercion needed (amount field)
- Incremental load based on created_at timestamp
- Partition by date for performance
```

### Step 2: Design Transformation Logic
Define how source data maps to warehouse schema:

**Transformation specification:**
```sql
-- SOURCE: orders_api raw data
-- TARGET: warehouse.orders (fact table)
-- SCHEDULE: Every 15 minutes (near real-time)

-- TRANSFORMATION LOGIC:

1. EXTRACT: Fetch incremental orders from API
   Last processed timestamp: 2026-03-05 14:00 UTC
   Query: GET /orders?created_after=2026-03-05T14:00:00Z&limit=10000
   Pagination: Loop until no records returned

2. LOAD-RAW: Store raw JSON in staging table (before cleaning)
   Table: stage.orders_raw
   Columns: source_data (JSONB), ingestion_timestamp, source_file_path
   Purpose: Preserve original data for debugging/auditing
   Retention: 30 days (rollback window)

3. TRANSFORM: Cleanse, type-coerce, enrich
   source_amount: String (e.g., "USD 123.45")
   → target_amount: Numeric (123.45)
   → Regex: Extract number from currency string

   source_customer_name: Optional
   → target_customer_name: String
   → Fallback: "Unknown" if null (not empty string)

   source_created_timestamp: ISO 8601
   → target_created_date: DATE
   → target_created_hour: HOUR (for time-of-day analysis)
   → Timezone: Convert to UTC explicitly

   source_product_id: Numeric
   → target_product_id: Numeric
   → Lookup: Join to warehouse.products for validation
   → Flag missing products for investigation

4. DEDUPLICATE: Remove API retries (idempotency)
   Primary key: (order_id)
   Duplicates keep: Most recent (by ingestion_timestamp)
   SQL: SELECT DISTINCT ON (order_id) * ORDER BY order_id, ingestion_timestamp DESC

   Natural key deduplication (if order_id not available):
   Keys: (customer_id, order_date, sequence_number)
   Aggregation: SUM(amount), MAX(status) by natural key
   Flag: Log duplicates for source investigation

5. VALIDATE: Quality gates before load
   Checks:
   □ Amount > 0 (no negative orders)
   □ created_date between 2020-01-01 and TODAY (no future dates)
   □ customer_id matches known customers (foreign key check)
   □ Status in ('pending', 'confirmed', 'shipped', 'delivered')

   Invalid row handling:
   - If <1% invalid: Log to quarantine table, alert, don't block load
   - If >1% invalid: Fail pipeline, investigate source issue

   SQL quarantine:
   INSERT INTO stage.orders_quarantine (source_data, validation_errors)
   SELECT source_data, ARRAY['amount <= 0', 'customer_id not found']
   FROM stage.orders_transformed
   WHERE amount <= 0 OR customer_id NOT IN (SELECT customer_id FROM warehouse.customers)

6. LOAD-FINAL: Insert/upsert to fact table
   Table: warehouse.orders
   Strategy: Upsert (insert if new, update if changed)
   SQL: ON CONFLICT (order_id) DO UPDATE SET
        amount = EXCLUDED.amount,
        status = EXCLUDED.status,
        updated_at = NOW()

   Partitioning: By created_date (monthly partitions for speed)
   Index: On order_id (PK), customer_id (FK), created_date (partitioning)

7. LOGGING: Record pipeline execution
   Insert: warehouse.pipeline_log
   Columns: pipeline_name, run_start, run_end, records_extracted,
            records_loaded, records_quarantined, status

   Example: (orders_api_15min, 14:00:00, 14:02:15, 125000, 124750, 250, SUCCESS)
```

### Step 3: Implement Idempotency
Ensure replaying pipeline doesn't corrupt data:

**Idempotency patterns:**

```python
# PATTERN 1: Upsert on natural key
# Running pipeline twice with same data produces same result

# If source provides order_id (surrogate key):
MERGE INTO warehouse.orders t
USING stage.orders_transformed s
ON t.order_id = s.order_id
WHEN MATCHED THEN UPDATE SET
  amount = s.amount,
  status = s.status,
  updated_at = NOW()
WHEN NOT MATCHED THEN INSERT
  (order_id, customer_id, amount, status, created_date)
VALUES
  (s.order_id, s.customer_id, s.amount, s.status, s.created_date)

# Result: Running twice loads same data once (idempotent)

# PATTERN 2: Timestamp-based incremental load
# Only load records changed since last successful run

-- Store last run checkpoint
CREATE TABLE pipeline_checkpoint (
  pipeline_name VARCHAR,
  last_processed_timestamp TIMESTAMP,
  PRIMARY KEY (pipeline_name)
)

-- Load only new/changed records
INSERT INTO warehouse.orders
SELECT * FROM stage.orders_transformed
WHERE updated_timestamp > (
  SELECT last_processed_timestamp
  FROM pipeline_checkpoint
  WHERE pipeline_name = 'orders_api'
)

-- Update checkpoint only after successful load
UPDATE pipeline_checkpoint
SET last_processed_timestamp = NOW()
WHERE pipeline_name = 'orders_api'

# Result: Resuming pipeline after failure continues from checkpoint (no reprocessing)

# PATTERN 3: Partition-based replayability
# Instead of upsert, partition allows replaying date ranges

-- Load October data (can be replayed without affecting Nov/Dec)
DELETE FROM warehouse.orders WHERE created_date >= '2025-10-01' AND created_date < '2025-11-01'
INSERT INTO warehouse.orders
SELECT * FROM stage.orders_transformed
WHERE created_date >= '2025-10-01' AND created_date < '2025-11-01'

# Result: Can reprocess October by just deleting October partitions and reloading
```

### Step 4: Design Error Handling and Recovery
Plan for failures before they happen:

```python
# ERROR HANDLING PYRAMID (order of preference)

Level 1: PREVENT ERRORS (best)
- Validate schema before extraction (API changed? table missing?)
- Type validation during transformation (would string cast work?)
- Duplicate detection before load (have we loaded this before?)

Level 2: ALERT & LOG (when prevention fails)
- Schema validation error → Alert + log detail + pause pipeline
- Data quality error → Log to quarantine table + alert if >threshold
- Network error → Log + retry with exponential backoff

Level 3: GRACEFUL DEGRADATION (when alerts insufficient)
- Connection timeout → Retry 3 times with 30s, 60s, 120s backoff
- Partial load success → Load succeeded records, quarantine failed, report
- Source data missing → Load empty results, don't fail (scheduled load will retry)

Level 4: MANUAL INTERVENTION (last resort)
- Unrecoverable error → Stop pipeline, alert on-call engineer, wait for fix

IMPLEMENTATION EXAMPLE:

def run_etl_pipeline():
    try:
        # Step 1: Validate source schema
        validate_source_schema()  # Fails fast if API changed

        # Step 2: Extract data with retry logic
        data = extract_with_retry(
            url='https://api.example.com/orders',
            max_retries=3,
            backoff_factor=2
        )  # Fails after 3 attempts, logs error

        # Step 3: Transform with error collection
        transformed_data, errors = transform(data)
        if len(errors) > 0.01 * len(data):  # >1% errors
            raise DataQualityError(f"Too many transform errors: {len(errors)}")

        # Step 4: Log errors to quarantine table (don't fail)
        quarantine_errors(errors)

        # Step 5: Load with idempotent upsert
        load_data(transformed_data)

        # Step 6: Log success
        log_pipeline_run(
            status='SUCCESS',
            records_processed=len(data),
            records_loaded=len(transformed_data),
            records_errored=len(errors)
        )

    except SchemaValidationError as e:
        alert_pagerduty(f"ETL CRITICAL: Schema changed: {e}")
        log_pipeline_run(status='FAILED', error=str(e))
        raise

    except DataQualityError as e:
        alert_slack(f"ETL WARNING: Data quality check failed: {e}")
        log_pipeline_run(status='PARTIAL_FAILURE', error=str(e))
        # Don't re-raise; continue

    except ConnectionError as e:
        log_and_retry()  # Orchestrator will retry
        raise

    except Exception as e:
        alert_oncall(f"ETL UNKNOWN ERROR: {e}")
        log_pipeline_run(status='FAILED', error=str(e))
        raise
```

### Step 5: Establish Monitoring and Observability
Create visibility into pipeline health and data freshness:

```
MONITORING METRICS:

Freshness (How recent is data?)
- Metric: MAX(updated_at) - NOW() for warehouse tables
- Target: <2 hours for orders, <1 hour for real-time data
- Alert: If freshness exceeds SLA (e.g., no data in 3 hours)
- Dashboard: Freshness trend chart for all pipelines

Completeness (Did we get all expected data?)
- Metric: Row count from source vs. warehouse
- Expected: 95%+ match (some failures/filters acceptable)
- Alert: If load volume <85% of expected
- Calculation: Compare daily ingestion count to known volume

Quality (Is loaded data correct?)
- Metric: Quarantine rate (% of rows flagged as invalid)
- Target: <0.5% quarantine rate (99.5% quality)
- Alert: If quarantine rate >2%
- Action: Investigate source or transformation logic

Latency (How long does pipeline take?)
- Metric: Total pipeline duration (extract + transform + load)
- Target: <30 min for daily batch, <5 min for hourly
- Alert: If duration 2x baseline (indicates performance degradation)
- Dashboard: Pipeline duration trend (hour/day)

Reliability (Do we complete successfully?)
- Metric: Success rate (successful runs / total runs)
- Target: >99.5% success rate
- Alert: If <95% success in trailing 7 days
- Action: Investigate failure root cause

IMPLEMENTATION (Prometheus-style):

# Freshness metric
warehouse_data_freshness_minutes{table="orders"} 120
warehouse_data_freshness_minutes{table="customers"} 45

# Completeness metric
pipeline_load_ratio{pipeline="orders_api", status="loaded"} 124750
pipeline_load_ratio{pipeline="orders_api", status="quarantined"} 250

# Latency metric
pipeline_duration_seconds{pipeline="orders_api"} 135

# Reliability metric
pipeline_success_rate_percent{pipeline="orders_api", window="24h"} 99.8
```

### Step 6: Document Pipeline Specification
Create replicable, maintainable pipeline documentation:

```
PIPELINE SPECIFICATION DOCUMENT

Name: orders_api_to_warehouse
Purpose: Ingest real-time orders from API, load to analytical warehouse
Frequency: Every 15 minutes
Owner: Data Platform team (Slack: #data-pipelines)
Runbook: https://wiki.company.com/pipelines/orders_api

Source:
  Type: REST API
  URL: https://api.example.com/v2/orders
  Auth: Bearer token in secrets manager (aws-secrets)
  Rate limit: 100 requests/min, 100K records per request
  Pagination: Offset-based (offset parameter)
  Incremental: Yes, based on created_after parameter
  Last run checkpoint stored in: postgresql://warehouse/pipeline_checkpoint

Transformation:
  Language: Python (airflow operator)
  Location: dbt/models/staging/stg_orders.sql
  Key transformations:
    - Type coercion: amount string → numeric
    - Timezone normalization: All timestamps → UTC
    - Deduplication: BY order_id (keep latest)
    - Validation: Amount > 0, status in enum, customer_id in warehouse.customers

Data Quality:
  Quarantine table: stage.orders_quarantine
  Alert threshold: >1% invalid rows
  Investigation: Check alert notification + quarantine table

Load:
  Target: warehouse.orders (fact table)
  Strategy: Upsert on order_id
  Partitioning: By created_date (monthly)
  Post-load validation: Count match expected within ±5%

Monitoring:
  Freshness SLA: <2 hours
  Volume SLA: >95% of expected daily rows
  Success rate: >99% (7-day rolling)
  Dashboard: https://grafana.company.com/d/orders_api

Failure handling:
  Retries: 3 attempts with exponential backoff (30s, 60s, 120s)
  Alerts: PagerDuty (critical) + Slack (warning)
  Manual recovery: See https://wiki.company.com/runbooks/orders_api_outage
  Escalation: Data platform on-call (after 1 hour down)

Backups / Rollback:
  Raw staging tables retained: 30 days (allow reprocessing)
  Partition delete & reload: Can reprocess any date range
  Time-to-recover: 30 minutes (reprocess 1 day of data)

Change management:
  Code review: 2 approvals before deploy
  Testing: Unit tests + staging integration test before production
  Deployment: Thursday EOD (time to fix before weekend)
  Rollback: Instant (previous docker image)
```

## Output Template

**ETL Specification**:
```
Pipeline Name: [name]
Source: [system, format, volume]
Target: [warehouse table, grain, partitioning]
Frequency: [schedule]
Idempotency: [upsert strategy, natural key]
Error Handling: [quarantine logic, alert thresholds]
SLA: [freshness, completeness, latency targets]
Owner: [team, oncall contact]
```

**Monitoring Dashboard**:
```
Freshness: Last data load timestamp
Completeness: Row count loaded vs. expected
Quarantine Rate: % of data rejected
Pipeline Duration: Minutes to complete
Success Rate: % of runs succeeding (24h, 7d, 30d)
```

## Quality Gates

1. **Idempotency**: Pipeline can run twice with same data (no duplication)
2. **Error handling**: Failures caught, logged, alerted (not silent)
3. **Data quality**: Validation gates prevent invalid data load (or quarantine)
4. **Monitoring**: All critical pipeline metrics tracked and alerted
5. **Documentation**: Specification complete, runbook exists for failures
6. **Testing**: Staging integration tests pass before production

## Examples

**Good: Robust production pipeline**
```
Source: Customer API (10K users/day, real-time)
Idempotency: Upsert on customer_id, handle duplicates
Monitoring: Freshness <1hr, completeness 98%+, quality 99.5%
Error handling: Invalid records quarantined (not rejected)
SLA: 99.5% success rate, <5min latency, rollback in 10min
Owner documented, runbook available, tested in staging
```

**Bad: Fragile, unmaintainable**
```
Source: Manual CSV files dropped in shared folder
Processing: One-off Python script, no version control
Monitoring: None (data staleness unknown)
Error handling: Script crashes, manual fix required
Documentation: None ("ask Sarah, she knows how it works")
Testing: None (discovered issues in production)
```

## Common Mistakes

1. **No idempotency**: INSERT without deduplication; replaying pipeline duplicates data
2. **Silent failures**: Pipeline completes with errors quarantined but not alerted
3. **No monitoring**: Data stale for days before anyone notices
4. **Hardcoded values**: Timestamps, IDs, filters baked into scripts; brittle to change
5. **No retry logic**: Transient network error fails entire pipeline
6. **Documentation after-the-fact**: Weeks later, impossible to onboard new person

## Anti-Patterns

1. **"Batch it daily"**: Running daily when incremental hourly possible; accumulates backlog
2. **No natural keys**: Surrogate keys only; can't detect duplicates across systems
3. **Transform in BI tool**: Complex business logic embedded in dashboard; unmaintainable
4. **One master table**: Warehouse has 1 uber-table with all data; impossible to manage
5. **Always recalculate**: Rebuilding 2-year history every run; waste of resources