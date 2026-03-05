---
name: root-cause-analyzer-systemic
description: "Investigate failure or problem through fishbone diagrams, 5 Whys, fault trees, and Pareto analysis to identify systemic root causes, not just symptoms, enabling durable solutions."
category: research
difficulty: intermediate
model_boost: "Weak models stop at first cause, missing systemic/organizational root causes"
---

# Systemic Root Cause Analysis

## Purpose
Root cause analysis investigates why a problem occurred through systematic investigation to identify fundamental causes, not superficial symptoms. Unlike quick fixes addressing symptoms (treating fever without diagnosing infection), root cause analysis traces back through causal chains to systemic factors (processes, incentives, capabilities, design flaws) enabling durable solutions. The key distinction is depth: surface cause ("employee made mistake") vs. root cause ("process lacked redundancy/error-checking, training insufficient, accountability unclear").

## When to Use
- Product failures, quality issues, or customer complaints requiring durable solutions
- Project failures, timeline slips, or budget overruns post-mortems
- Safety incidents, compliance violations, or operational breakdowns
- Repeated problems (same issue recurring despite previous fixes) indicating missed root cause
- Strategic failures or missed forecasts to understand decision process breakdowns
- **Do NOT use when**: Assigning blame is goal (root cause analysis is diagnostic, not punitive), predicting future problems (use forecasting instead), or conducting shallow incident response (when speed matters more than durability)

## Instructions

### Step 1: Define Problem Precisely and Establish Timeline
Vague problem definitions lead to vague root cause analysis. Define specifically what failed, when, and impact.

**Problem definition**:
- What exactly went wrong? (Not "project failed" but "project delivered 60 days late with 40% over budget")
- When did problem occur? (Specific date, and when was problem discovered? Gap between occurrence and discovery matters)
- How was problem discovered? (By whom? How did they detect it?)
- What was impact? (Revenue loss, customer churn, safety risk, etc. Quantify if possible)
- Scope: Is this problem isolated to one area or broader pattern?

**Timeline establishment**:
- When did preconditions for failure exist? (When did root cause originate?)
- When did early warning signs appear that problem was developing? (Could earlier intervention have prevented?)
- When did problem become critical? (At what point became irreversible?)
- What events preceded failure? (What happened in prior week/month that set stage?)

Example: "Product latency increased from 200ms to 2000ms on March 15, customer noticed March 16, we investigated starting March 17. Root cause investigation should trace back to infrastructure changes or code deployments in prior week, identify what warning signs we missed."

### Step 2: Map Immediate Causes Using Fishbone (Ishikawa) Diagram
Fishbone diagram structures thinking about multiple cause categories preventing premature fixation on first apparent cause.

**Fishbone categories** (standard; customize for your domain):
- **People**: Skills insufficient? Training inadequate? Staffing levels? Communication breakdown? Motivation/incentive misaligned?
- **Process**: Was process documented? Did process have built-in checkpoints? Was process followed? Had process changed recently?
- **Systems/Tools**: Did systems fail? Did tools have capability gaps? Were systems integrated properly? Data quality issues?
- **Environment/Conditions**: External factors? Market conditions? Resource constraints? Time pressure?
- **Materials/Inputs**: Raw material quality? Supplier issues? Data quality? Dependency failures?
- **Organizational**: Accountability clear? Decision-making structures? Cross-functional coordination? Were incentives aligned?

**Fishbone analysis process**:
For each category, brainstorm: What in this category contributed to failure? Don't limit to one cause per category; multiple causes often combine.

Example problem: "Product latency increased 10x"
- **People**: Engineer deployed code without testing; code reviewer didn't catch issue; on-call responder slow to detect
- **Process**: No pre-production testing gate; incident detection relies on customer complaints not automated alerting; no rollback procedure documented
- **Systems**: Monitoring didn't trigger alerts for elevated latency; database query optimization missing; caching layer misconfigured
- **Environment**: Traffic spike from viral social media post; baseline latency already elevated from prior code deployments
- **Organizational**: No on-call incident commander role; accountability for code quality vs. shipping speed unclear; on-call engineer burned out from frequent pages

Fishbone identifies 10-15 contributing factors, not just one cause. This prevents "fix one thing and problem recurs" pattern.

