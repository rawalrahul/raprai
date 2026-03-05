---
name: meeting-agenda-generator
description: "Generate structured meeting agendas with time blocks, decision points, owners, pre-reads, and follow-ups. Templates for standups, planning, retros, 1:1s, and board meetings with clear outcomes."
category: business
difficulty: beginner
model_boost: "Prevents meandering meetings without outcomes; produces focused agendas with clear owners, time discipline, and decision authority."
---

# Meeting Agenda Generator

## Purpose
A structured agenda transforms a meeting from unfocused discussion into efficient decision-making. This skill generates meeting agendas with: time blocks (enforcing discipline), decision points (clarifying authority), owners (ensuring accountability), pre-reads (respecting time), and follow-ups (tracking outcomes). Output enables efficient meetings across all contexts: standups, planning sessions, retros, 1:1s, and board updates.

## When to Use
- Recurring meetings without structure (standup, weekly sync, 1:1)
- Complex meetings requiring decisions (planning, board, launch reviews)
- Large-group meetings where side conversations derail progress (all-hands, town halls)
- Post-meeting, you often ask "What did we decide?" (agenda prevents this)
- **Do NOT use when**: Meeting has clear agenda already; meeting is informal brainstorm (structure stifles creativity); meeting is social/team-building (agendas are rigid).

## Instructions

### Step 1: Define Meeting Purpose & Desired Outcome
Every meeting needs a 1-sentence purpose. This filters agenda items: Does this item support the purpose?

**Purpose Examples**:
- Standup: "Unblock impediments and sync progress on {{sprint goal}}"
- Planning: "Lock prioritized features, milestones, and resource allocation for Q2"
- Retro: "Identify what worked, what didn't, and 3 process improvements"
- 1:1: "Review {{employee}} progress on OKRs and discuss growth/concerns"
- Board: "Deliver Q1 results, secure board approval for Q2 strategy"

If you can't write 1 sentence, the meeting purpose is unclear—cancel it.

### Step 2: Identify Decision Points (Not Discussion Points)
Distinguish decisions (requires authority, has yes/no or A/B outcome) from discussions (exploration, no immediate decision needed).

**Decision Points**: "Approve $500K marketing budget for Q2", "Decide on acquisition target: Company A vs. Company B", "Release v2.0 by March 1"

**Discussion Points**: "Share customer feedback trends", "Explore possible directions for product roadmap"

If you list only discussion points, attendees leave without clarity. Ensure ≥50% of agenda is decisions.

### Step 3: Assign Owners & Decision Authority
For each agenda item, assign:
- **Owner** (who leads discussion): CEO, VP Product, etc.
- **Decision Authority** (who decides): If different from owner (e.g., owner is PM, but SVP Product has final say)
- **Stakeholder Input** (who must be heard before decision)

This prevents: "We discussed for 30 minutes but nobody has authority to decide."

### Step 4: Allocate Time Blocks
Calculate total time available. Subtract 5 minutes (start/end buffer). Allocate: 40% to decisions, 30% to updates/reports, 30% to discussion/problem-solving.

Example: 60-minute meeting
- Agenda Item 1 (Decision): 15 min
- Agenda Item 2 (Decision): 15 min
- Updates: 15 min
- Retro/Discussion: 15 min

Publish specific time blocks (e.g., "7:30-7:45am: Item 1, 7:45-8:00am: Item 2"). Enforce with visible timer.

### Step 5: Identify Pre-Reads & Preparation
For each major agenda item, specify what attendees should review beforehand. This prevents: "I need 10 minutes to explain the budget..."

Example Pre-Reads:
- Board review: Read Q1 metrics dashboard (3 min read), Q2 strategy doc (5 min)
- Planning: Review customer request backlog (filtered to top 10, 5 min), competitive updates (3 min)

### Step 6: Plan Outputs & Follow-ups
Before meeting, define: What outputs does this meeting produce? What happens next?

Example Outputs:
- **Decision record**: "Board approves $5M Series A timeline. CFO will close by April 1."
- **Action items**: "Engineering ships API by March 15. Marketing prepares launch announcement by March 10."
- **Notes**: "Retro identified 3 process improvements: implement by next retro."

### Step 7: Review & Prune
Ruthlessly cut agenda items that don't support the purpose. Typical meeting: 30% of items don't belong. Ask: "Is this decision/update critical this week? If not, cut."

## Output Template

