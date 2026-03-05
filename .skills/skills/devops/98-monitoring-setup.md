---
name: monitoring-setup
description: "Design comprehensive monitoring using RED/USE metrics, structured logging, smart alerting rules, dashboard layout, and SLO/SLI definitions to detect problems before customers do."
category: devops
difficulty: advanced
model_boost: "Fixes flying blind on production health and alert fatigue from poor metrics"
---

# Monitoring Setup

## Purpose

You can't fix what you can't see. Monitoring makes system health visible, surfacing problems before customers discover them. But bad monitoring—missing metrics, alert fatigue from false alarms, dashboards no one reads—is as bad as no monitoring. This skill provides a framework: RED/USE metrics to track, logging strategy, alerting rules that actually matter, dashboard design, and SLO/SLI definitions. You'll exit with a monitoring setup that catches real problems and ignores noise.

## When to Use

- You're setting up monitoring for the first time
- Your team ignores alerts (alert fatigue)
- You're building dashboards but not sure what metrics matter
- You're defining SLOs for customers
- You want to reduce MTTR (mean time to resolution)
- You have a production system and want visibility
- **Do NOT use when**: You're pre-launch or have no users (premature optimization)

## Instructions

### Step 1: Define Core Metrics Using RED and USE

Two frameworks cover most scenarios.

**RED Metrics** (for user-facing services):

- **Rate**: Requests per second (RPS)
- **Errors**: Number or percentage of failed requests
- **Duration**: Latency (p50, p95, p99)

**USE Metrics** (for resources: CPU, memory, disk, network):

- **Utilization**: Percentage of resource in use (CPU%, memory%, disk%)
- **Saturation**: Queue depth, threads waiting (indicates bottleneck)
- **Errors**: Failed I/O, dropped packets, etc.

**Example: Web API**

```
RED Metrics:
- Rate: 1,000 requests/second (normal)
- Errors: 0.5% error rate (p99 latency breaches)
- Duration: p50=50ms, p95=200ms, p99=500ms

USE Metrics:
- Utilization: CPU 45%, memory 60%, disk 70%
- Saturation: 0 threads waiting (good), queue depth 0 (good)
- Errors: 0 failed I/O, 0 dropped packets
```

**For databases**:

```
RED:
- Queries per second
- Query errors (deadlocks, timeouts)
- Query latency (p50, p95, p99)

USE:
- CPU utilization
- Memory utilization, hit ratio (cache effectiveness)
- Disk utilization
- Connection saturation (active connections vs. max connections)
```

**For message queues** (Kafka, RabbitMQ):

```
RED:
- Messages published/consumed per second
- Error rate (publishing failures, consumer lag)
- Latency (message latency from publish to consume)

USE:
- Disk utilization (storing messages)
- Network saturation (bandwidth)
- Consumer lag (how behind are consumers?)
```

### Step 2: Set Up Instrumentation

You need a monitoring tool to collect metrics.

**Popular tools**:
- **Prometheus**: Open-source, pull-based, time-series database
- **Datadog**: SaaS, full-featured, expensive but comprehensive
- **New Relic**: SaaS, APM (application performance monitoring) focused
- **CloudWatch** (AWS): Native to AWS, cheaper if already on AWS

**Basic instrumentation**:

```
# Application code (pseudocode)

import prometheus_client

# Define metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_latency = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])
active_connections = Gauge('active_connections', 'Active database connections')

# Track metrics
@app.route('/api/users')
def get_users():
    start = time.time()
    try:
        result = db.query('SELECT * FROM users')
        request_count.labels(method='GET', endpoint='/api/users', status='200').inc()
        request_latency.labels(endpoint='/api/users').observe(time.time() - start)
        return result
    except Exception as e:
        request_count.labels(method='GET', endpoint='/api/users', status='500').inc()
        raise
```

Your app exports metrics; Prometheus scrapes them every 15-30 seconds.

### Step 3: Logging Strategy

Logs capture what happened; metrics show trends.

**Log levels**:
- **ERROR**: Something failed; needs attention
- **WARN**: Unexpected but recoverable
- **INFO**: Important business event (user created, payment processed)
- **DEBUG**: Development diagnostics; typically disabled in production