### Step 3: Conduct 5 Whys Analysis
5 Whys traces back through causal chains to systematic root cause by repeatedly asking "why?" Stops when reaching controllable factor your organization can change.

**5 Whys process**:
1. **Why did latency increase?** Because code deployed caused database queries to become inefficient
2. **Why did code review miss the issue?** Because code reviewer didn't have expertise in database optimization; focused on code style not performance
3. **Why didn't code reviewer have expertise?** Because team hasn't invested in database performance training; hiring has prioritized feature velocity over depth
4. **Why is feature velocity prioritized over depth?** Because OKRs measure feature launch rate; technical quality metrics absent; organizational incentives misaligned
5. **Why are incentives misaligned?** Because compensation and promotion criteria reward shipping features fast over preventing problems; no penalty for technical debt accumulation

Root cause identified: **Organizational incentive structure rewards short-term shipping over long-term quality.**

Key principle: Stop when you reach controllable cause your organization can influence. "Why did database queries become inefficient?" leads to "engineer didn't optimize" (symptom). Continue to "Why didn't process prevent unoptimized queries?" → "No code review expertise" → "No training investment" → "Incentive structure misaligned" (root cause).

**Common 5 Whys mistakes**:
- Stopping after 2-3 whys (stops at proximate cause, not root cause)
- Treating external factors as unarguable (e.g., "Traffic spike happened" → don't dig deeper into why systems couldn't handle spike)
- Blaming individual ("Engineer made mistake") instead of system ("What process gap allowed mistake?")

### Step 4: Develop Fault Tree Analysis for Complex Failures
For complex failures with multiple interdependent causes, fault tree makes causal logic explicit.

**Fault tree structure**:
- **Top event**: The problem (e.g., "Customer data deleted")
- **Intermediate events**: Contributing factors (e.g., "Backup failed AND restore procedure failed")
- **Primary events**: Basic causes not further decomposed (e.g., "Backup software malfunction," "Restore testing inadequate")

**Fault tree logic**:
- **AND gate**: All contributing factors must occur for failure. (Failure occurs only if backup failed AND restore procedure flawed AND no manual recovery attempted)
- **OR gate**: Any one factor causes failure. (System crashes if disk fails OR memory insufficient OR CPU overloaded)

**Developing fault tree**:
1. Identify top event
2. Ask: What must be true for this top event to occur?
3. For each factor, ask: Is this a fundamental cause, or can it be broken down further?
4. Break down further into sub-causes with AND/OR logic
5. Continue until reaching basic causes you can't reduce further

Example fault tree: "Customer data deleted"
```
Top: Customer data deleted
├─ AND gate: Deletion executed AND recovery failed
   ├─ Deletion executed
   │  └─ OR gate (user action OR system action)
   │     ├─ User accidentally deleted data
   │     └─ Batch job executed delete unintentionally
   └─ Recovery failed
      └─ AND gate: Backup unavailable AND manual recovery impossible
         ├─ Backup unavailable
         │  └─ OR gate (backup failure OR retention policy)
         │     ├─ Backup software malfunction
         │     └─ Backup retention policy deleted backups prematurely
         └─ Manual recovery impossible
            ├─ No data recovery procedure documented
            ├─ Data recovery specialist unavailable
            └─ Data scrambled/corrupted (couldn't be recovered)
```

Fault tree reveals that preventing problem requires addressing multiple paths: Prevent accidental deletion (user controls, confirmation prompts), ensure backup availability (software testing, retention policy), and enable manual recovery (documentation, capability).

### Step 5: Conduct Pareto Analysis to Prioritize Root Causes
Pareto principle (80/20 rule): Roughly 80% of problems come from 20% of causes. Prioritize the vital few causes, not the trivial many.

**Pareto analysis steps**:

1. **Quantify contributing factors** from fishbone analysis by frequency or impact:
   - Customer complaints: "Complaint type A: 40%, Complaint type B: 35%, Complaint type C: 15%, Complaint type D: 10%"
   - Revenue loss: "Failure reason X: $500K, Reason Y: $200K, Reason Z: $50K"
   - Incident frequency: "Cause A responsible for 25 incidents, Cause B: 8 incidents, Cause C: 3 incidents"

2. **Create Pareto chart** showing factors ordered by impact, with cumulative % line:
   - X-axis: Root causes (ranked by frequency/impact)
   - Y-axis: Frequency/Impact (left); Cumulative % (right)
   - Find "elbow" where cumulative % reaches ~80%