```markdown
# Meeting Agenda: {{Meeting Name}}
**Date & Time**: {{Date}}, {{Time}} ({{Duration}} minutes)
**Location**: {{Zoom link / Room number}}
**Organizer**: {{Name}}

---

## MEETING PURPOSE
{{One sentence: what is this meeting designed to accomplish}}

**Desired Outcome**: {{Specific decision(s) or output by end of meeting}}
**Attendees**: {{Must-attend}}, {{Optional}}
**Pre-Reads**: {{Docs to review beforehand, with estimated time}}

---

## AGENDA

### Item 1: {{Agenda Item Title}} ({{Start Time}}-{{End Time}}, {{# minutes}})
**Type**: {{Decision / Update / Discussion / Retro}}
**Owner**: {{Who leads this segment}}
**Decision Authority**: {{Who has final say (if different from owner)}}
**What We're Deciding**: {{Specific decision: Approve {{}} / Choose {{A vs B}} / Confirm {{target}}}}
**Stakeholder Input Needed**: {{Who must be heard (e.g., "Finance input on budget, Sales on timeline")}}
**Pre-Read**: {{Resource to review}}, {{X min}}

**Talking Points**:
- {{Context or background}}
- {{Key facts/data supporting decision}}
- {{Potential objections & rebuttals}}

**Success Criteria for This Item**: {{How we know decision is clear (e.g., "Board votes yes/no", "Team alignment on 3 action items")}}

---

### Item 2: {{Next Item}}
**Type**: {{}}
**Owner**: {{}}
**Decision Authority**: {{}}
**What We're Deciding**: {{}}
**Stakeholder Input**: {{}}
**Pre-Read**: {{}}

---

### Item 3: {{}}
...

---

## DECISION RECORD (Template to Fill During Meeting)

### Decision 1: {{What We Decided}}
- **Decided By**: {{Decision Authority}}
- **Vote/Consensus**: {{Unanimous / {{#}} against / Consensus after debate}}
- **Rationale**: {{Why this decision (1-2 sentences)}}
- **Owner for Execution**: {{Who implements}}
- **Timeline**: {{When completed}}
- **Open Questions**: {{Any unresolved items for next meeting}}

---

## ACTION ITEMS (Capture During Meeting)

| Action Item | Owner | Due Date | Notes |
|---|---|---|---|
| {{Action}} | {{Name}} | {{Date}} | {{Acceptance criteria}} |
| {{}} | {{}} | {{}} | {{}} |

---

## NEXT MEETING
**Date**: {{When}}
**Purpose**: {{Focus for next meeting}}
**Pre-Read Prep**: {{What should be ready}}

---

## MEETING TEMPLATES

## A. STANDUP (15 minutes, Daily or Bi-Weekly)

**Purpose**: Unblock impediments, sync progress on sprint goal, identify risks.

**Agenda**:
1. **Sprint Goal Review** (2 min): Owner = Scrum Master
   - {{Current goal}}: On track? At risk? Off track?

2. **Blocker Review** (3 min): Owner = Team
   - {{Team member 1}}: Any blockers? {{Resolution needed}}
   - {{Team member 2}}: Any blockers?

3. **Progress Updates** (5 min): Owner = Team (2 min per team = 6 people max)
   - {{Person 1}}: {{What I'm working on}}, {{What's next}}, {{Blockers}}
   - {{Person 2}}: {{}}

4. **Risks & Course Correction** (3 min): Owner = Team Lead
   - {{Any risks surfaced?}} {{Mitigation}}

**Decision Points**: Unblock impediments (real-time). Escalate risks.

**Success Criteria**: Everyone understands sprint progress, blockers are identified and owners assigned, meeting ends in 15 min.

---

## B. WEEKLY PLANNING (60 minutes)

**Purpose**: Prioritize work for the week, align team on goals, surface dependencies.

**Agenda**:
1. **Previous Week Retro** (10 min): Owner = Team Lead
   - {{What went well?}} {{What didn't?}} {{One process change for this week}}

2. **Business Context** (10 min): Owner = Manager
   - {{Key company priorities this week}} (e.g., "Launch feature X, hit sales target Y")
   - {{Customer feedback or market signals}}
   - {{Resource constraints or changes}}

3. **Prioritized Tasks** (30 min): Owner = Manager/Team Lead
   - {{Task 1 (P0: blocking other work)}}: Owner {{name}}, 5 days
   - {{Task 2 (P1: high value)}}: Owner {{name}}, 3 days
   - {{Task 3 (P2: nice-to-have)}}: Owner {{name}}, 2 days
   - (Total should be 5 days max per person)

4. **Dependencies & Risks** (5 min): Owner = Team Lead
   - {{Task A depends on Task B from other team}}
   - {{Risk: if X doesn't happen, Y is blocked}}

5. **End-of-Week Success Criteria** (5 min): Owner = Manager
   - {{We'll know this week was successful if...}}

**Decision Points**: Confirm task prioritization. Resolve dependencies.

**Success Criteria**: Every team member leaves with clear top 3 tasks. Dependencies are documented and communicated to other teams. Realistic weekly plan (not 120% of capacity).

---

## C. RETROSPECTIVE (60 minutes, Quarterly or After Major Release)

**Purpose**: Identify what worked, what didn't, and process improvements for next period.

**Agenda**:
1. **Celebration of Wins** (10 min): Owner = Facilitator
   - {{What are we proud of from this quarter/project?}}
   - {{Shout-outs to team members}} (async pre-work: post 1 shout-out beforehand)

2. **What Went Well** (10 min): Owner = Facilitator
   - {{Process or practice that accelerated us}} (e.g., "Daily standups kept us aligned")
   - {{Team strength that made difference}} (e.g., "X's technical depth solved critical bug")
   - {{External factor that helped}} (e.g., "Customer champion advocated internally")

3. **What Didn't Go Well** (15 min): Owner = Facilitator
   - {{Process or practice that slowed us down}} (e.g., "Lack of clear prioritization wasted 30% of sprint")
   - {{Skills gap or team constraint}} (e.g., "No mobile expertise delayed iOS launch")
   - {{External factor that hurt}} (e.g., "Dependency on other team slipped 3x")
   - **Ground Rule**: Focus on systems/processes, not individual blame.

4. **Root Cause Analysis** (10 min): Owner = Facilitator (for 1-2 biggest blockers)
   - {{Blocker}}: {{Why did it happen?}} {{Why did that happen?}} (5 Whys)
   - {{Action to prevent recurrence}}

5. **Process Improvements** (10 min): Owner = Team
   - {{Propose 1-2 process changes for next period}}
   - {{How we'll measure if it improves}} (e.g., "Sprint velocity increases 15%", "Bugs decrease 25%")
   - {{Owner to implement}}

6. **Owner Accountability** (5 min): Owner = Manager
   - {{Which improvements are we committing to?}}
   - {{Who owns each improvement?}}
   - {{How we'll track in next retro}}

**Decision Points**: Commit to 1-2 process improvements (not 5+). Assign owners.

**Success Criteria**: Team identifies ≥2 process improvements with owners and success metrics. No blame, focus on systems.

---

## D. 1:1 (30 minutes, Weekly or Bi-Weekly)

**Purpose**: {{Employee name}}: Review progress on OKRs, discuss growth/concerns, strengthen relationship.

**Pre-Work**:
- {{Employee}}: Complete self-review (5 min)
  - {{What OKRs did I hit?}} {{What did I struggle with?}}
  - {{What I'm proud of this week}} {{What I want to improve}}
  - {{Anything I want to discuss with manager}}

- {{Manager}}: Review performance context (5 min)
  - {{How is employee tracking against OKRs?}}
  - {{Any feedback from peers/customers?}}
  - {{Growth opportunities or concerns?}}

**Agenda**:
1. **Wins & Celebrations** (5 min): Owner = Employee
   - {{What are you proud of this week?}}

2. **OKR Progress & Challenges** (10 min): Owner = Employee
   - {{OKR 1}}: {{Progress to date}}, {{What's working}}, {{What's hard}}
   - {{OKR 2}}: {{}}
   - {{Manager feedback}}: {{Progress looks {{on/off}} track, here's why}}

3. **Growth & Development** (8 min): Owner = Manager
   - {{Growth goal for this period}}: {{Progress}}
   - {{Skill gap or stretch project}}: {{How can I help?}}
   - {{Career interest}}: {{What's next for you?}}

4. **Feedback (Both Directions)** (5 min): Owner = Both
   - {{Employee to manager}}: {{Feedback on support, priorities, process}}
   - {{Manager to employee}}: {{Strengths to leverage}}, {{Areas to develop}}

5. **Next Week Preview** (2 min): Owner = Manager
   - {{What's the priority for next week?}}
   - {{Any support you need?}}

**Decision Points**: Confirm growth path. Address any concerns/blockers.

**Success Criteria**: Employee leaves energized. No surprises on performance. Path forward is clear.

---

## E. BOARD MEETING (90-120 minutes, Quarterly)

**Purpose**: Report Q{{X}} results, secure board approval for Q{{X+1}} strategy, get advisor input on key decisions.

**Pre-Reads**:
- **Board materials** (15 min read):
  - Metrics dashboard: {{Revenue, growth rate, churn, CAC, NPS, headcount}}
  - {{Narrative of Q results: successes, misses, learnings}}
  - {{Q{{X+1}} strategy & key initiatives}}
  - {{Financial forecast & runway}}

**Agenda**:
1. **Opening Remarks** (5 min): Owner = CEO
   - {{Q{{X}} narrative (1-2 minute summary of materials)}}
   - {{Energy/mood of company}}

2. **Metrics Deep Dive** (20 min): Owner = CEO/CFO
   - {{Revenue}}: {{${{Q}} revenue}}, {{{{%}} growth}}, {{Customer acquisition vs. expansion}}
   - {{Churn & Retention}}: {{Monthly churn {{%}}}}, {{why trending {{up/down}}}}
   - {{Unit Economics}}: {{CAC {{$}}}}, {{LTV {{$}}}}, {{Payback {{months}}}}
   - {{NPS}}: {{Score}}, {{trending}}, {{customer sentiment}}
   - {{Team & Burn}}: {{Headcount}}, {{burn rate}}, {{runway months}})

3. **Major Misses & Learnings** (15 min): Owner = CEO/Relevant Lead
   - {{What we planned to hit that we missed}}: {{Target vs. actual}}
   - {{Why it happened}}: {{Root cause}}
   - {{What we learned}}: {{How this changes next quarter}}

4. **Q{{X+1}} Strategy & Priorities** (20 min): Owner = CEO/Department Heads
   - {{Company OKR 1}}: {{Owner}}, {{Target metric}}, {{Why this matters}}
   - {{Company OKR 2}}: {{}}
   - {{Resources / Hiring needed}}: {{Headcount}}, {{Budget}}
   - {{Key risks & mitigation}}

5. **Key Decision Points (Require Board Vote)** (15 min): Owner = CEO
   - {{Decision 1}}: {{Approve ${{}} funding use}}, {{for what purpose}}
   - {{Decision 2}}: {{Approve new {{hire/product direction/partnership}})}}
   - {{Board votes}}

6. **Q&A & Board Advice** (15 min): Owner = Board Members
   - {{Questions on metrics, strategy, execution}}
   - {{Advisor input on decisions, market context, network introductions}}

7. **Closed Session (If Applicable)** (10 min): Owner = Board
   - {{CEO and board discuss governance, compensation, or sensitive matters}}

**Decision Points**: Board votes on funding use, major strategic decisions, material hires.

**Success Criteria**: Board clearly understands Q performance and Q{{X+1}} direction. Board alignment on major decisions. CEO leaves with clear advisory input.

---

## FOLLOW-UP TEMPLATE (Send Within 24 Hours)

**Meeting**: {{Meeting Name}}, {{Date}}

**Decisions Made**:
1. {{Decision}}: Approved {{}} by {{Authority}}
2. {{Decision}}: {{}}

**Action Items**:
| Action | Owner | Due | Status |
|---|---|---|---|
| {{}} | {{}} | {{}} | 🟢 On Track |

**Next Meeting**: {{Date}}, {{Purpose}}

**Questions?**: Reply in thread or schedule follow-up.
```

