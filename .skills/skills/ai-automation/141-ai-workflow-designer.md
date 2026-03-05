---
name: ai-workflow-designer
description: "Design end-to-end AI automation workflows with trigger identification, data flow mapping, model orchestration, fallback strategies, and cost estimation. Covers scheduled, event-driven, and user-initiated workflows with real-world examples."
category: ai-automation
difficulty: intermediate
model_boost: "Fixes weak models' inability to plan multi-step automation sequences, specify APIs/endpoints, and estimate infrastructure costs"
---

# AI Workflow Designer

## Purpose
This skill teaches you to architect complete AI automation pipelines that integrate triggers, data transformations, model calls, fallback strategies, and monitoring. You'll learn to design workflows for production deployment with graceful degradation, cost controls, and human-in-loop checkpoints. This is the foundation for complex automation across email, documents, customer service, and data processing.

## When to Use
- Designing workflows with 3+ sequential AI steps or parallel branches
- Integrating multiple APIs, models, or databases
- Building systems that must handle failures gracefully
- Planning cost-constrained automation (need cost estimation)
- Creating workflows that toggle between automated and human-reviewed decisions
- **Do NOT use when**: Single API call tasks, synchronous-only processes without retry needs, or one-off scripts that don't need monitoring

## Instructions

### Step 1: Identify Trigger Types and Activation Patterns
Define how your workflow starts. Three primary trigger categories:

**Scheduled Triggers** (time-based):
- Cron expressions (0 9 \* \* 1 = Monday 9am UTC)
- Use cases: daily digest compilation, weekly report generation, monthly data cleanup
- Implementation: Cloud Functions with Cloud Scheduler, Lambda + EventBridge, Temporal, Airflow DAGs
- Consideration: Account for timezone skew—always explicit about UTC vs local time

**Event-Driven Triggers** (reactive):
- Webhook events: email received, file uploaded, form submitted, database record created
- Pub/Sub events: Google Pub/Sub, AWS SNS/SQS, RabbitMQ, Kafka
- Use cases: Process support tickets immediately, tag documents on upload, validate form submissions
- Implementation: Set up HTTP endpoint with signature verification (HMAC-SHA256), parse event payload, enqueue to processing queue
- Idempotency: Add request ID to event payload; deduplicate by ID in database

**User-Initiated Triggers** (on-demand):
- HTTP API endpoint, Slack command (/analyze this), UI button click
- Implementation: REST endpoint with authentication (API key or OAuth token)
- Response strategy: Return job ID immediately with webhook callback or polling URL for async results

Example trigger specification:
```
Trigger: Email arrives in support@company.com
Type: Event-driven (Gmail → Pub/Sub)
Payload: {
  message_id: "...",
  from: "customer@example.com",
  subject: "...",
  body: "...",
  timestamp: "2024-01-15T10:30:00Z"
}
Latency SLA: Complete within 2 minutes
```

### Step 2: Map Data Flow (Input → Transforms → Output)
Create a detailed data flow diagram showing how information moves through your workflow.

**Input Schema Definition** (validate early):
```yaml
email_triage_input:
  message_id: string (unique identifier)
  from: string (email regex validation)
  subject: string (max 500 chars)
  body: string (max 100k chars)
  labels: list[string] (existing Gmail labels)
  attachments:
    - filename: string
      mime_type: string
      url: string (signed, expires in 1 hour)
```

**Transformation Steps** (explicit about data mutations):
1. **Extraction**: Parse unstructured data into fields
   - Extract customer ID from email signature using regex or Claude's extraction
   - Retrieve customer account context from database (past issues, subscription tier)
   - Extract attachments, store in temporary Cloud Storage, generate signed URLs

2. **Enrichment**: Add context and metadata
   - Call customer service API to fetch account status, recent interactions
   - Check knowledge base for similar issues (semantic search)
   - Classify email urgency using fine-tuned classifier or prompt-based heuristic

3. **Validation**: Check against business rules
   - Verify email sender is registered customer (check customer database)
   - Check for duplicate issues (semantic similarity to last 30 days of tickets)
   - Validate attachments: size < 50MB, no malware signatures