3. **Identify vital few (20% of causes causing 80% of impact)**: Prioritize these for elimination

Example: "Product defects"
- Missing null check: 45 defects (40%)
- Incorrect variable type: 30 defects (27%)
- Logic error: 20 defects (18%)
- Typo/naming: 15 defects (13%)
- Performance issue: 2 defects (2%)

Pareto chart shows first three causes account for 85% of defects. Fix these three and you solve majority of defect problem. The last two are distractions (only 15% of problem).

Applies to root causes too: "What % of engineering problems come from inadequate testing?" vs. "What % from unclear requirements?" vs. "What % from poor communication?" Pareto reveals which systemic problem deserves most remediation investment.

### Step 6: Identify Systemic vs. Individual Root Causes
Distinguish between one-off errors and systemic failures. Systems problems are those that would cause future failures if not fixed; individual problems happen once and don't recur.

**Systemic causes** (require process/system change to prevent recurrence):
- Process lacks error-checking or validation
- Training insufficient or absent
- Incentive structure rewards undesirable behavior
- Tools inadequate for task
- Communication/handoff point broken
- No accountability for outcome

**Individual causes** (unlikely to recur from same person/circumstance):
- Individual mistake (usually caught by system; indicates system let it through)
- Unusual circumstance (combination of events unlikely to repeat)
- Bad luck (random failure)

**Analysis principle**: Assume individual cause is symptom of system failure. Example:
- **Symptom**: "Developer deployed untested code causing outage"
- **System failure**: Why didn't code review, testing, staging environment, and automated testing gates catch this?

Shift from "How do we punish developer?" to "What system gaps let this developer's mistake reach production?"

Systemic root causes are more valuable to fix because prevention of recurrence is durable.

### Step 7: Assess Systemic Factors Enabling Root Cause
Look beyond immediate causes to organizational factors that enabled problems to develop undetected.

**Systemic factor categories**:

**Visibility/Detection factors**:
- Did warning signs exist but go unnoticed? (Metrics, monitoring, customer feedback channels)
- Is problem detection dependent on customer complaint vs. proactive detection?
- Are there metrics to track health of systems/processes?

**Incentive alignment factors**:
- Do incentives reward prevention or only penalize failures?
- Are quality and speed trade-offs explicit in performance metrics?
- Is there accountability for technical debt accumulation?

**Capability and training factors**:
- Does team have capability to prevent this problem?
- Is training provided for critical tasks?
- Are knowledge/expertise gaps identified and addressed?

**Process and governance factors**:
- Are processes documented and followed?
- Are checkpoints and gates in place to catch errors?
- Is there accountability for process adherence?
- Have processes been recently changed without documenting impact?

**Organizational structure factors**:
- Are responsibilities clear? (No ambiguity about "whose job" it is)
- Are cross-functional dependencies managed?
- Is decision-making authority clear?
- Does hierarchical structure enable or hinder problem detection?

**Communication factors**:
- Is critical information communicated to decision-makers?
- Are handoff points between functions documented?
- Is there psychological safety to raise concerns?

Example: Product latency failure traced to systemic factors:
- **Visibility**: Monitoring wasn't checking query performance (only endpoint latency); customer complaints were only way to detect
- **Incentives**: Performance reviews emphasized feature shipping, not code quality; technical debt not tracked as risk
- **Capability**: Database optimization expertise lacking; hiring focused on feature developers not systems engineers
- **Process**: Code review didn't include performance review; no pre-production load testing gate; no rollback procedure documented
- **Communication**: On-call engineer overwhelmed by false alerts, ignored real alert; no escalation path documented

Each systemic factor reveals durable fix opportunity.

### Step 8: Test Root Cause Hypotheses with Evidence
Don't assume root causes without evidence. Test hypotheses against available data.

**Evidence to collect**:
- Logs/audit trails: What happened right before failure? (Deployment logs, code changes, configuration changes, infrastructure changes)
- Metrics: Did metrics show warning signs? (Performance degradation, error rate increase, resource utilization changes)
- Interviews: What did people observe? What were constraints they faced?
- Incident reports: Have similar issues occurred? What were previous root cause conclusions?
- Changes: What changed recently? (Code, infrastructure, process, personnel, traffic)