## Quality Gates
- [ ] Meeting purpose is 1 sentence; all agenda items support it
- [ ] ≥50% of agenda is decision points with clear decision authority
- [ ] Each agenda item has an owner and time block (enforces discipline)
- [ ] Pre-reads are identified with estimated time (respects attendee time)
- [ ] Decision record template captures what was decided, by whom, and why
- [ ] Action items specify owner, due date, and acceptance criteria
- [ ] Standup uses 15 min format with blocker/risk focus
- [ ] Planning meeting results in prioritized task list (not 120% capacity)

## Examples

### Good Output (excerpt)
```
Meeting: "Q1 Planning - Engineering"
Purpose: Lock prioritized features, engineering capacity, and success metrics for Q1.

Item 2: Prioritize Feature Roadmap (10:30-11:00am, 30 min)
Type: Decision
Owner: VP Product
Decision Authority: VP Product (after engineering input)
What We're Deciding: Approve top 5 features for Q1, confirm engineering effort estimate aligns with capacity
Stakeholder Input: Engineering lead must confirm 5-feature plan is realistic. Sales input on customer requests.

Pre-Read: Customer request backlog (5 min), competitive update (3 min)

Talking Points:
- Customer feedback: Feature A (requested by 15 customers), Feature B (10x ROI potential), Feature C (competitive response)
- Engineering estimate: Total 40 engineering weeks available Q1 (5 engineers × 8 weeks). Feature set = 32 weeks (80% utilization).
- Timeline: Release features in sprints: F A+B (Sprint 1), F C (Sprint 2), F D+E (Sprint 3)

Success Criteria: Engineering confirms 5-feature plan is realistic and achievable. Team leaves with clear priority order.

---

Decision Record:
Decision: Approve Q1 feature roadmap (Features A, B, C, D, E)
Owner: VP Product
Rationale: Balances customer feedback (#1 request A), revenue impact (B, C, D), and competitive response (D, E). 32-week estimate = healthy utilization with buffer for bugs/refactoring.
Action Owner: VP Product, coordinate sprint planning by EOW
Timeline: First feature (A+B) ships Sprint 1 (3 weeks), rest in Sprints 2-3
```