4. **Transformation**: Convert to canonical format
   - Normalize text (lowercase, remove URLs for safety)
   - Structure into standardized ticket object:
   ```python
   Ticket(
       id: str,
       customer_id: str,
       priority: Literal['low', 'medium', 'high', 'critical'],
       category: str,  # product, billing, account, other
       summary: str,
       body: str,
       attachments: list[Attachment],
       metadata: dict
   )
   ```

**Output Schema** (what leaves the workflow):
```yaml
workflow_output:
  ticket_id: string (unique, persisted to database)
  routing_destination: enum [support_queue, kb_article, auto_response]
  response_template: string (pre-filled email draft)
  priority: enum [low, medium, high, critical]
  confidence: float (0.0-1.0)
  processing_time_ms: integer
```

### Step 3: Select Models and APIs for Each Step
Match capability to task; avoid over-specifying (GPT-4 for everything) or under-specifying (cheap model for critical classification).

**Classification Task** (email priority + category):
- Option A: Fine-tuned small model (Llama 2 7B quantized, ~50MB)
  - Cost: ~$0.001 per call (running self-hosted)
  - Latency: 200ms on CPU, 50ms on GPU
  - Best for: High volume (1000s/day), latency-sensitive
  - Training data: 500+ labeled email samples

- Option B: Few-shot prompt with Claude 3 Haiku
  - Cost: $0.005 per call (0.2K input + 0.1K output tokens)
  - Latency: 1-2s (API call + network)
  - Best for: Low volume (<100/day), complex reasoning needed
  - No training required; adapt via prompt

- Decision matrix:
  - Volume < 100/day + complex logic → Haiku
  - Volume > 1000/day + stable patterns → Fine-tuned model
  - Volume 100-1000/day + some edge cases → Haiku + fallback to human review

**Extraction Task** (customer ID, attachments, action items):
- Claude's tool_use for structured extraction
  ```python
  tools = [
      {
          "name": "extract_ticket_info",
          "description": "Extract customer ID, urgency, and action items from email",
          "input_schema": {
              "type": "object",
              "properties": {
                  "customer_id": {"type": "string"},
                  "urgency": {"enum": ["low", "medium", "high"]},
                  "action_items": {"type": "array", "items": {"type": "string"}}
              }
          }
      }
  ]
  ```

**Search/Retrieval Task** (find similar past issues):
- Embedding model: sentence-transformers/all-MiniLM-L6-v2 (22MB, 384-dim)
  - Generate embedding of customer email (370ms on CPU)
  - Query vector database with top-10 semantic search
  - Alternative: Jina AI embeddings API (~$0.02 per 1M tokens)

**Routing Logic** (rule-based vs ML):
- Simple decision tree if < 5 rules:
  ```python
  if priority == 'critical' and category == 'billing':
      destination = 'priority_queue'
  elif category == 'product' and len(similar_articles) > 0:
      destination = 'kb_article'
  else:
      destination = 'general_queue'
  ```
- ML classifier if > 10 rules or overlap/ambiguity

### Step 4: Design Fallback Strategies and Graceful Degradation
Plan what happens when any step fails or times out.

**Fallback Levels** (in order of execution):
1. **Immediate Retry** (transient failures):
   - Network timeout / 5xx errors → Exponential backoff (1s, 2s, 4s, 8s, max 3 retries)
   - Embeddings API down → Use cached embedding from similar email, note degradation

2. **Alternative Model/Service**:
   - Primary: Claude 3 Haiku for classification
   - Fallback: Rule-based heuristic (keyword matching) + human review flag
   ```python
   try:
       result = classify_with_haiku(email)
   except APIError:
       result = classify_with_rules(email)
       result['requires_human_review'] = True
   ```

3. **Reduced Functionality**:
   - Can't access customer database? Proceed with email info only, skip account context
   - Can't generate embedding? Use TF-IDF search instead of semantic search
   - Attachment parsing fails? Quarantine attachment, continue processing email

4. **Human-in-Loop**:
   - Critical failures (unable to parse email) → Send to human queue with full context
   - Low confidence classification (< 0.65) → Add to manual review batch
   - Attachment virus scan failed → Flag for security team

5. **Graceful Abort**:
   - If workflow fails > 3 times → Stop and send alert to ops
   - If cost exceeds daily budget → Disable workflow, escalate to manager
   - If SLA violated (>10 min to process) → Log incident, send user notification