**Common mistakes**:
- Confirmation bias: Find one possible cause, stop investigating; ignore contradictory data
- Narrative fallacy: Create plausible-sounding story without evidence
- Insufficient data collection: Don't check logs; rely only on user reports

**Testing root cause hypothesis**:
1. State hypothesis: "Hypothesis: Code change on March 15 introduced query inefficiency"
2. Identify evidence that would support: "If true, we'd see performance degradation in metrics starting March 15; git diff would show query changes; latency would correlate with specific code deployment"
3. Identify evidence that would contradict: "If hypothesis wrong, we'd see latency issues before March 15; or latency wouldn't improve when code rolled back"
4. Collect evidence and evaluate: "Logs show latency increased exactly at 3:15 PM on March 15, matching deployment time; git diff confirms query change; latency immediately improved when code rolled back → hypothesis strongly supported"

Only accept root cause when evidence supports it, not just plausibility.

### Step 9: Develop Corrective Actions Addressing Root Causes
Distinguish between short-term fixes (stabilize problem) and corrective actions (prevent recurrence).

**Short-term fixes** (immediate, stabilize situation):
- "Roll back deployment to restore service"
- "Manual data recovery from backup"
- "Increase resources to handle load"

These restore service but don't prevent recurrence if root cause not addressed.

**Corrective actions** (address root causes):
For root cause "Process lacked code review expertise," corrective action: "Conduct database optimization training for all code reviewers; establish performance review checklist for database queries; add automated query performance testing to CI pipeline"

For root cause "Monitoring didn't detect performance degradation," corrective action: "Add query latency metrics to monitoring; set alerts for query latency >500ms; include query performance in on-call dashboard"

For root cause "Incentive structure valued speed over quality," corrective action: "Revise OKRs to include quality metric; add code quality/technical debt reduction to engineering goals; tie compensation reviews to quality outcomes"

**Corrective action attributes**:
- **Specific**: Not "improve process" but "add performance review checklist to code review template"
- **Measurable**: "Query performance degradation reduced by 80%" not "better queries"
- **Owned**: Named person responsible for implementation
- **Deadline**: Completion date (not "ongoing")
- **Cost-benefit documented**: Is investment reasonable relative to problem prevention value?

### Step 10: Create Root Cause Analysis Report and Prevention Plan
Document findings and corrective actions for organizational learning and accountability.

**Root cause analysis report**:
1. **Problem summary**: What failed, when, impact
2. **Timeline**: When did preconditions exist, when were warning signs
3. **Fishbone analysis**: Contributing factors by category
4. **5 Whys analysis**: Causal chain to fundamental causes
5. **Systemic factors**: Organizational/process/incentive gaps that enabled problem
6. **Root causes ranked**: Prioritized by impact (Pareto analysis)
7. **Corrective actions**: For each vital few root cause, specific action, owner, deadline, budget
8. **Prevention mechanisms**: Going forward, how will this problem be detected/prevented?
9. **Lessons learned**: What did we learn that applies beyond this incident?

**Prevention plan** (prospective):
- **Detection**: How will we detect if problem is recurring? (Metrics, monitoring, review processes)
- **Response**: If problem recurs despite corrective actions, what's our response? (Escalation path, analysis procedure)
- **Review schedule**: When will we verify corrective actions are effective? (30 days, 90 days, 6 months)

## Output Template

### Problem Definition
- **What failed**: [Specific description of failure]
- **When**: [Date/time failure occurred; when discovered]
- **How discovered**: [How was problem detected; by whom]
- **Impact**: [Revenue loss, customer impact, safety risk, etc.; quantify]
- **Scope**: [Isolated incident or pattern; if pattern, frequency]

### Timeline
- **Precondition phase**: [When root cause condition began; what state was system in]
- **Incubation phase**: [Undetected period; could problem have been detected earlier; what were warning signs]
- **Acute phase**: [When problem became critical; impact timeline]
- **Resolution phase**: [When problem identified; resolution timeline]

### Fishbone Analysis
[Diagram or table showing contributing factors by category: People, Process, Systems, Environment, Materials, Organizational]

