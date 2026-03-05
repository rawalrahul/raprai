---
name: post-mortem-generator
description: "Generate post-mortems with timeline reconstruction, 5-Why root cause analysis, contributing factors, action items, and blameless culture. Enables learning from incidents and prevents recurrence."
category: business
difficulty: intermediate
model_boost: "Prevents superficial incident analysis and blame culture; produces instead thorough root cause investigations with preventive actions."
---

# Post-Mortem Generator

## Purpose
A post-mortem (or incident review) systematically analyzes what went wrong, why, and how to prevent recurrence. This skill generates post-mortems that: reconstruct the incident timeline, identify root causes (via 5-Why analysis), document contributing factors, assign preventive action items, and foster blameless culture. Output enables: organizational learning, incident prevention, team psychological safety, and continuous improvement.

## When to Use
- After a significant incident (outage, data breach, missed deadline, major customer churn, product launch failure)
- Before a potentially serious incident (near-miss): "What if this had been worse?"
- Recurring problems: "Why does this keep happening?"
- Post-project review: "What worked, what didn't, what'll we do differently?"
- **Do NOT use when**: Incident is still unfolding (focus on resolution first); organization has blame culture (post-mortem will be defensive, not honest); incident is minor (low learning value).

## Instructions

### Step 1: Define Incident & Scope
What happened? When? How long? Who was impacted?

