---
name: ux-research-report-writer
description: "Transform user research into actionable findings with severity ratings, evidence-backed recommendations, and priority matrices. Makes research data usable for design and product decisions."
category: professional
difficulty: intermediate
model_boost: "Weak models produce research summaries; this skill converts research into finding cards with severity ratings, evidence, and prioritized recommendations for decision-making"
---

# UX Research Report Writer

## Purpose
A UX research report translates raw research data (interview transcripts, video sessions, survey responses, task completion metrics) into findings that drive design and product decisions. Unlike a research summary (which describes what you found), a research report answers: "What should we change and why?" and "What's the impact if we don't?" This skill walks you through structuring findings with severity ratings, supporting evidence, and clear recommendations that leaders and designers will act on.

## When to Use
- Concluding usability testing, user interviews, or diary studies
- Presenting research findings to stakeholders (design team, product team, leadership)
- Informing design decisions or roadmap prioritization
- Creating a research repository for future reference
- Building business case for UX improvements
- **Do NOT use when**: research is incomplete (finish studies first), you lack evidence for claims (don't speculate), or you're presenting preliminary findings (clearly mark as "preliminary" and discuss next steps)

## Instructions

### Step 1: Establish Study Methodology (200-300 words)
Set context so readers understand research rigor and limitations.

**Components**:

**Research Type**: Clearly state method
- Usability testing (moderated or unmoderated)
- User interviews (depth interviews, exploratory)
- Diary study or diary entries
- Survey or questionnaire
- Analytics analysis
- A/B test comparison

**Participants** (anonymized):
- Number of participants: 8
- Participant profile: "8 B2B SaaS managers (5 male, 3 female), ages 28-55, with 3-15 years experience, using project management software daily"
- Recruitment method: "Recruited from existing customer base; screened for job title and software familiarity"
- Compensation: "Offered $50 Amazon gift card"
- Incentive bias note: (if any) "Incentive may have skewed participation toward motivated users; results may not represent disengaged users"

**Study Design**:
- Duration: How long did research take?
- Tasks/Questions: If usability test, "Asked participants to complete 5 core tasks: create project, invite team, set timeline, track progress, export report"
- Success Metrics: "Measured: task success rate, time on task, number of errors, perceived difficulty (1-5 scale), and NPS question"

**Data Collection**:
- Video recordings: "Sessions recorded and transcribed"
- Note-taking: "Researcher took contemporaneous notes on task behavior and participant comments"
- Measurement: "Time on task measured via screen recording; error rates counted manually"

**Analysis Approach**:
"Sessions were reviewed independently by 2 researchers who identified recurring themes. Themes were then coded into finding categories. Only findings mentioned by 3+ participants (or showing high severity for single individuals) are included in this report."

**Limitations**:
- Sample size: "N=8 is small; findings are directional, not statistically significant"
- Generalizability: "Participants are existing customers; may not represent prospective users or inactive accounts"
- Timing: "Testing occurred in March 2024; seasonal or product changes may affect applicability"

Be honest about limitations. Credibility increases when you acknowledge constraints.

### Step 2: Executive Summary (200-300 words)
Busy stakeholders may read only this section. Make it count.

**Structure**:

**Problem Statement** (1-2 sentences):
"This usability study examined how B2B SaaS project managers use the planning and collaboration features. We identified barriers to adoption that prevent users from fully leveraging the platform."

**Key Findings** (3-5 bullets):
List your most critical findings without detail:
- "64% of participants struggled to invite team members; the invite flow is unclear and requires too many steps"
- "Custom field creation is a requested feature; 6 of 8 participants wanted ability to add custom fields"
- "Users don't discover timeline/Gantt view; only 1 of 8 found it without prompting"
- "Mobile app is underutilized; users expected same functionality as desktop but key features are missing"

**Business Impact** (1 paragraph):
"These findings directly impact adoption and retention. Users who struggle with core workflows (inviting teams, creating timelines) are less likely to expand usage across their organization or renew their subscription. The requested custom fields feature would enable adoption in industries with unique workflows (design agencies, consulting firms)."

**Recommended Actions** (3-5 bullets):
Immediately prioritized recommendations:
- "Redesign invite flow: reduce from 5 steps to 2 steps; test with 3 users"
- "Add custom field feature to roadmap: high adoption impact, moderate development effort"
- "Improve Gantt view discoverability: add prominent link in left sidebar; test findability with 5 new users"
- "Audit mobile app feature parity: identify most-used features and ensure mobile support"

**Timeline**:
"We recommend starting with quick wins (invite flow redesign) within 1 sprint, and planning custom fields for Q3 roadmap."

### Step 3: Create Finding Cards (50-100 words each)
A finding card is a standalone, actionable insight. Structure them consistently.

**Finding Card Template**:

**Title**: Clear, concise problem statement
"Invite Flow is Too Complex (5 Steps) Reducing Team Adoption"

**Severity**: High/Medium/Low rating
"**Severity: HIGH** — Blocks core workflow (inviting team members); 64% of participants struggled"

**Evidence**: Quote or behavioral observation proving this is real
"6 of 8 participants got stuck at the 'set team roles' step. One participant said: 'I don't understand what these role options mean. There are too many decisions here.' Another abandoned the task after 3 minutes."

**Frequency**: How common is this problem?
"Experienced by 6 of 8 participants (75%)"

**Recommendation**: Specific, actionable fix
"Redesign invite flow: (1) Reduce decision points from 5 to 2. (2) Pre-select recommended role based on invite method (email, link, integration). (3) Make roles optional—users can assign roles later. (4) Add inline help text explaining each role."

**Effort/Impact Matrix**: Quick estimate
"Effort: 1 sprint | Impact: High (enables team collaboration, unblocks feature adoption)"

**Example Finding Cards** (multiple):

---

**Finding 1: Gantt View is Undiscovered**

**Severity: MEDIUM** — Only 1 of 8 participants found the Gantt/timeline view without prompting. Yet 7 of 8 said they would use it if they knew it existed.

**Evidence**:
"When asked 'How would you visualize the project timeline,' 7 participants assumed the feature didn't exist or looked in the wrong place. One participant said: 'You can't see projects as a timeline? That's the first thing I'd want.' After being shown the view, all 7 said they'd use it."

**Frequency**:
"Unknown feature: 7 of 8 participants | Likely to use if discovered: 7 of 8"

**Recommendation**:
"Improve discoverability: (1) Add 'Gantt View' button to top navigation or project sidebar. (2) On-board new users with a 'timeline available' tip. (3) Use analytics to understand where users look for this feature and place accordingly. (4) A/B test navigation placement with 5 new users."

**Effort/Impact Matrix**:
"Effort: 0.5 sprint (navigation change only) | Impact: Medium (unlocks feature adoption, increases user satisfaction)"

---

**Finding 2: Custom Fields Requested for Industry-Specific Workflows**

**Severity: MEDIUM** — Not blocking immediate adoption, but prevents expansion into specialized industries.

**Evidence**:
"Design agencies and consulting firms specifically requested custom fields. A design agency manager said: 'We track client deliverables and approval status—that's not a default project field. We'd need custom fields to fit our workflow.' Without this, they're evaluating competitor tools."

**Frequency**:
"Requested by 6 of 8 participants | Blocking adoption for 2 of 8 (specialized industries)"

**Recommendation**:
"Develop custom field feature: (1) Allow users to create text, dropdown, date, and number custom fields. (2) Make fields available at project and task level. (3) Prioritize dropdown and date fields (most requested). (4) Plan for Q3 roadmap; validate with 3 design agencies and 2 consulting firms before building."

**Effort/Impact Matrix**:
"Effort: 2-3 sprints (moderate complexity) | Impact: High (enables adoption in new industries, differentiator vs. competitors)"

---

**Finding 3: Mobile App Feature Gaps Reduce On-the-Go Adoption**

**Severity: MEDIUM** — Not critical for all users, but high for field teams and managers on-the-move.

**Evidence**:
"Participants accessing the mobile app expected same functionality as desktop. One participant said: 'I wanted to update a task on my phone but couldn't add comments. Why would I use the mobile app if I can't do the same things?' Only 2 of 8 participants used mobile app regularly."

**Frequency**:
"Expected feature parity: 5 of 8 participants | Regular mobile users: 2 of 8"

**Recommendation**:
"Audit and expand mobile app: (1) List top 5 features from desktop (commenting, custom fields, attachments, status changes, task assignment). (2) Ensure all are available on mobile or add to roadmap. (3) Optimize for one-handed use (current design requires two hands). (4) Test expanded feature set with 5 mobile-first users."

**Effort/Impact Matrix**:
"Effort: 2-3 sprints (depends on feature selection) | Impact: Medium (expands adoption among mobile-first users)"

---

### Step 4: Create Affinity Diagram and Thematic Analysis (300-400 words)
Show patterns across findings by clustering them into themes.

**Affinity Diagram Structure**:

Organize findings into related themes:

**THEME 1: Discoverability**
- Finding: Gantt view is undiscovered
- Finding: Custom fields are buried in settings
- Finding: Advanced search/filter options are unknown
- Common Root Cause: Navigation is not intuitive; features exist but aren't surfaced

**THEME 2: Workflow Friction**
- Finding: Invite flow is too complex
- Finding: Task creation requires too many fields
- Finding: Role assignment is unclear
- Common Root Cause: Forms/flows have too many decision points; not optimized for quick action

**THEME 3: Feature Parity (Desktop vs. Mobile)**
- Finding: Mobile app lacks commenting
- Finding: Mobile app lacks custom field support
- Finding: Mobile app search is limited
- Common Root Cause: Mobile app developed as afterthought; not feature-parity with desktop

**THEME 4: Personalization**
- Finding: Users want custom fields for industry-specific workflows
- Finding: Users want customizable dashboard
- Finding: Users want flexible role definitions
- Common Root Cause: One-size-fits-all approach doesn't serve diverse user bases; need customization layer

**Root Cause Analysis**:
"The themes reveal a pattern: the product is feature-rich but prioritizes feature breadth over discoverability and ease-of-use. Users get lost navigating the interface. The mobile app is treated as secondary (feature parity missing). And the product assumes all users have the same workflows, leaving specialized industries underserved."

**Opportunity**:
"Focus next quarter on: (1) Simplifying core workflows (quick wins), (2) Improving discoverability of existing features (leveraging existing investment), (3) Feature parity mobile (enables on-the-go adoption), and (4) Custom fields (unblock specialized industries)."

### Step 5: Present Task Success Rates and Metrics (200-300 words)
Quantify findings with concrete metrics.

**Task Success Rates Table**:

| Task | Participants Who Succeeded | Success Rate | Avg Time (Seconds) | Errors | Notes |
|------|------|---------|---------|--------|-------|
| Create project | 8/8 | 100% | 45 | 0 | Straightforward; no issues |
| Invite team member | 2/8 | 25% | 180 | 6 avg | Most common blocking point; users confused by role options |
| Add task deadline | 7/8 | 87% | 25 | 1 | High success; minor confusion on date picker |
| Create Gantt view | 1/8* | 12% | N/A | N/A | *Only 1 found feature without prompting; 7 couldn't locate it |
| Assign custom fields | 0/8 | 0% | N/A | N/A | Feature not available in test version; marked as missing |
| Export report | 4/8 | 50% | 120 | 2 avg | Export dialog is hidden; users expected button in main menu |

**Key Metrics**:
- **Critical Path Success Rate**: 25% (invite team member is the blocker)
- **Average Time on Platform During Session**: 18 minutes (5 of 8 participants got frustrated and abandoned)
- **Overall Satisfaction (Post-Task)**: 3.4/5 average (frustration with navigation and complexity)
- **NPS (Net Promoter Score)**: +12 (promoters: 3, passives: 3, detractors: 2)

**Task Completion Barriers**:
"The 'invite team member' task is the critical barrier to adoption. Users must navigate role assignment (5 options with minimal explanation), which is the decision point where most get stuck. Simplifying this task from 5 steps to 2 and pre-selecting recommended role based on context could increase success rate to 75%+."

### Step 6: Build Priority Matrix (Impact vs. Effort) (200-300 words)
Help stakeholders understand which recommendations to tackle first.

**Priority Matrix Explanation**:

Create a 2x2 matrix:
- Y-axis: **Impact** (Low to High) — how much does this improve user experience and business outcomes?
- X-axis: **Effort** (Low to High) — how much work does this require?

**Quadrant 1: Quick Wins (High Impact, Low Effort)**
Tackle immediately:
- Redesign invite flow: reduce from 5 to 2 steps
- Improve Gantt view discoverability: add sidebar button
- Add inline help text for role options

**Quadrant 2: Strategic Projects (High Impact, High Effort)**
Plan for next quarter:
- Custom fields feature
- Mobile app feature parity
- Dashboard customization

**Quadrant 3: Low Priority (Low Impact, Low Effort)**
Do eventually:
- Cosmetic UI refinements
- Additional export formats

**Quadrant 4: Reconsider (Low Impact, High Effort)**
Deprioritize:
- Advanced features requested by <2% of users
- Performance optimization (users didn't mention performance)

**Matrix with Recommendations**:

| Recommendation | Impact | Effort | Priority | Timeline |
|---|---|---|---|---|
| Redesign invite flow | High | Low | 1 | Sprint 1 |
| Improve Gantt discoverability | Medium | Low | 2 | Sprint 1 |
| Inline help text for roles | Medium | Low | 2 | Sprint 1 |
| Custom fields feature | High | High | 3 | Q3 Planning |
| Mobile feature parity | High | High | 3 | Q3/Q4 |
| Dashboard customization | Medium | High | 4 | Future |

### Step 7: Provide Video Clip Timestamps (100-150 words)
Stakeholders often doubt findings until they see video evidence. Provide timestamp markers.

**Video Clip Repository**:
"Full session videos are available in [location]. Key moments referenced in this report:

- **Invite Flow Struggle (Time: 4:32-8:15, ~4 min)**: Participant attempts to invite team member, gets stuck on role selection, abandons task. Shows cognitive overload and unclear UX.
- **Gantt View Discovery (Time: 15:20-16:05, ~1 min)**: When shown Gantt view exists, participant reacts with interest: 'Oh, I didn't know that was there. I would totally use that.'
- **Mobile App Frustration (Time: 22:10-23:30, ~1 min)**: Participant tries to add comment on mobile app, realizes feature unavailable, expresses frustration: 'Why would I use this if I can't do the same things as desktop?'
- **Custom Fields Request (Time: 29:45-31:00, ~1.5 min)**: Design agency participant explains custom fields need: 'We track deliverables and approval status. Those aren't standard fields. Without custom fields, we'd need a different tool.'

Consider watching these clips in team meetings to build consensus around findings."

## Output Template

```
---
study_name: "[Study Title]"
study_date: "[YYYY-MM]"
research_method: "[Usability Testing/Interviews/etc.]"
number_of_participants: [N]
report_prepared_by: "[Name]"
report_date: "[YYYY-MM-DD]"
---

# UX Research Report: [Study Name]

## Executive Summary
[200-300 words: problem, key findings, impact, recommendations]

## Methodology
[200-300 words: research type, participants, study design, analysis approach, limitations]

---

## Key Findings (Finding Cards)

### Finding 1: [Title]
- Severity: [HIGH/MEDIUM/LOW]
- Evidence: [Quote or observation]
- Frequency: [X of Y participants / percentage]
- Recommendation: [Specific actionable fix]
- Effort/Impact: [Effort estimate | Impact assessment]

### Finding 2: [Title]
[Repeat structure]

[Add 3-8 additional findings]

---

## Thematic Analysis & Patterns

**Theme 1: [Cluster Name]**
[List related findings, identify root cause, indicate pattern]

**Theme 2: [Cluster Name]**
[List related findings, identify root cause, indicate pattern]

---

## Task Success Metrics
[Table showing success rates, time, errors for each task]

## Key Metrics Summary
- Critical path success rate: [%]
- Average session duration: [time]
- User satisfaction (post-task): [score/5]
- NPS: [score]

---

## Priority Matrix (Impact vs. Effort)

[Table or visual showing recommendations mapped to 2x2 matrix]

**Quick Wins (Start Immediately)**:
[List high-impact, low-effort items]

**Strategic Projects (Next Quarter)**:
[List high-impact, high-effort items]

---

## Video Evidence
[Timestamps and clips supporting key findings, with descriptions]

---

## Next Steps & Recommendations

### Immediate Actions (This Sprint)
1. [Action] — Expected outcome, timeline
2. [Action] — Expected outcome, timeline

### Short-Term (Next 2-4 Weeks)
1. [Action] — Expected outcome, timeline
2. [Action] — Expected outcome, timeline

### Future Planning (Next Quarter)
1. [Action] — Expected outcome, timeline
2. [Action] — Expected outcome, timeline

---

## Appendices
- A: Full Participant Demographics
- B: Study Protocol/Tasks
- C: Full Session Transcripts (or summary notes)
- D: Survey Data/Raw Metrics
- E: Video Links and Timestamps
```

## Quality Gates
1. **Evidence-Backed Findings**: Is every finding supported by specific observation or quote, not speculation?
2. **Severity Ratings**: Are ratings justified? Can stakeholders understand why finding is High vs. Medium?
3. **Actionable Recommendations**: Can designer or PM act on recommendation without further clarification?
4. **Data Honesty**: Are metrics presented accurately? Are limitations acknowledged?
5. **Clarity**: Can non-researcher (PM, executive) understand findings without expertise in research?
6. **Video Evidence**: Are timestamps and clips referenced for key findings?
7. **Prioritization**: Is priority matrix clear? Can stakeholders agree on what to tackle first?

## Common Mistakes

1. **Recommendations Without Evidence** — "Users want a dark mode" without data showing this request. Solution: Always tie recommendations to participant behavior or verbatim quotes.

2. **Buried Key Findings** — Critical findings scattered throughout report; easy to miss. Solution: Lead with findings that will surprise or change decisions.

3. **Severity Without Rationale** — Finding marked "HIGH" without explaining why. Stakeholders question severity. Solution: Explain: "Severity: HIGH because this blocks X% of users from core workflow."

4. **Missing Context** — Metrics presented without context. "25% task success" sounds bad until you know this is a new feature most users haven't seen. Solution: Always explain what success rate means.

5. **Too Many Findings** — Report lists 20 findings; prioritization becomes unclear. Solution: Focus on 5-8 most important findings. Mention others briefly or in appendix.

6. **No Video Evidence** — Report is all text; stakeholders doubt findings. Solution: Include 3-5 short video clips showing key moments.

## Anti-Patterns

1. **The Anecdote Report** — One participant said something interesting, so it becomes a finding. Anti-pattern: "One user suggested dark mode, so we should build it." Better: "3 of 8 users requested dark mode in low-light environments, suggesting a real need."

2. **The Blame Game** — Findings focus on what users did wrong ("Users don't read instructions") rather than design issues. Anti-pattern: "Users are confused by the interface" as finding without analyzing interface design. Better: "The interface lacks clear visual hierarchy; users miss primary actions."

3. **The Wish List** — Recommendations are feature requests, not addressing underlying problems. Anti-pattern: "Add dark mode, add collaboration, add AI." Better: Address root causes. "Users feel overwhelmed by complexity; prioritize simplification."

4. **The Generic Report** — Findings could apply to any product. No specificity. Anti-pattern: "Users want intuitive design" and "Users value performance." Better: "Users don't discover Gantt view; adding navigation button increased discoverability by 75% in follow-up test."

5. **The Missing Limitations** — Report doesn't acknowledge sample size or generalizability constraints. Stakeholders overweight findings. Better: "N=8 is small; findings are directional. Recommend validating with 20+ users before major investment."