**Structured logging** (JSON format):

```
Good (structured):
{"timestamp":"2026-03-05T14:23:15Z", "level":"ERROR", "service":"payment-api", "message":"Payment processing failed", "user_id":"12345", "error":"timeout", "duration_ms":5000}

Bad (unstructured):
ERROR: Something went wrong at 2026-03-05 14:23:15. Payment failed for user 12345. Timeout.
```

Structured logs are queryable and aggregatable.

**Logging strategy by service**:

```
Payment API:
- INFO: Each successful payment (user_id, amount, timestamp)
- WARN: Retried payment (reason)
- ERROR: Payment failed (reason, user_id)

User Service:
- INFO: User created, user deleted
- WARN: User login failed [threshold] times
- ERROR: Database connection lost

Background Job Queue:
- INFO: Job started, job completed
- WARN: Job took longer than expected
- ERROR: Job failed after retries (stack trace)
```

**Centralize logs**:
- Use ELK stack (Elasticsearch, Logstash, Kibana), Splunk, or Datadog
- All services send logs to central store
- Query all logs across services in one place

### Step 4: Alerting Rules (Avoid Alert Fatigue)

Alert only on actionable problems. Too many alerts = ignored alerts.

**Alert rule template**:

```
Alert Rule: High Error Rate

Metric: error_rate
Condition: error_rate > 5% for 2+ consecutive minutes
Severity: CRITICAL
Action: Page on-call engineer immediately
Runbook: [link to runbook]
Threshold notes: 5% is above normal (0.5%); indicates issue

Alert Rule: High Memory Usage

Metric: memory_utilization
Condition: memory_utilization > 85% for 5+ minutes
Severity: HIGH
Action: Alert on-call (no page; can wait a bit)
Runbook: [link to runbook]
Threshold notes: 85% is warning; 95% would be critical
```

**Threshold guidelines**:

**Errors**: Alert on elevated error rate, not absolute count. Normal error rate is ~0.1-0.5%; alert if >2%.

**Latency**: Alert on p99, not p50. p50 =100ms is fine; p99=5s is bad. Alert when p99 > 2x baseline.

**Saturation**: Alert when approaching limits. CPU >80%, memory >85%, disk >90% are typical.

**Avoid**:
- "CPU > 50%" (too sensitive; false alarms)
- "Error count > 1" (too low; every service has occasional errors)
- Alerts that page engineers for non-urgent issues (they ignore alerts)

**Alert action mapping**:

- **Critical**: Page on-call engineer immediately
- **High**: Alert (email/Slack), don't page (monitor manually, respond within 30 min)
- **Medium**: Ticket, review next morning
- **Low**: Don't alert; dashboard only

### Step 5: Dashboard Design

Dashboards surface system health at a glance.

**Dashboard types**:

**Service Health Dashboard** (overview):
- Service status (up/down)
- Error rate (p99 vs. baseline)
- Latency (p50, p95, p99)
- Traffic (RPS)
- CPU/memory/disk usage

**Incident Debug Dashboard** (during incident):
- Service logs (errors, warnings)
- Recent deployments
- Traffic pattern (spike or normal)
- Resource trends (spike or normal)
- Related services' health

**SLO Dashboard** (for business):
- Uptime percentage (vs. SLO target)
- Error rate (vs. SLO target)
- Latency (vs. SLO target)
- Budget remaining (how much room before SLO breach?)

**Example dashboard layout**:

