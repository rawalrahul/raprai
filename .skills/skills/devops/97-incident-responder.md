---
name: incident-responder
description: "Systematically respond to incidents: detection → triage → mitigation → resolution → postmortem, using severity classification, communication templates, and escalation protocols."
category: devops
difficulty: intermediate
model_boost: "Fixes chaotic incident response, poor communication, and repeated outages from lack of postmortems"
---

# Incident Responder

## Purpose

When production breaks, panic kills clear thinking. A systematic response framework keeps everyone aligned, minimizes downtime, and prevents future incidents. This skill provides a playbook: how to detect incidents early, triage severity correctly, communicate clearly during the incident, escalate appropriately, resolve systematically, and learn in postmortems. You'll exit with runbooks for your team and templates that turn chaos into structure.

## When to Use

- You're on-call for production systems
- You're building incident response processes for your team
- You want to reduce mean time to resolution (MTTR)
- You need to improve communication during incidents
- You're learning from repeated similar incidents
- **Do NOT use when**: You're in early-stage startup with no users yet (defer this until you have scale), or you lack monitoring in place (set up monitoring first)

## Instructions

### Step 1: Detection and Alerting

Incidents must be detected quickly, ideally automatically.

**Detection sources**:
- **Automated alerts**: Monitoring system (Datadog, New Relic, Prometheus) detects metric threshold breach (CPU >90%, error rate >5%, latency >500ms)
- **Customer reports**: User submits bug, contacts support
- **Team observation**: Engineer notices something weird during work
- **Health checks**: Synthetic monitoring confirms service is down

**Alert rules** (examples):

```
Rule 1: ERROR RATE
  Condition: Error rate > 5% for 2+ minutes
  Action: Page on-call engineer immediately
  Severity: CRITICAL

Rule 2: LATENCY
  Condition: p99 latency > 1000ms for 5+ minutes
  Action: Alert on-call, not paging (can wait a bit)
  Severity: HIGH

Rule 3: DISK SPACE
  Condition: Disk usage > 90%
  Action: Alert operations team (not critical immediately, but needs attention)
  Severity: MEDIUM
```

**Alert fatigue**: Too many alerts = people ignore them. Alert only on things that matter; tune out flaky signals.

### Step 2: Triage and Severity Classification

Not all incidents are equal. Classify by impact and urgency.

**Severity levels**:

```
SEVERITY 1 (CRITICAL):
- Complete service outage or severe degradation
- Large number of users affected (>1% of customer base)
- Data loss or security breach
- Response time: Declare incident within 5 minutes
- Escalate to: On-call engineer, manager, possibly VP

Example: Payment system down; customers can't check out

SEVERITY 2 (HIGH):
- Partial outage affecting some users or features
- Feature is broken but workaround exists
- Performance severely degraded (p99 latency >5s)
- Response time: Declare incident within 10 minutes
- Escalate to: On-call engineer, team lead

Example: Search is slow but users can browse products

SEVERITY 3 (MEDIUM):
- Minor feature broken or degraded
- Workaround exists, users can accomplish goal
- Single user or small group affected
- Response time: Declare incident within 30 minutes
- Escalate to: On-call or team lead

Example: Export feature returns partial data

SEVERITY 4 (LOW):
- Cosmetic issue, no functional impact
- No user-facing impact, internal tool problem
- Nice to fix but not urgent
- Response time: Can wait until business hours
- Escalate to: Ticket, not emergency

Example: Admin dashboard shows wrong color on button
```

**Triage questions**:
1. How many users/transactions are affected?
2. Is this a complete outage or partial degradation?
3. Is there a workaround?
4. Is customer data at risk?
5. Is this affecting revenue (Severity 1-2) or just convenience (Severity 3-4)?

### Step 3: Incident Declaration and Communication

Declare the incident formally so everyone knows.

**Incident declaration** (within minutes of discovery):

Send a message to a dedicated `#incidents` Slack channel or incident management tool:

```
🚨 INCIDENT DECLARED

Severity: 2 (HIGH)
Service: Payment API
Started: 14:23 UTC
Current status: Investigation ongoing
Impact: ~10% of transactions failing

Incident Commander: @alice
On-call Engineer: @bob
Communications Lead: @charlie

Status page: [UPDATE LINK]
War room: [ZOOM/JIRA LINK]

Next update: 14:35 UTC
```