**Implementation Pattern** (with structured error handling):
```python
class WorkflowExecutor:
    async def execute(self, trigger_event):
        try:
            # Step 1: Parse & validate
            email = await self.parse_email(trigger_event)
            await self.validate_input(email)

            # Step 2: Enrich with retries
            try:
                customer = await self.fetch_customer(email.from, retries=3)
            except CustomerNotFound:
                customer = None  # Graceful degradation

            # Step 3: Classify with fallback
            try:
                priority = await self.classify_priority(email, timeout=2s)
            except TimeoutError:
                priority = self.classify_with_rules(email)
                await self.log_degradation('classification_timeout')

            # Step 4: Route
            routing = self.compute_routing(priority, customer)

            # Step 5: Persist and notify
            ticket = await self.save_ticket(email, routing)
            await self.notify_handler(ticket)

            return {'ticket_id': ticket.id, 'status': 'success'}

        except Exception as e:
            # Log full error + telemetry
            await self.log_failure(e, trigger_event)

            # Route to human
            await self.escalate_to_human(trigger_event, error=str(e))
            return {'status': 'escalated', 'reason': str(e)}
```

### Step 5: Error Handling and Retry Logic
Design explicit retry strategies for each failure mode.

**Retry Configuration** (per API/service):
- Transient network errors (ConnectionError, Timeout): Exponential backoff 1s→2s→4s→8s, max 3 retries
- Rate limit (429): Exponential backoff with jitter, read Retry-After header
- Service unavailable (503): Back off aggressively, check health endpoint
- Invalid input (400): Do not retry; log as permanent failure

**Dead Letter Queue** (for unrecoverable failures):
```python
class DeadLetterQueue:
    async def enqueue_failure(self, event, error, step_name):
        await db.insert('dead_letter_queue', {
            'event_id': event['message_id'],
            'raw_event': json.dumps(event),
            'error': str(error),
            'failed_step': step_name,
            'timestamp': datetime.now(),
            'retry_count': event.get('retry_count', 0),
            'status': 'pending_review'
        })
        # Alert: Send to Slack if >= 5 failures in last hour
        recent = await db.count('dead_letter_queue',
            where="status='pending_review' AND timestamp > now() - interval 1 hour")
        if recent >= 5:
            await slack.post(f"⚠️ {recent} workflow failures in past hour")
```

**Idempotency Keys** (prevent duplicate processing):
- Generate deterministic key: `workflow_id + event_id + step_number`
- Before processing, check cache: "Have we processed this before?"
- If yes: Return cached result instead of re-executing
- Prevents double-charging, double-ticketing, etc.

### Step 6: Cost Estimation Per Execution
Calculate actual costs to run one instance of your workflow.

**Cost Breakdown Example** (email triage workflow):
```
Per Email Processed:
1. Parse & store email (Cloud Storage): $0.0000004 (1KB write)
2. Generate embedding (sentence-transformers): $0.00 (self-hosted, amortized)
3. Vector search (Pinecone starter): $0.00005 (1 query)
4. Classify with Haiku: $0.0005 (150 input + 50 output tokens)
5. Fetch customer from database: $0.00001 (1 read operation, Cloud Firestore)
6. Send email response: $0.0001 (SendGrid)

Total: ~$0.00065 per email
Daily budget: 500 emails = $0.325
Monthly: 15,000 emails = $9.75

Cost controls:
- Max 1,000 emails/day (rate limit)
- Batch-process at 2am UTC (cheaper off-peak hours)
- Skip embedding search for internal emails (cost optimization)
```

**Real-world API costs** (2024 pricing):
| Service | Cost | Per |
|---------|------|-----|
| Claude 3 Haiku | $0.25 | 1M input tokens |
| Claude 3 Opus | $15 | 1M input tokens |
| OpenAI GPT-4 | $30 | 1M input tokens |
| Pinecone (Starter) | $0.04 | 1M vectors/month |
| Weaviate Cloud | $25 | Base + $0.001 per query |
| Embedding API (Jina) | $0.02 | 1M tokens |