### Root Cause Analysis: 5 Whys
1. Why did [immediate symptom] occur? [Answer 1]
2. Why [cause 1]? [Answer 2]
3. Why [cause 2]? [Answer 3]
4. Why [cause 3]? [Answer 4]
5. Why [cause 4]? [Root cause statement]

**Root cause**: [Fundamental, controllable cause your organization can address]

### Fault Tree (if applicable)
[Diagram or text representation of causal logic showing AND/OR gates and basic causes]

### Systemic Root Causes (Ranked by Impact)
| Root Cause | Frequency | Impact | Category | Corrective Action |
|-----------|-----------|--------|----------|------------------|
| [Cause 1] | [# incidents] | [High/Med/Low] | [People/Process/Systems/Org] | [Action with owner] |
| [Cause 2] | [# incidents] | [High/Med/Low] | [People/Process/Systems/Org] | [Action with owner] |

### Corrective Actions
| Root Cause | Action | Owner | Deadline | Budget | Success Metric | Priority |
|-----------|--------|-------|----------|--------|---|---|
| [Cause] | [Specific action] | [Name] | [Date] | [$] | [Measurable outcome] | [H/M/L] |

### Prevention Plan
- **Detection mechanisms**: How will we detect if this problem recurs? (Metrics, monitoring, audit procedures)
- **Response plan**: If problem recurs, what action? (Escalation path, analysis procedure)
- **Review schedule**: When will corrective action effectiveness be verified? (30/90/180 days)

### Lessons Learned
- What did we learn about our processes/systems that applies beyond this incident?
- What should all teams understand from this incident?

## Quality Gates

1. **Problem precisely defined**: Specific failure state documented, not vague; quantified impact; timeline established from precondition to resolution
2. **Multiple analysis methods applied**: Fishbone + 5 Whys minimum; fault tree for complex failures; Pareto analysis for multi-cause failures
3. **Root cause investigation depth achieved**: Minimum 5 levels of "why?" explored; reached controllable/systemic cause not proximate symptom; individual cause identified as system failure symptom
4. **Evidence-based conclusions**: Root causes supported by logs/data/metrics, not just plausibility; contradictory evidence addressed; evidence gaps acknowledged
5. **Systemic factors identified**: Organizational/process/incentive gaps documented; not just technical causes; addressed visibility, capability, incentives, process gaps
6. **Vital few causes prioritized**: Pareto analysis applied; 20% of causes accounting for 80% of impact identified; corrective actions focus on vital few not trivial many
7. **Corrective actions specific and owned**: Actions specific (not vague), measurable, owned (named person), with deadline and budget; not just "improve process"
8. **Prevention mechanisms defined**: How problem will be detected going forward; detection depends on monitoring/metric/process not customer complaints; false negative risk considered (will we detect if corrective action fails?)
9. **Short-term fix vs. durable fix distinguished**: Immediate mitigation separated from corrective actions; not assuming problem solved just because immediate fix applied
10. **Report accessible and actionable**: Clear summary for executives; detailed analysis for implementers; lessons learned documented for organizational learning; not created then filed away

## Examples

### Good Root Cause Analysis
**Problem**: "Customer data deleted; 1,200 records lost; customer impacted for 48 hours until recovery; $50K revenue impact"

**5 Whys**:
1. Why was data deleted? Batch job scheduled daily to delete records >90 days old; logic error caused it to delete all records regardless of age
2. Why did logic error exist? Code review didn't catch it; reviewer (junior engineer) unfamiliar with deletion logic; no test case for boundary condition
3. Why was reviewer unqualified? No training for risky operations; deletion logic not documented; knowledge held only by departing engineer
4. Why was knowledge concentrated? No onboarding/documentation process; no knowledge transfer before departures; high turnover in data team
5. Why high turnover? On-call duties for data system unpredictable/frequent; compensation below market; team morale low from repeated incidents

**Systemic factors identified**:
- Visibility: No pre-deletion validation; batch job logs weren't reviewed; no alert on large-scale deletions
- Process: Code review insufficient for risky operations; no code review checklist for database changes; no pre-production testing of batch jobs
- Capability: Data systems expertise concentrated in few people; knowledge transfer process absent; training for critical operations absent
- Incentive: On-call responsibilities uneven; no incentive to prevent incidents; compensation not competitive
- Organizational: Knowledge hoarding instead of documentation; high turnover made knowledge concentration worse

**Pareto analysis**: 60% of data incidents came from batch job errors; 25% from manual operations; 15% from infrastructure failures

**Corrective actions**:
- **Immediate**: Implement pre-deletion validation; add alert on deletions >100 records; establish daily batch job review; audit other batch jobs for similar issues
- **Near-term**: Establish data operations documentation and runbook; conduct training for all engineers on deletion procedures; implement code review checklist for database changes
- **Long-term**: Implement infrastructure to prevent mass deletion (backup isolation, deletion approval workflow); redistribute on-call to reduce burden; conduct compensation review for data team
- **Prevention**: Query pre-execution validation; audit deletions monthly; knowledge management system for critical procedures

### Poor Root Cause Analysis
- "Problem: Data deleted; Root cause: Engineer made mistake in code" → Stops at proximate cause, not root cause
- "Batch job had logic error" → Identifies technical symptom, not systemic cause
- No evidence collected; no log analysis; no interview of engineer who wrote code
- No systemic factors addressed; no process/capability/knowledge gaps identified
- Corrective action: "Code reviewer should be more careful" → Individual blame, not system change
- No prevention plan; assumes problem won't recur if person is more careful

## Common Mistakes

1. **Stopping at proximate cause instead of root cause**: "Engineer made coding error" is symptom, not root cause. Root cause is "Why did code review process not catch error?" → "Why wasn't reviewer trained?" → "Why is knowledge concentrated?" Root cause requires asking until reaching controllable organizational factor.

2. **Blaming individual instead of system**: "Engineer was careless" vs. "System had no pre-deletion validation; code review process insufficient for risky operations." Individuals don't make mistakes randomly; systems enable or prevent mistakes. Blaming individual prevents recurrence prevention.

3. **Insufficient evidence collection**: Concluding root cause without checking logs, metrics, or interviewing people. Plausible stories aren't facts. "Logic error likely in batch job" vs. actually checking code, logs, and confirming what changed when.

4. **Ignoring contradictory evidence**: Finding one possible cause, assuming it's root cause, ignoring data that contradicts. Example: "Must be code logic error" but logs show batch job didn't run at all that day; actual cause was scheduler failure. Confirmation bias.

5. **Assuming system resilience exists when it doesn't**: "This shouldn't happen because we have backups." But backup retention policy deleted backups; no one tested restore procedure; recovery took 48 hours. Resilience mechanisms not tested; assumed reliability without evidence.

6. **No accountability for prevention**: Root cause analysis completed; report filed; no corrective actions assigned; no monitoring. Next incident occurs and investigation finds previous root cause analysis identified same problem. Prevention requires ownership and verification.

## Anti-Patterns

1. **Blame-focused root cause analysis**: Process used to assign fault and punish rather than prevent recurrence. Engineer defensive; doesn't fully explain what happened; team culture becomes afraid to report issues. Solution: Separate incident investigation from performance evaluation; use investigation for learning not blame; psychological safety essential for honest root cause analysis.

2. **Stopping after first fix works**: Problem stabilized; immediate mitigation applied; service restored; investigation stops. Root cause never addressed. Incident recurs. Solution: Distinguish short-term stabilization from durable correction; commit to full RCA before considering problem solved; require corrective actions before closing incident.

3. **Root cause analysis without prevention**: Thorough analysis conducted; root causes identified; corrective actions recommended; not implemented. Same problem occurs. Solution: Require preventive action implementation, not just identification; assign owner and deadline; verify corrective action effectiveness before closing.

4. **Assuming recurrence won't happen again**: "This was a one-time failure; engineer will be more careful next time; no systemic change needed." Individuals don't prevent problems; systems do. Identical failure occurs within weeks. Solution: Assume similar failure could occur unless system prevents it; design systems not relying on human vigilance for critical safety/reliability.

5. **Ignoring near-misses**: Only analyzing failures, not near-misses (times system almost failed but someone caught it). Near-misses provide same insights as failures with less organizational resistance to change. Solution: Investigate near-misses systematically; build feedback loops to catch problems before they cause failures.

6. **Too broad scope**: Root cause analysis of "sales decline" looks at entire company, all functions, everything. Becomes overwhelming and diffuse. Solution: Start with incident as narrowly scoped as possible; expand scope only if evidence leads to adjacent areas; focus on controllable factors within scope you can influence.