**Incident Record**:
- **Title**: Concise description (e.g., "Database connection pool exhaustion caused 30-minute outage")
- **Date/Time**: {{Date}}, {{Start time}} - {{End time}} ({{# minutes/hours}} duration)
- **Impact**: {{# of customers affected}}, {{$ revenue impact}}, {{what they experienced}}
- **Severity**: {{Critical (full system down)}}, {{Major (partial outage or data loss)}} {{Minor (degradation)}}
- **Responder**: {{Who discovered / resolved it}}

Example: "Invoice Processing Service Outage: January 15, 2:15 AM - 2:45 AM UTC (30 minutes). 150 customers unable to process invoices. ~$5K revenue impact. 40 invoices delayed."

### Step 2: Reconstruct Timeline (Minute-by-Minute)
Recreate what happened, in order. Interview responders. Check logs.

**Timeline Format**:
- **2:15 AM**: Service starts rejecting requests (500 errors). Customers report issues.
- **2:17 AM**: On-call engineer paged. Checks monitoring dashboard.
- **2:20 AM**: Dashboard shows 100% CPU usage on invoice-processing service.
- **2:22 AM**: Engineer restarts service. Service comes back online.
- **2:28 AM**: Service goes down again (same symptom).
- **2:30 AM**: Engineer escalates to database team. Discovers connection pool exhausted.
- **2:35 AM**: Database team finds {{long-running query}} holding connections. Kills query.
- **2:45 AM**: Service stable. Customers resume processing invoices.

Detailed timeline is crucial for root cause analysis.

### Step 3: Identify Root Cause (5-Why Analysis)
Don't stop at surface cause. Dig deeper with 5 Whys.

**Example**:
1. **Why did the service go down?** Connection pool exhausted (service couldn't get DB connections).
2. **Why was the connection pool exhausted?** {{Long-running query}} was holding {{N}} connections.
3. **Why was that query long-running?** {{Missing database index}} on {{column]]. Query had to scan {{millions}} of rows.
4. **Why was the index missing?** {{Deployed schema change yesterday that removed unused index. Didn't realize it was actually used by {{this query]]}}}}.
5. **Why wasn't this caught before deployment?** {{No code review of schema changes}}. {{No load testing on staging]].

**Root Cause**: Lack of code review + load testing revealed {{missing index]] usage.

### Step 4: Identify Contributing Factors
What else made the incident worse or prevented earlier detection?

**Contributing Factors**:
- **Monitoring gaps**: Alerting didn't notify team of {{metric spike}} until customers reported (time lost)
- **Documentation**: {{Long-running query}} wasn't {{documented|profiled}}; engineer had to hunt it down
- **Runbook**: No {{documented]] procedure for {{this specific error]], so engineer didn't know to check DB first
- **On-call**: {{Engineer]] was new; didn't know {{system well}} (more time to debug)

Contributing factors don't cause the incident but make it worse or harder to resolve.

### Step 5: Determine Preventive Actions
For each root cause and contributing factor, what will prevent recurrence?

**Format**:
- **Preventive Action**: {{What we'll do}}
- **Owner**: {{Who implements}}
- **Timeline**: {{By when}}
- **Success Metric**: {{How we know it's done and effective}}

**Example**:
| Root Cause | Preventive Action | Owner | Timeline | Success Metric |
|---|---|---|---|---|
| {{Missing index after deploy}} | Add code review step for schema changes (template) | {{DBA}} | Week 1 | {{All schema deploys reviewed before production}} |
| {{Missing load test}} | Add load test to pre-deployment checklist | {{QA}} | Week 1 | {{All major deploys load-tested on staging}} |
| {{Monitoring gap}} | Alert on {{connection pool usage >80%}} | {{Infra}} | Week 2 | {{Alert fires, team notified before customer impact}} |
| {{No runbook}} | Document {{db connection troubleshooting]] | {{Tech Lead}} | Week 1 | {{New on-call can resolve in <5 min next time}} |

### Step 6: Create Action Items
Preventive actions become action items. Track to completion.

**Action Item Template**:
- **Title**: {{What needs to be done}}
- **Owner**: {{Name, role}}
- **Priority**: {{Critical (fix ASAP), High (next sprint), Medium (backlog)}}
- **Due Date**: {{Target completion}}
- **Description**: {{Details on what to implement}}
- **Success Criteria**: {{How we know it's done}}

### Step 7: Document Blameless Culture
Post-mortems are about systems, not blame.

**Blameless Principles**:
- **Assume good intent**: Engineer made {{decision]] based on {{info they had at the time}}. Not malice.
- **Focus on "How"**: "How did this happen?" not "Who did this?"
- **Systems over individuals**: {{Engineer didn't catch it}} because {{code review process missing]]}}, not because {{engineer careless}}
- **Psychological safety**: Honesty is rewarded. Blame is not tolerated.

**Language**:
- ✓ "The code review process didn't catch this because nobody reviewed schema changes."
- ✗ "The engineer didn't check if the index was used elsewhere."

### Step 8: Communicate & Distribute
Share post-mortem with team. Celebrate learnings.

**Who Needs to Know**:
- **Team involved in incident**: Validate post-mortem, add context
- **Broader engineering**: Learn from others' incidents
- **Leadership**: Understand impact and improvements
- **Customers** (if relevant): Transparency builds trust

### Step 9: Follow-up (Monthly Check)
Did we actually implement preventive actions? Are they working?

**Monthly Follow-up Questions**:
- {{Action 1}}: {{Completed?}} {{Effective (did it prevent recurrence)?}}
- {{Action 2}}: {{}}
- {{Are we seeing similar incidents?}} {{Why?}}
- {{What new insights have we learned?}}

If action didn't prevent recurrence, dig deeper (root cause was wrong, implementation was incomplete).

## Output Template

```markdown
# POST-MORTEM: {{Incident Title}}
**Incident Date**: {{Date}}, {{Start time}} - {{End time}} ({{Duration}})
**Severity**: {{Critical / Major / Minor}}
**Post-Mortem Date**: {{Date}}
**Prepared By**: {{Name}}, {{Role}}
**Reviewed By**: {{Engineering Lead, Manager}}

---

## EXECUTIVE SUMMARY

**What Happened**: {{1-sentence description of incident}}

**Impact**: {{# of customers}}, {{$ cost}}, {{Duration}}

**Root Cause**: {{Core reason incident occurred}} (not surface cause, but real root)

**Key Actions**:
1. {{Preventive action 1 (highest priority)}}
2. {{Preventive action 2}}
3. {{Preventive action 3}}

---

## INCIDENT DETAILS

### Timeline (Minute-by-Minute)

| Time | Event | Actor | Notes |
|---|---|---|---|
| {{2:15 AM}} | {{Service returned 500 errors}} | {{Customers}} | First issue observed |
| {{2:17 AM}} | {{Engineer paged}} | {{On-call}} | {{Acknowledged {{alert / customer report}}}} |
| {{2:20 AM}} | {{Checked monitoring; saw {{symptom}}}} | {{Engineer}} | {{Identified: {{}}}} |
| {{2:22 AM}} | {{Restarted service}} | {{Engineer}} | {{Service came online}} |
| {{2:28 AM}} | {{Service crashed again}} | {{Automation}} | {{Same error}} |
| {{2:30 AM}} | {{Escalated to {{database team}}}} | {{Engineer}} | {{Connection pool exhausted}} |
| {{2:35 AM}} | {{Found {{culprit query]]}}, killed it}} | {{DBA}} | {{Identified {{long-running query}}}} |
| {{2:45 AM}} | {{Service stable}} | {{Automation}} | {{Customers resume processing}} |

**Duration**: {{30 minutes}} from first issue to resolution

**Detection**: {{Customer report}} (no alert fired)

**Resolution**: {{Kill long-running query}} (temporary fix)

---

## ROOT CAUSE ANALYSIS (5-Why)

### Why 1: Why did the service go down?
{{Database connection pool was exhausted. Service couldn't get new DB connections, rejected requests.}}

### Why 2: Why was the connection pool exhausted?
{{A {{long-running query}} was holding {{number}} connections for {{duration}}.}}

### Why 3: Why was the query long-running?
{{Missing {{database index]] on {{column}]. Query had to scan {{# million}} rows instead of using index.}}

**Evidence**: {{EXPLAIN plan shows full table scan; index created, query now <100ms}}

### Why 4: Why was the index missing?
{{Yesterday's {{schema deploy]] removed the {{index]]. Thought it was unused; actually {{this query uses it]]. Didn't run load test; impact wasn't caught.}}

**Evidence**: {{Commit message shows index dropped; no code review}}

### Why 5: Why wasn't this caught before deployment?
{{No {{code review process]] for schema changes. No {{load test]] on staging. Impact only visible under {{production load]].}}

**Root Cause**: {{Missing code review + missing load test. Index removal wasn't reviewed. Load test would have caught {{performance regression]].}}

---

## CONTRIBUTING FACTORS

**These didn't cause the incident but made it worse / harder to resolve**:

1. **Monitoring**: {{No alert on connection pool usage >80%. Team found out from customer report ({{X minutes}} delay). If alert existed, team notified at {{2:16 AM]]}}, could have prevented customer impact.}}

2. **Runbook**: {{No documented {{procedure]] for {{connection pool exhausted error]]. On-call engineer had to figure out root cause from {{scratch]]. With runbook: could have resolved {{faster}}.}}

3. **Documentation**: {{{{Query]] not documented; no {{performance profiling]]. Engineer didn't know which query to look at. DBA had to hunt {{connections]].}}

4. **On-Call Knowledge**: {{New on-call engineer. Took {{longer to debug]]. Experienced engineer would have known to check {{database first]]. Training gap.}}

5. **Temporary vs. Permanent Fix**: {{Restarted service (temporary). Service crashed again. Should have immediately {{killed query]] or {{restored index]]. Wasted {{13 minutes}} on temporary fix that didn't address root cause.}}

---

## PREVENTIVE ACTIONS

### Action 1: Code Review for Schema Changes [CRITICAL]
**Why This Prevents Recurrence**: {{{{Code review would have caught index removal. Reviewer would ask: "Is this index used elsewhere?" Discovery: yes, used by {{query]]. Index restored. Deploy prevented.}}

**Owner**: {{Database Team Lead}} (implement code review template)
**Timeline**: {{Week 1 (by {{date}})}}
**Implementation**:
- Create {{schema change review checklist}} (dependencies, performance impact, rollback plan)
- Require {{2 approvals]] for any schema deploy (DBA + backend lead)
- {{Add to deployment SOP}}

**Success Metric**: {{All schema changes reviewed before production}}. {{{{Track: # of schema deploys in past month that had code review}} → {{target: 100%}}}}.

---

### Action 2: Load Testing in Staging [HIGH]
**Why This Prevents Recurrence**: {{{{Load test would have revealed query performance degradation. Caught before production deploy.}}

**Owner**: {{QA Lead}}
**Timeline**: {{Week 1}}
**Implementation**:
- {{Add {{load test scenario]] to {{pre-deployment checklist}}}}
- {{Run {{production-like load]] on staging before major deploys}} ({{schema changes]}, {{query changes]})
- {{Profile [[query execution time]] under load; if >{{threshold}}, fail deploy}}

**Success Metric**: {{All major deploys load-tested before production}}. {{Track: {{# of deploys}} with {{load test results>}} → {{target: 100%}}.}}}

---

### Action 3: Connection Pool Alerting [HIGH]
**Why This Prevents Recurrence**: {{{{Alert notifies team at {{2:16 AM]] when pool hits {{80%}}. On-call responds {{immediately]], not after customer reports.}}

**Owner**: {{Infrastructure Team}}
**Timeline**: {{Week 1}}
**Implementation**:
- Add {{Prometheus alert]]: {{connection_pool_usage}} > {{80%}} → {{page on-call}}
- Alert threshold: {{{{conservative (80%) to catch early}}}}
- {{Alert includes {{runbook link]] in pagerduty message}}

**Success Metric**: {{Alert fires before customer impact}}. {{{{Test: {{simulate {{connection pool exhaustion]] on staging; verify {{alert fires within {{# seconds]]}}.}}}}}

---

### Action 4: Connection Pool Troubleshooting Runbook [MEDIUM]
**Why This Prevents Recurrence**: {{{{Runbook tells on-call: "If {{alert]], check {{these places]]". Reduces debug time from {{13 min}} to {{{{2-3 min]]}}.}}

**Owner**: {{Tech Lead}}
**Timeline**: {{Week 1}}
**Implementation**:
- Document {{Connection Pool Exhausted - Troubleshooting Runbook}}:
  1. {{Check {{connection pool usage]] metric}}
  2. {{Query {{database]] for long-running queries}}: {{SQL command}}
  3. {{{{Kill [[offending query]]: `KILL {{query_id}}`}}}}
  4. {{Monitor {{metric]] for recovery}}
  5. {{{{Post-incident: Investigate why query was slow. Index missing? Query inefficient?}}}}
- {{Link in {{Pagerduty alert}} so on-call has it at their fingertips}}

**Success Metric**: {{Next similar incident resolved in {{<5 min}}}} (vs. {{13 min}} this time). {{Track: {{incident response time]].}}}

---

### Action 5: On-Call Training [MEDIUM]
**Why This Prevents Recurrence**: {{{{New on-call spent {{longer debugging]]. Training on {{architecture, common incidents, {{runbooks]]]] reduces debug time.}}

**Owner**: {{Engineering Manager}}
**Timeline**: {{Week 2}}
**Implementation**:
- {{Create on-call onboarding checklist}}:
  - {{Review {{top 5 incidents]] of last {{# months}}}}
  - {{Shadow {{experienced on-call]] for {{# days}}}}
  - {{Review {{all runbooks]]}}
  - {{Practice {{incident response]] scenario}}
- {{Assign {{mentor]] to new on-call for {{first month}}}}

**Success Metric**: {{New on-call can resolve incident within {{{{benchmark time}}}}. {{Track: {{incident response time]] for {{new on-call]]}} over first {{month]].}}}

---

## ACTION ITEMS (Tracking)

| Action | Owner | Priority | Due Date | Status | Last Update |
|---|---|---|---|---|---|
| {{Code review template for schema changes}} | {{DBA Lead}} | Critical | {{Week 1}} | In Progress | {{Reviewed draft, feedback sent}} |
| {{Load test checklist}} | {{QA Lead}} | High | {{Week 1}} | Not Started | {{TBD}} |
| {{Connection pool alert}} | {{Infra}} | High | {{Week 1}} | Not Started | {{TBD}} |
| {{Runbook: connection pool}} | {{Tech Lead}} | High | {{Week 1}} | Not Started | {{TBD}} |
| {{On-call training plan}} | {{Manager}} | Medium | {{Week 2}} | Not Started | {{TBD}} |

---

## BLAMELESS CULTURE STATEMENT

**This post-mortem is written in the spirit of continuous improvement, not blame.**

- {{Engineer who deployed schema change}}: {{Made {{reasonable decision]] based on {{info available at the time}}. {{Nobody suspected [[index}} used elsewhere. Not their fault; system fault.}}
- {{On-call engineer}}: {{Did {{exactly what they should]]} (paged, started investigating). Only took {{longer because {{no runbook]]. Not their fault; training/documentation fault.}}
- **What We'll Do Different**: {{We'll add {{code review]] + {{load test]] so [[issues caught before production]]. If similar incident happens again, root cause will be {{different (better systems)]]}}

**Psychological Safety**: {{Everyone should feel {{safe sharing]] what went wrong, what they tried, {{what they would do differently]]. No judgment. Only learning.}}

---

## FOLLOW-UP & MONITORING

### Monthly Check-In (Due {{+30 days}})
- {{Action 1 (code review)}}: {{Completed?}} {{Are all schema deploys now reviewed?}} {{Effectiveness: Has this caught any issues?}}
- {{Action 2 (load test)}}: {{Completed?}} {{Are all major deploys load-tested?}} {{Effectiveness: Have we caught regressions?}}
- {{Action 3 (alert)}}: {{Completed?}} {{Have we had false positives?}} {{Effectiveness: Would alert have caught this incident?}}
- {{Action 4 (runbook)}}: {{Completed?}} {{Used in incident response?}} {{Effectiveness: Is response time improving?}}
- {{Action 5 (training)}}: {{Completed?}} {{New on-call completing training?}} {{Effectiveness: Are they ramping faster?}}

**Questions**:
- {{Are we seeing similar incidents?}} {{Why? Root cause analysis was wrong? Implementation incomplete?}}
- {{What new insights have we learned?}} {{Anything we missed?}}
- {{What's the next {{incident]] we should be prepared for?}}

### Escalation Triggers
- {{If Action {{X]] not completed by {{due date}}, escalate to {{manager]]}}}
- {{If similar {{incident]] happens again within {{# months}}, full root cause re-analysis}}

---

## COMMUNICATION

### Who Gets This Post-Mortem
- {{Team involved in incident}} (validate + add context)
- {{All engineers}} (learn from others)
- {{Leadership}} (understand impact + improvements)
- {{Customers}} (if relevant) {{transparency on what happened + how we'll prevent}}

### Customer Communication (if applicable)
{{If customer-facing incident:}}
- {{Timeline: When will customer be informed?}} ({{immediately / after internal review}})
- {{Message**: {{What happened in customer-friendly language, root cause, what we're doing to prevent}})}}
- **Owner**: {{VP Customer Success or CEO}}

---

## APPENDIX

### A. Incident Timeline (Detailed)
{{Full reconstruction with {{logs, metrics, chat transcripts]}}

### B. Code Changes That Contributed
{{Commits deployed yesterday that led to incident}}

### C. Monitoring Dashboard
{{Link to dashboard]] during incident (what did/didn't alert?)

### D. Similar Incidents (Historical)
{{Previous {{similar]] incidents and what we learned}}}

---

**Post-Mortem Owner**: {{Name}}
**Review Status**: {{Reviewed and approved by {{Engineering Lead}}}}
**Review Date**: {{Date}}
**Scheduled Follow-Up**: {{Date (30 days)}}
**Contact**: {{Email}} if questions
```

## Quality Gates
- [ ] Timeline reconstructed minute-by-minute with actors and events
- [ ] Root cause identified via 5-Why analysis (not surface cause)
- [ ] Contributing factors documented (what made it worse or harder to resolve)
- [ ] 3-5 preventive actions with owners, timelines, and success metrics
- [ ] Blameless language used (systems focus, not blame)
- [ ] Action items tracked with owners, priorities, and due dates
- [ ] Monthly follow-up plan to verify preventive actions are implemented and effective
- [ ] Communication plan defines who gets post-mortem and customer notification (if applicable)
- [ ] Post-mortem reviewed and approved by team lead or manager
- [ ] Lessons documented for future reference and training

## Examples

### Good Output (excerpt)
```
INCIDENT: Database Connection Pool Exhaustion

TIMELINE:
2:15 AM - Invoice service starts returning 500 errors
2:17 AM - On-call paged by customer report
2:20 AM - Engineer checks monitoring, sees 100% CPU + connection pool at max
2:22 AM - Restarts service (temporary fix)
2:28 AM - Service crashes again (temporary fix didn't work)
2:30 AM - Escalates to database team
2:35 AM - DBA finds long-running query (holding 50 connections for 8 minutes), kills it
2:45 AM - Service stable, customers resume

ROOT CAUSE (5-Why):
1. Why service down? Connection pool exhausted
2. Why pool exhausted? Long-running query holding connections
3. Why slow query? Missing index on {{column}}
4. Why missing index? Schema deploy yesterday removed "unused" index; actually used by this query
5. Why not caught? No code review of schema changes. No load test on staging.

Root Cause: Missing code review + missing load test

---

PREVENTIVE ACTIONS:

1. Code Review for Schema Changes (Owner: DBA Lead, Week 1)
   - Why: {{Would have caught index removal}}
   - Implementation: Require 2 approvals for schema deploys
   - Success Metric: {{100% of schema deploys reviewed before production}}

2. Load Testing (Owner: QA Lead, Week 1)
   - Why: {{Would have caught performance degradation}}
   - Implementation: Add load test scenario to pre-deployment checklist
   - Success Metric: {{All major deploys load-tested}}

3. Connection Pool Alerting (Owner: Infra, Week 1)
   - Why: {{Would have alerted team at 2:16 AM instead of waiting for customer report}}
   - Implementation: Alert when pool usage >80%
   - Success Metric: {{Alert fires before customer impact}}

---

BLAMELESS:
The engineer who deployed the schema change made a reasonable decision based on their understanding that the index was unused. Nobody thought to check load impact. Root cause is system (lack of code review + load test), not individual.

---

FOLLOW-UP (Month 1):
- Code review implemented? {{Yes, all schema deploys reviewed}}
- Load test implemented? {{In progress, targeting week 2}}
- Alert implemented? {{Yes, deployed and tested}}
- Runbook created? {{Yes, new on-call following it}}
- Similar incidents? {{No, only one related performance issue caught by load test}}
```

### Bad Output (what to avoid)
```
Post-Mortem: Database went down.

Engineer restarted it. Now it works.

(Why this fails: No timeline, no root cause analysis, no preventive actions, looks like blame toward engineer)
```

## Common Mistakes

1. **Stopping at Surface Cause**: "Query was slow" (not root cause). Better: Ask 5 Whys. "Why slow? Missing index. Why missing? Schema deploy removed it. Why removed? No code review."

2. **Blame Language**: "Engineer didn't check the impact" (blames engineer). Better: "System was missing code review process, so impact wasn't checked."

3. **Preventive Actions Too Vague**: "Improve monitoring." Better: "Alert when connection pool >80%, owned by Infra, by Week 1, success metric: alert fires before customer impact."

4. **No Follow-up**: Post-mortem written, filed, forgotten. Actions never implemented. Similar incident happens. Better: Track action items. Monthly check-in.

5. **Post-Mortem Hidden**: Only discussed in private team. Org never learns. Same problem happens elsewhere. Better: Share post-mortem (anonymized if sensitive) across org.

## Anti-Patterns

1. **Post-Mortem as Performance Review**: Post-mortem finds "engineer made {{mistake]]". Used later in performance review / firing. Culture becomes "hide mistakes". Incidents go unreported. Better: Post-mortems are for learning. Don't use against individuals.

2. **Action Items That Never Get Done**: "{{Engineer]] will add monitoring" but gets deprioritized. {{6 months}} later, {{similar]] incident. Better: Actions tracked, prioritized, due dates enforced.

3. **Repeating Same Incident**: {{Similar incident]] happens {{# months}} later. Root cause was same; post-mortem lesson wasn't learned. Better: {{Quarterly review]] of {{all incidents]]. If {{pattern]], escalate.

4. **Too Long / Complex to Read**: Post-mortem is {{50+ pages]]. Nobody reads it. Better: {{1-2 page summary]] with {{appendices]] for details.

5. **No Learning Culture**: Post-mortem says "Don't do X in future." But {{reason}} wasn't fixed, so doing X is {{still possible]]. Better: Fix {{system/process]] so {{X }} can't happen. Example: "Remove {{permission]] so {{person]] can't deploy {{without review]]."