**Initial message includes**:
- Severity level
- Which service/feature is affected
- Start time (when did we first detect it)
- Current understanding (what's broken and why, if known)
- Named incident commander (one person drives decision-making)
- Link to war room (everyone joins here)
- Next update time (keep communication flowing)

**Why this matters**: Clarity prevents duplicate efforts and miscommunication.

### Step 4: Mitigation and Root Cause Discovery

In parallel with communication, work on fixing it.

**Incident commander's job**:
- Keep people focused on the incident
- Coordinate between engineers working on fix, on-call, and comms lead
- Make escalation decisions
- Call the postmortem afterward

**Engineer's job**:
- Gather logs and metrics
- Identify the root cause
- Implement a fix (rollback, config change, hotpatch)
- Test and deploy

**Example incident timeline**:

```
14:23 - Alert fires: error rate > 5%
14:24 - Engineer joins war room
14:25 - Checking recent deployments; saw deploy 10 min ago
14:26 - Reviewing deploy diff; suspicious change in payment-processor
14:28 - Checking logs for errors; seeing "timeout" on external API call
14:30 - That external API had a breaking change in their API last night (we weren't notified)
14:32 - Fix: Revert deploy or update code to handle new API response
14:35 - Fix tested; no errors in staging
14:36 - Deploy to production
14:38 - Error rate drops, all good
14:40 - Declare incident resolved
```

**Mitigation options** (in order of speed):

1. **Rollback** (fastest, if recent deploy): Revert to last known good version
2. **Feature flag / config change** (fast): Disable problematic feature or adjust config without redeploying
3. **Hotpatch** (slower): Write and deploy a quick fix
4. **Scale** (if overload): Add capacity (more servers, database resources)
5. **Redirect traffic** (if one region down): Route users to another region

### Step 5: Real-Time Communication

Update stakeholders every 15-30 minutes while incident is ongoing.

**Update message**:

```
📊 UPDATE #2 - 14:35 UTC

Status: RESOLVING

What we found:
- Root cause identified: External payment API changed response format overnight
- Our code expects old format; got parsing errors

What we're doing:
- Hotpatching code to handle both old and new formats
- Testing in staging now; should deploy in 5 min

Impact so far:
- ~500 failed transactions
- Users seeing "Payment failed" error
- ~2% of daily revenue affected

Next update: 14:45 UTC
```

**Update template**:
- What's the status?
- What did we learn since last update?
- What are we doing to fix it?
- What's the impact (users affected, revenue, data)?
- When's the next update?

**Frequency**: 15-30 min updates during active incident, less frequent if resolving.

### Step 6: Resolution and Verification

Once fix is deployed, verify it worked.

**Resolution checklist**:
- [ ] Error rate back to normal
- [ ] Latency back to baseline
- [ ] No new error spikes after fix
- [ ] Customer reports resolved (if applicable)
- [ ] Manual test of feature works end-to-end
- [ ] Monitor for 5-10 min to ensure no regression

**Declare resolution**:

```
✅ INCIDENT RESOLVED

Severity: 2
Service: Payment API
Duration: 17 minutes (14:23 - 14:40 UTC)

Root cause: External payment API broke backward compatibility without notice

Fix: Updated code to handle both old and new API response formats

Impact: 500 failed transactions; ~$2,000 in impacted revenue (will be retried)

Follow-up: Will set up alerting for external API changes; add monitoring for API compatibility

Postmortem scheduled: Tomorrow at 2pm UTC

War room closed. Thank you all.
```

### Step 7: Postmortem (Learning)

**Blameless postmortem**: Focus on systems, not people.

Postmortem should happen within 24-48 hours while memory is fresh.

**Template**:

```
# Incident Postmortem: Payment API Timeout

**Date**: 2026-03-05
**Severity**: 2
**Duration**: 17 minutes
**Impact**: 500 failed transactions, $2k affected revenue

## What Happened (Timeline)
- 14:23 UTC: Alert fires (error rate > 5%)
- 14:23-14:30: Investigation; identified recent deploy
- 14:30: Root cause found: external API broke backward compatibility
- 14:30-14:36: Wrote and tested fix
- 14:36: Deploy to production
- 14:40: Error rate normalized; incident resolved

## Root Cause
External payment API provider changed their response format without backward compatibility warning. Our code expected old format and failed to parse new format.

## Why Did This Happen? (Five Whys)
1. Why did we fail to parse? Because code expected old format.
2. Why didn't we know about API change? No notification system; we rely on manual updates.
3. Why don't we monitor external API changes? Not prioritized; assumed they'd warn us.
4. Why wasn't this assumed? It's common for APIs to break compatibility if they don't have versioning.
5. Why don't we use API versioning? External provider doesn't offer it.

## What We Did Right
- Detection was fast (within 1-2 min)
- Root cause was identified quickly
- Fix and deploy was smooth
- Communication was clear and timely

## What We Could Improve
- Add monitoring for external API format changes (validate response structure every 5 min)
- Add circuit breaker: If API returns unexpected format, fail gracefully instead of crashing
- Increase test coverage for API compatibility
- Add Slack bot to notify when external APIs update (if they publish updates)

## Action Items
1. [Engineer] Add API response validation checks (Due: 1 week)
2. [Engineer] Add circuit breaker for external API calls (Due: 2 weeks)
3. [Ops] Set up external API monitoring dashboard (Due: 3 days)
4. [Product] Contact payment provider for API versioning or change notification (Due: ASAP)

## Metrics
- MTTR (Mean Time to Resolution): 17 minutes
- Impact: 500 transactions, $2k revenue
- Root cause: External dependency, not our code
```

**Postmortem principles**:
- Blameless: Focus on systems, not people ("Why was the system designed this way?" not "Why did Alice mess up?")
- Transparent: Share postmortem with whole team
- Action-oriented: Each postmortem should produce 1-3 action items
- Follow-up: Track action items; did we actually implement them?

### Step 8: Build Runbooks

Create runbooks (procedures) for common incidents so response is faster next time.

**Example runbook: High Error Rate**

```
# Runbook: High Error Rate on Payment API

## Detection
Alert: Error rate > 5% for 2+ minutes

## Immediate Actions (First 5 min)
1. Join war room (link in alert)
2. Check recent deploys: `git log -5 --oneline`
3. Check logs for error patterns: `kubectl logs -f payment-api-prod`
4. Check metrics: CPU, memory, latency (in Datadog)

## Diagnosis (Next 10 min)
- [ ] Did error rate spike coincide with a deploy? (Rollback candidate)
- [ ] Did error rate spike coincide with traffic spike? (Scale issue)
- [ ] Are there particular endpoints with high errors? (Feature-specific)
- [ ] Are database queries slow? (Database issue)
- [ ] Is an external service down? (Dependency issue)

## Actions by Root Cause

### If Recent Deploy
- [ ] Rollback: `kubectl rollout undo deployment/payment-api`
- [ ] Monitor error rate; should drop within 1-2 min
- [ ] If resolved, investigate deploy and test better before redeploying

### If Traffic Spike
- [ ] Scale up: `kubectl scale deployment payment-api --replicas=10`
- [ ] Monitor CPU and latency; should improve
- [ ] If sustained spike, investigate why traffic spiked

### If Database Slow
- [ ] Check query logs: `SELECT * FROM slow_queries LIMIT 10`
- [ ] Consider adding index to slow queries
- [ ] If critical, reduce load: disable non-essential features

### If External Service Down
- [ ] Check status page: [Payment Gateway status]
- [ ] Implement fallback/retry logic if possible
- [ ] Wait for external service to recover

## Rollback Procedure
```bash
kubectl rollout history deployment/payment-api
kubectl rollout undo deployment/payment-api --to-revision=N
kubectl rollout status deployment/payment-api
```

## Escalation
- If error rate doesn't drop within 10 min: Page on-call manager
- If customers are calling in: Notify customer success team
- If revenue impact >$10k/min: Notify VP Engineering
```

Create runbooks for your top 5 incident types. Update as you learn new causes.

### Step 9: Prevention

Not all incidents are preventable, but many are.

**Prevention categories**:

**Code level**:
- Better error handling (catch expected errors gracefully)
- Circuit breakers (stop calling failing external API; fail fast)
- Timeouts (don't hang forever)
- Retry logic with exponential backoff

**Monitoring level**:
- Alert on anomalies (not just thresholds; unexpected change)
- Synthetic monitoring (simulate user experience; know before customers report)
- Log-based alerts (error messages, specific patterns)

**Deployment level**:
- Canary deployments (deploy to 5% of users; monitor before 100%)
- Gradual rollouts (ramp up traffic slowly; easy to detect issues)
- Automated rollbacks (if error rate spikes post-deploy, rollback automatically)

**Architecture level**:
- Redundancy (if one instance fails, others handle traffic)
- Graceful degradation (non-essential features turn off; core features stay up)
- Rate limiting (prevent cascade failures; if system overloaded, reject requests to stay stable)

### Step 10: Incident Metrics and Trends

Track incidents to identify patterns and improve over time.

```
# Incident Metrics (Last 3 Months)

Total incidents: 12
Average MTTR: 25 minutes
Severity distribution:
  - Sev 1 (Critical): 1 (payment provider API break)
  - Sev 2 (High): 4 (deploy errors, database issues)
  - Sev 3 (Medium): 7 (feature bugs)

Root causes:
  - Deploy-related: 5 incidents (insufficient testing, missing monitoring)
  - Database: 3 incidents (slow queries, disk full)
  - External dependency: 2 incidents (API changes, timeout)
  - Unknown: 2 incidents (transient; can't reproduce)

Trends:
- Sev 1 incidents trending down (better deploy process)
- Database incidents trending up (growing traffic exposing query issues)
- Average MTTR improving (runbooks helping)

Recommendations:
1. Increase database query monitoring
2. Add canary deployments to reduce deploy-related incidents
3. Improve testing for external API compatibility
```

Review metrics monthly. Are MTTR and incident frequency improving?

## Output Template

```
# Incident Response Playbook

## Severity Classification
- Severity 1 (CRITICAL): [Definition]
- Severity 2 (HIGH): [Definition]
- Severity 3 (MEDIUM): [Definition]
- Severity 4 (LOW): [Definition]

## Roles During Incident
- Incident Commander: [Drives decision-making, coordinates response]
- On-call Engineer: [Fixes the issue]
- Communications Lead: [Updates stakeholders]
- Manager: [Escalates if needed]

## Detection and Alerting
- [Alert rule 1]: [Condition and action]
- [Alert rule 2]: [Condition and action]

## Communication Templates
- Incident Declaration
- Status Update (every 15-30 min)
- Resolution

## Runbooks (Create for Each Common Incident Type)
1. [High error rate]
2. [Database performance]
3. [Deployment failure]
4. [External API down]

## Postmortem Template
- Timeline
- Root cause
- What we did right
- What we could improve
- Action items

## Escalation Policy
- Sev 1: [Escalation path]
- Sev 2: [Escalation path]
- Sev 3: [Escalation path]

## Metrics to Track
- MTTR (Mean Time to Resolution)
- MTTI (Mean Time to Incident) - how often do we have incidents?
- Incident distribution by severity
- Root cause frequency
```

## Quality Gates (5+)

1. **Severity Criteria Clear**: Can any engineer classify a new incident correctly?
2. **Communication Template Ready**: Can you paste a template and send an incident alert in <2 minutes?
3. **Runbooks Exist for Top Incidents**: Do you have step-by-step procedures for your 3-5 most common incidents?
4. **Escalation Policy Known**: Does everyone know when to page manager vs. on-call engineer?
5. **Postmortems Happen**: Are you doing postmortems within 48 hours and tracking action items?

## Examples

### Good Incident Response (Structured, Quick)

**Incident**: Payment API high error rate

**Timeline**:
- 14:23: Alert fires, engineer joins war room
- 14:24: Checks recent deploys; spots suspicious change
- 14:30: Root cause found; rollback in progress
- 14:31: Rollback deployed; error rate dropping
- 14:35: Error rate back to normal; incident resolved
- 14:40: Status update sent to customers

**MTTR**: 17 minutes

**Postmortem**: Completed next day; identified weak testing; added canary deployment process

---

### Bad Incident Response (Chaotic, Slow)

- 14:23: Alert fires; engineer sleeping, paged at 14:30
- 14:35: Engineer joins, doesn't know what to do
- 14:40: Asks manager for help
- 14:50: Still investigating; no one assigned to comms
- 15:10: Root cause found; starts coding fix (slow, under pressure)
- 15:35: Fix deployed; not thoroughly tested
- 15:50: Error rate drops
- Customers bombard support; no one told them about incident
- Never does postmortem; repeats same incident in 2 weeks

**MTTR**: 87 minutes (5x worse!)

## Common Mistakes (3+)

1. **No Postmortems**: Incident happens, gets resolved, never discussed again. Team repeats same mistakes.

2. **Blame Culture**: "Why did Alice deploy bad code?" instead of "Why did our testing not catch this?" Blameless culture encourages openness.

3. **No Runbooks**: Every incident is novel; response is slow and chaotic. Standard procedures speed response.

4. **Silent Outages**: Users discover issues before your team. Add synthetic monitoring and dashboards that surface problems before customers see them.

5. **Unclear Escalation**: Incident happens, unclear who's on-call, unclear when to page manager. Publish escalation policy and update it when team changes.

## Anti-Patterns (3+)

1. **Alert Fatigue**: 100s of alerts; engineers ignore them. Tune alerting to real problems only.

2. **Slow Postmortems**: Scheduled for 2 weeks later; people forget details. Do postmortem within 48 hours.

3. **Action Items Forgotten**: Postmortem identifies 5 action items; none are tracked, none get done. Assign owners and follow up weekly.

---

**Next Steps**: Classify incidents by severity. Create incident declaration template. Build runbooks for your 3 most common incidents. Schedule weekly "incident review" to discuss recent incidents and trends.