### Bad Output (what to avoid)
```
Meeting Agenda:
1. Updates from everyone (30 min)
2. Discuss roadmap (20 min)
3. Any other business (10 min)

(Why this fails: No decision points. No time blocks. No owners. "Updates" doesn't say what. "Discuss roadmap" is vague—are we deciding, or exploring?)
```

## Common Mistakes

1. **All Discussion, No Decisions**: 60-minute meeting full of "Let's discuss X." Nobody leaves with clarity on what was decided. Result: Same discussion next week. Better: 40% agenda dedicated to decisions with clear authority. "We decide between A and B; CEO has final say."

2. **No Pre-Reads, So First 10 Minutes is Explanation**: Meeting starts with person explaining context everyone should have reviewed. If pre-read is <5 min and clear, most attendees come prepared. If pre-read is vague or long, they don't.

3. **Time Blocks Ignored**: Agenda says "Item 1: 10 min" but discussion goes 25 min, other items get cut. Better: Start with timer visible (Google Meet shows elapsed time). When 10 min is up, say "Time—take discussion offline or next meeting."

4. **No Decision Authority Stated**: "Let's decide on pricing tier A vs. B." Discussion happens, no conclusion. Turns out the department head wasn't in meeting, so no authority to decide. Clarify upfront: "This decision is made by {{Name}} after hearing input from {{team}}."