**Cost optimization strategies**:
- Batch requests (process 100 emails in one batch vs 100 separate calls)
- Use cheaper model for high-volume steps (Haiku vs Opus)
- Cache embeddings (don't re-embed same text)
- Implement circuit breaker (if cost/hour > threshold, pause workflow)

### Step 7: Monitoring, Alerting, and Observability
Set up production monitoring to detect issues early.

**Key Metrics to Track**:
```python
# Success metrics
successful_runs: Counter[workflow_id, timestamp]
success_rate: success_runs / total_runs
sla_compliance: runs_completed_within_sla / total_runs

# Performance metrics
execution_duration_ms: Histogram[workflow_id, step_name]
latency_p50: 1200ms
latency_p99: 5000ms

# Quality metrics
model_confidence: Histogram[step_name, value]
human_overrides: Counter[step_name, correct_override]

# Cost metrics
api_cost_usd: Counter[workflow_id, service_name]
daily_spend: sum of api_cost_usd
cost_per_execution: sum / total_runs

# Error metrics
failures_by_step: Counter[step_name, error_type]
retry_rate: retries / total_attempts
dead_letter_queue_size: count
```

**Alert Rules** (using Prometheus/Datadog):
```yaml
alert:
  - name: HighErrorRate
    expr: (1 - success_rate) > 0.05  # > 5% failure
    for: 5m
    action: PagerDuty alert + auto-disable if > 10%

  - name: SLAViolation
    expr: latency_p99 > 10000  # > 10 second latency
    for: 15m
    action: Slack notification

  - name: HighCost
    expr: cost_per_execution > baseline * 1.5
    for: 1h
    action: Log and review, potential bug in cost estimation

  - name: DLQAccumulation
    expr: dead_letter_queue_size > 10
    for: 30m
    action: Page oncall engineer to investigate
```

**Structured Logging** (every execution):
```json
{
  "workflow_id": "email_triage_v2",
  "execution_id": "exec_abc123",
  "timestamp": "2024-01-15T10:30:45Z",
  "status": "success",
  "steps": [
    {"name": "parse", "duration_ms": 45, "status": "success"},
    {"name": "classify", "duration_ms": 1200, "status": "success", "model": "haiku", "confidence": 0.87},
    {"name": "route", "duration_ms": 15, "status": "success", "destination": "support_queue"},
    {"name": "notify", "duration_ms": 300, "status": "success"}
  ],
  "total_duration_ms": 1560,
  "cost_usd": 0.00065,
  "input_tokens": 1500,
  "output_tokens": 250
}
```

## Output Template

**Workflow Design Document**:
```markdown
# [Workflow Name] Architecture

## Overview
[1-2 sentence description of what this workflow automates]

## Triggers
- Type: [scheduled|event-driven|user-initiated]
- Frequency: [if scheduled]
- Event source: [if event-driven]
- SLA: Complete within [X minutes]

## Data Flow
[ASCII diagram or detailed text description]
Input → Parse → Enrich → Classify → Route → Persist → Notify

## Step Details
| Step | Action | Model/Service | Cost | Timeout | Fallback |
|------|--------|----------------|------|---------|----------|
| Parse | Extract fields | Regex + Claude | $0.0001 | 5s | Rules-based |
| Classify | Priority + Category | Haiku | $0.0005 | 3s | Rule-based |
| Route | Select destination | Decision tree | $0.0 | 1s | Manual review |

## Error Handling
- Transient failures: Exponential backoff 1s-8s, max 3 retries
- Permanent failures: Escalate to DLQ + human review
- Cost spike: Disable workflow, alert ops

## Cost & SLA
- Cost per execution: $0.00065
- Monthly cost (15k events): $9.75
- Success rate SLA: 99.5%
- Latency SLA: P99 < 5 seconds
```

## Quality Gates

1. **Latency within SLA**: P99 latency ≤ specified threshold (measure over 1 week)
2. **Error rate < 2%**: Total failures / total executions ≤ 0.02
3. **Cost per execution within budget**: Actual cost ≤ estimated cost × 1.1
4. **Human override rate < 5%**: Incorrect automated decisions ≤ 5% of samples
5. **Idempotency verified**: Re-running workflow with same input produces same output
6. **Fallback coverage**: Every step has documented fallback strategy
7. **Monitoring in place**: All metrics defined, alerts configured, dashboards created

## Examples

### Good Workflow Design: Email Triage
```
Trigger: Email arrives
Input Validation: Check sender is registered customer (reject if not)
Enrichment: Fetch customer account + recent tickets
Classification: Use Haiku to classify priority/category (with rules fallback)
Routing: Decision tree → support_queue / kb_article / auto_response
Persistence: Write ticket to database, generate tracking ID
Notification: Send auto-response email with ticket ID
Monitoring: Track success rate, classification accuracy, cost

SLA: 2 minute completion
Cost: $0.0006/email
Error handling: Failures → dead letter queue + page oncall if > 5 in 1 hour
```

### Bad Workflow Design: Instruction Ambiguity
```
❌ "Use AI to process emails" (too vague)
   - Which AI model? Haiku? Opus? Fine-tuned model?
   - What if it fails? No fallback specified
   - What's the cost? Not estimated
   - What's the SLA? Not specified
   - How to monitor? No metrics defined

✓ Fixed: See "Good Workflow Design" above
```

## Common Mistakes

1. **Ignoring Latency in Multi-Step Workflows**
   - ❌ Each step takes 1s, workflow has 10 steps = 10s total (violates 5s SLA)
   - ✓ Parallelize independent steps, use async operations, pre-compute where possible
   - ✓ Test end-to-end latency; measure P99, not just average

2. **No Cost Control / Budget Overflow**
   - ❌ Using GPT-4 Turbo for every step (high volume) = $1000+/month unexpectedly
   - ✓ Estimate cost per execution upfront, implement cost alerts, use cheaper models for high-volume steps
   - ✓ Add circuit breaker: if hourly cost > threshold, pause workflow

3. **Missing Idempotency / Duplicate Processing**
   - ❌ Processing same email twice = double-charged, duplicate ticket created
   - ✓ Generate deterministic idempotency key (event_id + step), cache results
   - ✓ Check for duplicates in database before inserting

4. **Inadequate Fallback Strategy**
   - ❌ API down = entire workflow fails, 0% success rate
   - ✓ Design multi-level fallbacks: retry → alternative model → rule-based → human review
   - ✓ Test fallback paths; measure success rate with primary service degraded

5. **No Dead Letter Queue / Lost Events**
   - ❌ Failures silently drop events; customer never gets response
   - ✓ Implement DLQ for all unrecoverable failures; alert on accumulation
   - ✓ Periodic audit: check DLQ backlog, replay, fix root cause

6. **Inadequate Observability**
   - ❌ Workflow fails silently; ops discovers hours later via customer complaint
   - ✓ Log every step with structured JSON (status, duration, cost, errors)
   - ✓ Set up alerts: error rate > 5%, latency > threshold, cost spike

## Anti-Patterns

1. **Linear Blocking Workflow Instead of Async**
   - ❌ Step 1 → wait for response → Step 2 → wait → Step 3 (synchronous blocking)
   - ✓ Enqueue event → Step 1 immediately returns → Step 2 processes asynchronously
   - Impact: Latency for user feedback vs latency for completion are different

2. **Trying to Handle All Errors with Single Retry**
   - ❌ `for i in range(3): try: execute() except: continue` (naive retry)
   - ✓ Classify errors (transient vs permanent), apply appropriate retry strategy
   - Impact: Transient errors retry quickly; permanent errors fail fast

3. **No Cost Visibility / Uncontrolled Spending**
   - ❌ "It's cheap, just use GPT-4 for everything" → $5000/month surprise
   - ✓ Estimate, monitor, alert, optimize before scaling
   - Impact: Monthly AI spend spirals without control

4. **Workflow State Not Persisted / Lost Progress**
   - ❌ If workflow crashes mid-execution, state lost; must restart from beginning
   - ✓ After each step, persist state to database; resume from checkpoint on retry
   - Impact: Large workflows become inefficient; expensive steps rerun unnecessarily

5. **No Differentiation Between Latency Types**
   - ❌ "Workflow must complete in 1 second" is wrong if step requires 2s API call
   - ✓ Distinguish: User response latency (wait for API response), execution latency (end-to-end processing)
   - Impact: Misaligned expectations; impossible SLAs