```
[Service Health]
┌─────────────────────────────────────────┐
│ Payment API Status                      │
├─────────────────────────────────────────┤
│ Uptime: 99.95% | Errors: 0.3%          │
│ Latency p99: 280ms | Traffic: 1.2k RPS │
├─────────────────────────────────────────┤
│ CPU: 45% | Memory: 62% | Disk: 71%    │
└─────────────────────────────────────────┘

[Error Rate Over Time]
┌─────────────────────────────────────────┐
│ Error Rate (%)                          │
│ 5 ├────────────────╮                   │
│ 3 │       ╱╱╱      │                   │
│ 1 ─┼─────────────────┤                   │
│ 0 ├──────────────────┤ Baseline: 0.3% │
│   0:00 4:00  8:00  12:00               │
└─────────────────────────────────────────┘

[Latency Percentiles]
┌─────────────────────────────────────────┐
│ Latency (ms)                            │
│ p99: 280ms ▓▓▓░░░░                     │
│ p95: 120ms ▓▓░░░░░░                    │
│ p50: 45ms  ▓░░░░░░░                    │
│ Baseline: ──────────                   │
└─────────────────────────────────────────┘

[Recent Logs (Errors)]
┌─────────────────────────────────────────┐
│ ERROR: Timeout calling payment gateway  │
│ ERROR: Database connection lost         │
│ WARN: Slow query (2s): SELECT * FROM..│
└─────────────────────────────────────────┘
```

**Dashboard rules**:
- Frontload critical metrics (top left)
- Use red for bad, green for good, yellow for warning
- Time-based trends (24 hour, 7 day options)
- Link to runbooks and logs
- Refresh frequently (every 10-30 seconds)

### Step 6: SLO and SLI Definitions

SLOs (Service Level Objectives) are promises to customers. SLIs (Service Level Indicators) are measurements against those promises.

**Example**:

```
Service: Payment API

SLO: 99.9% uptime per month (no more than 43 minutes downtime)
SLI: (successful_requests / total_requests) × 100%

SLO: p99 latency < 500ms
SLI: (requests with latency < 500ms / total_requests) × 100%

SLO: Error rate < 0.1%
SLI: (errors / total_requests) × 100%
```

**SLO budget** (how much you can afford to fail):

```
SLO: 99.9% uptime
Monthly budget: 100% - 99.9% = 0.1% of minutes = 43 minutes
- January: Used 15 minutes (28 remaining)
- February: Used 20 minutes (23 remaining)
- March: Used 12 minutes (11 remaining)

March status: Tight budget; be cautious with deployments
```

Monitor SLO budget. If you're heading to breach, pause non-critical deployments.

### Step 7: Incident Correlation

Metrics alone don't explain incidents. Correlate metrics with events.

```
Timeline of incident:

14:00 - Deployment: payment-processor v2.5
14:23 - Error rate spikes from 0.3% to 5%
14:30 - p99 latency jumps from 200ms to 2000ms
14:32 - CPU usage spikes from 40% to 90%
14:33 - Memory usage increases from 60% to 85%
14:40 - Rollback deployment
14:42 - Error rate drops to 0.3%

Correlation: Deployment at 14:00 correlated with error spike at 14:23
Next time: Add monitoring for CPU/memory spike immediately post-deploy
```

Log all events (deployments, config changes, scaling events) on your dashboards so you can correlate with metric changes.

### Step 8: Monitoring Tools Setup Checklist

```
[ ] Metric collection tool installed (Prometheus, Datadog, etc.)
[ ] Application instrumented with RED metrics
[ ] Logging centralized and structured (JSON)
[ ] Alerting rules defined for critical paths
[ ] Dashboard created for service health
[ ] Dashboard created for incident debugging
[ ] SLOs and SLIs defined in writing
[ ] On-call rotation has access to dashboards and runbooks
[ ] Monitoring data retained for at least 30 days (for trend analysis)
[ ] Cost estimated and budgeted (Datadog: $100s/month; Prometheus: ~free)
```

### Step 9: Regular Review

Monitoring should evolve as your system does.

**Monthly review** (30 min):
- Did any alerts fire? Were they actionable?
- Did we miss any incidents (customers found before monitoring)?
- Are thresholds still appropriate?
- New metrics needed?

**Quarterly review** (60 min):
- Review SLO attainment (did we hit targets?)
- Update dashboards based on new services/features
- Prune old metrics no longer relevant
- Train team on new tools or processes

## Output Template