5. **Agenda Items That Aren't Actually Decisions**: "Let's hear from Finance about Q1 spend" (update, not decision). Better: "Finance requests $100K for Q1 tools/services. Approve? Yes/No." Now there's a decision.

## Anti-Patterns

1. **Invitation Bloat**: Meeting invites 15 people, 5 contribute, 10 listen passively. Better: Invite 5 decision-makers + 2-3 key input roles. Record meeting for others to watch async. "Most people don't need to attend; watch 30-min recording and comment by EOD if you have input."

2. **"Parking Lot" Everything**: Conversation veers off-topic. Instead of addressing, say "That's a good point; let's parking-lot it." By end of meeting, parking lot has 10 items, none get addressed. Better: Track parking lot items with owners and schedule separate discussion. "Item X: We'll discuss {{date}} with {{group}}"

3. **No Follow-up**: Meeting ends, no decision record sent. Attendees interpret decisions differently. "I thought we decided X" vs. "No, we decided Y." Better: Standup = send action items within 4 hours (1-min effort). Big decisions = 30-second email with decision, owner, timeline.

4. **Recurring Meetings That Lose Purpose**: Standup starts as 15-min sync but becomes 45-min design discussion. Weekly planning becomes show-and-tell. Better: Defend meeting purpose. "This standup is for blockers only. Design discussion happens in design retro, not here."

5. **One Person Dominates**: CEO or senior person talks for 40 of 60 minutes. Others silent. Result: Their view is heard, others feel unheard. Better: Facilitator enforces time, ensures turn-taking. "Thanks for that insight, let's hear from {{person}} now."