```
# Monitoring Setup Plan

## Services and Key Metrics

### Service: [Name]
**RED Metrics**:
- Rate: [metric, expected baseline]
- Errors: [metric, alert threshold]
- Duration: [p50/p95/p99 latencies, targets]

**USE Metrics**:
- CPU: [baseline, alert at 80%]
- Memory: [baseline, alert at 85%]
- Disk: [baseline, alert at 90%]
- Network: [baseline, saturation indicator]

## Instrumentation
- Monitoring tool: [Prometheus/Datadog/other]
- Metrics export: [How services export metrics]
- Logging: [Centralized to ELK/Splunk/Datadog]
- Log retention: [30 days / 90 days / other]

## Alert Rules
| Alert Name      | Metric      | Condition       | Severity | Action        |
|-----------------|-------------|-----------------|----------|---------------|
| High Error Rate | error_rate  | > 5% for 2 min  | CRITICAL | Page on-call  |
| High Latency    | p99_latency | > 1000ms for 5m | HIGH     | Alert only    |
| CPU Saturation  | cpu_usage   | > 80% for 5 min | HIGH     | Alert only    |

## Dashboards
1. Service Health (overview)
2. Incident Debug (detailed troubleshooting)
3. SLO Tracking (for customers/leadership)

## SLOs and SLIs
- Service uptime: [SLO %, SLI measurement]
- Latency: [SLO (p99), SLI measurement]
- Error rate: [SLO %, SLI measurement]
- SLO budget tracking: [How frequently reviewed]

## Review Schedule
- Daily: On-call reviews dashboard (spot-check)
- Weekly: Team reviews alert trends
- Monthly: Threshold and alert rule review
- Quarterly: SLO attainment, tool evaluation
```

## Quality Gates (5+)

1. **Comprehensive Metrics**: Do you have RED metrics for all user-facing services?
2. **Actionable Alerts**: Do alerts page/email only for problems that need immediate action?
3. **Meaningful Dashboards**: Can an engineer understand system health from the dashboard in 30 seconds?
4. **SLOs Documented**: Are SLOs written down and communicated to customers/stakeholders?
5. **Regular Review**: Do you review monitoring quarterly and update thresholds based on data?

## Examples

### Good Monitoring (Complete, Low Alert Fatigue)

**Metrics**: RED + USE implemented for all services
**Alerts**: 5 rules total; ~3 per week; >90% actionable
**Dashboard**: Health overview visible at a glance; latency trends clear
**SLO**: 99.95% uptime; tracking daily; have 5 days buffer for breaches
**Review**: Quarterly; thresholds adjusted; alert rules pruned

---

### Bad Monitoring (Incomplete, Alert Fatigue)

**Metrics**: A few random metrics; no comprehensive RED/USE
**Alerts**: 50 rules; 100+ per week; mostly false alarms
**Dashboard**: Complex, hard to read; no one uses it
**SLO**: Vague ("be reliable"); not tracked
**Review**: Never; thresholds from 3 years ago

## Common Mistakes (3+)

1. **Alert on Absolutes**: Alerting on "error count > 1" triggers daily. Alert on rate (error_rate > 2%) instead.

2. **Missing Context**: Error spikes to 5%; dashboard shows error rate but not that you just deployed. Log deployments on dashboard.

3. **SLO Obscurity**: "We want to be 99% available" but never measure it; never communicate it. Write down SLOs, measure them, track budget.

4. **Dashboard Decay**: Built dashboard; never updated. 6 months later it shows retired services, missing new ones. Review and update quarterly.

5. **No Root Cause**: Alerts fire; you fix the symptom; never investigate root cause. Each incident should surface one improvement.

## Anti-Patterns (3+)

1. **Monitoring Sprawl**: 100+ metrics; 50+ dashboards; no one knows what matters. Start with RED/USE; only add metrics that inform decisions.

2. **Alert Fatigue**: Everyone ignores Slack alerts because 99% are false alarms. Fix root cause (better thresholds) instead of ignoring channel.

3. **Post-Incident Monitoring**: Add monitoring only after incident. Proactive: define RED/USE upfront, instrument before launch.

---

**Next Steps**: Define RED metrics for your top 3 services. Choose a monitoring tool (Prometheus or Datadog). Deploy instrumentation. Create health dashboard. Define SLOs for one service.
