---
name: developer-growth-coach
description: "Analyze developer work patterns, code review feedback, skill gaps, and create personalized learning paths mapped to career goals"
category: personal
difficulty: intermediate
model_boost: "Weak models assume all developers need the same skills; miss understanding of actual project context, specific weaknesses, and realistic timelines"
---

# Developer Growth Coach: Skill Gap Analysis & Learning Path Design

## Purpose
Transform raw data (git history, code reviews, projects) into a personalized development roadmap. This skill teaches you to identify what a developer is actually working on (not what they claim), spot recurring patterns in mistakes, map current skills to market demands, and build realistic learning plans with specific resources and timelines. Use this to accelerate growth from 6-12 months, identify hidden strengths, and prevent skill irrelevance.

## When to Use / Do NOT use when
**USE WHEN:** Career inflection point (promotion, job change, burnout), feeling stuck, or mentoring someone you want to help grow.
**DO NOT:** Use as a replacement for actual mentorship or without discussing findings with the developer.

## Instructions

### Step 1: Analyze Git History (Past 12 Months)
**Gather Data**:
```bash
# Clone repository
git clone [repo-url]

# Analyze commit frequency and recency
git log --author="[name]" --all --oneline --since="12 months ago" | wc -l
# Result: Total commits in past year

# Languages worked on
git log --author="[name]" --all --pretty="" --name-only --since="12 months ago" | \
  grep -oE '\.[^.]*$' | sort | uniq -c | sort -rn
# Result: File extensions (language breakdown)

# Commit size pattern
git log --author="[name]" --all --shortstat --since="12 months ago" | \
  grep "changed" | awk '{lines+=$1} END {print lines " lines changed"}'
# Result: Total lines changed (indicator of scope)

# Files most frequently modified
git log --author="[name]" --all --pretty="" --name-only --since="12 months ago" | \
  sort | uniq -c | sort -rn | head -20
# Result: Top files (what consumes time)

# Commit timing (frequency pattern)
git log --author="[name]" --all --format="%h %ar" --since="12 months ago" | \
  awk '{print $NF}' | sort | uniq -c
# Result: Activity pattern (consistent vs bursty)
```

**What This Tells You**:
- Total commits: Productivity, engagement level
- Languages: Current tech stack, breadth
- Lines changed: Scope of responsibility
- Modified files: Domain expertise areas
- Commit timing: Work style (steady vs sprint)

**Record**:
```
Commits/Month: [Average, trend up/down]
Primary Languages: [Python 40%, TypeScript 35%, etc]
Domains Touched: [Backend, Infra, Frontend, etc]
Average Commit Size: [X lines, Y files]
Work Style: [Steady daily or weekend bursts]
```

### Step 2: Analyze Commit Messages for Patterns
**Review past 50 commits**:
```
Pattern Categories:

Feature Work: "Add user authentication", "Implement caching"
→ Shows: Product development, understanding requirements

Bug Fixes: "Fix memory leak", "Correct validation logic"
→ Shows: Debugging, pattern recognition, attention to detail

Refactoring: "Simplify error handling", "Extract duplicated logic"
→ Shows: Code quality awareness, architectural thinking

Documentation: "Add API docs", "Clarify setup instructions"
→ Shows: Communication skills, onboarding thinking

DevOps/Config: "Update Docker image", "Configure CI/CD"
→ Shows: Infrastructure comfort, systems thinking

Dependencies: "Upgrade React", "Add new package"
→ Shows: Maintenance mindset, safety practices
```

**Quantify**:
```
Feature development: X%
Bug fixes: X%
Refactoring: X%
Documentation: X%
DevOps/Tooling: X%
Dependency management: X%

Insight: If 80% features/bugs and 5% docs, developer focused on shipping (good) but weak on knowledge transfer (growth area)
```

### Step 3: Analyze Code Review Feedback (Past 6 Months)
**Collect feedback patterns**:

**Technical Feedback**:
- "Add error handling for edge case" → Missing defensive programming
- "Consider using [pattern] here" → Pattern unfamiliarity
- "Performance concern: O(n²) loop" → Algorithm analysis weakness
- "This could use caching" → Optimization awareness gap
- "Security issue: SQL injection risk" → Security blindspot

**Architecture Feedback**:
- "This violates single responsibility" → Design principles knowledge
- "Abstraction is too generic" → Abstraction judgment
- "Tight coupling between modules" → System design weakness

**Communication Feedback**:
- "Unclear variable naming" → Readability/communication
- "Missing comment on complex logic" → Documentation awareness
- "PR description doesn't explain why" → Communication of intent

**Process Feedback**:
- "Too many changes in one PR" → Scope management
- "Merge before tests pass" → Quality standards
- "Committed secrets by accident" → Tooling/workflow knowledge

**Quantify**:
```
Recurring Feedback Topics (Ranked):
1. [Topic]: Appeared in X reviews (X% of feedback)
2. [Topic]: Appeared in Y reviews (Y% of feedback)
3. [Topic]: Appeared in Z reviews (Z% of feedback)

Trend: Getting better, staying same, or getting worse?
```

### Step 4: Map Current Skills Using Proficiency Levels
**Skill Framework (Novice → Expert)**:

```
Level 1 - Novice: "I've read about this"
- Can implement with documentation
- Needs help debugging
- Can't teach others
- Takes 2x longer than expert

Level 2 - Competent: "I've done this in production"
- Can implement without docs
- Can debug most issues
- Can explain to junior dev
- Time matches senior dev (1x)

Level 3 - Proficient: "I know the tradeoffs"
- Can implement quickly and optimize
- Can anticipate edge cases
- Can mentor, design systems with it
- Time advantage: 0.5x senior
- Can identify when NOT to use

Level 4 - Expert: "I've solved novel problems with this"
- Contributes to standards/libraries
- Can teach others unconventional uses
- Predicts problems before they occur
- Time advantage: 0.25x senior
```

**Assessment Process**:

For each technology in their commits:
```
Technology: Python
Evidence from recent work:
- Commits touching Python files: 15
- Complexity: Web scraping, data pipelines, API servers
- Feedback: 1 review noted "consider generator here" (efficiency awareness)
- Self-assessment: "Pretty comfortable"

Assessment:
  Syntax/Basics: Level 4 (Expert - shipping production code)
  Standard library: Level 3 (Proficient - using without docs)
  Advanced patterns (generators, decorators): Level 2 (Competent - knows they exist)
  Performance optimization: Level 2 (Competent - open to learning)
  Testing frameworks: Level 2 (Competent - basic coverage, not advanced)

Overall Python Level: Level 3 (Proficient)
Growth Edge: Testing, performance optimization
```

**Create Skills Matrix**:
```
Technology    | Proficiency | Confidence | Frequency | Growth Area
──────────────┼─────────────┼────────────┼───────────┼──────────────
Python        | Proficient  | High       | Daily     | Testing
TypeScript    | Competent   | Medium     | 2x/week   | Advanced types
Kubernetes    | Novice      | Low        | Rare      | Full learning
PostgreSQL    | Competent   | Medium     | Daily     | Query optimization
Docker        | Competent   | High       | 2x/week   | Networking
```

### Step 5: Identify Recurring Skill Gaps
**Pattern Analysis from Code Review + Commits**:

**Top 3 Recurring Gaps**:
```
Gap 1: Testing
Evidence:
- Code review: "Missing test for edge case" (3 times)
- Code review: "Test coverage dropped 5%" (2 times)
- Commit messages: Zero commits mentioning tests
- Git history: No test files created in past 6 months
Impact: Bug escape rate, confidence in refactoring, maintainability
Market demand: 9/10 (every job description mentions)
Effort to close: 3-4 weeks intensive study

Gap 2: System design
Evidence:
- Architecture feedback: "Tight coupling between modules" (2 times)
- Commits show feature work but no refactoring/abstraction
- No microservices/scaling patterns in work history
- Self-assessment: "I build features, not systems"
Impact: Can't lead design discussions, limited to feature work
Market demand: 8/10 (senior roles require)
Effort to close: 8-12 weeks applied learning

Gap 3: Observability
Evidence:
- Commits never mention logging/monitoring
- Code reviews silent on this (maybe not required yet)
- Production incidents suggest debugging was slow
Impact: Can't independently troubleshoot production issues
Market demand: 7/10 (growing, not universal)
Effort to close: 2-3 weeks applied learning
```

### Step 6: Identify Hidden Strengths
**Mining Git History for Underrated Skills**:

```
Signal: Quick bug fixes with complex root causes
- Developer found and fixed memory leak in 2 commits
- Commit messages show reasoning
- Implication: Strong debugging ability (often overlooked on resume)

Signal: Consistent refactoring across codebases
- Regular commits titled "Simplify X", "Extract Y"
- Low churn rate (clean changes, not thrashing)
- Implication: Code quality mindset, architectural thinking

Signal: Cross-team contributions
- Commits in 5+ different services/repos
- Shows: Systems understanding, communication, context switching

Signal: Dependency management diligence
- Regular updates, security patches applied
- Implication: Security mindedness, responsibility

Hidden Strength Opportunities:
1. [Strength] - Could deepen into [adjacent skill]
   - Example: Debugging → Observability, Root cause analysis
2. [Strength] - Could market better in interviews/resume
   - Example: Code quality → Could lead architecture reviews
```

### Step 7: Map Career Goals to Skill Requirements
**Example Goal: Move from Mid-level Engineer to Senior Engineer**

**Career Level Requirements** (industry standards):
```
Mid-level:
- Proficient in 1-2 languages
- Can own features end-to-end
- Competent at debugging
- Follows established patterns

Senior:
- Expert in 1-2 languages, competent in several
- Can own services (multiple features)
- Expert at root cause analysis
- Can design systems, mentor others
- Understands tradeoffs (performance vs simplicity)
- Contributes to technical strategy
```

**Gap Analysis for Specific Goal**:
```
Goal: Staff Engineer (5 years ahead)

Current Skills Assessment:
- Python: Proficient ✓
- System Design: Novice ✗
- Mentoring: Novice ✗
- Technical Writing: Competent ✓
- Observability: Novice ✗

Skills to Develop (Priority):
1. System Design (12 weeks) - Required for any senior role
2. Observability (4 weeks) - Needed for staff-level production ownership
3. Technical Leadership (16 weeks) - Mentoring, code reviews at scale
4. Architecture Patterns (8 weeks) - Distributed systems, scaling
```

### Step 8: Curate Learning Resources (Specific, Not Generic)
**Resource Selection Process**:

**For Testing Gap** (High priority, 3-4 weeks):
```
Week 1: Foundations
- Course: "Testing best practices" (Udemy - 8 hrs)
- Article: pytest documentation (2 hrs)
- Applied: Add 10 tests to current project (5 hrs)
Total: 15 hours

Week 2: Advanced
- Course: "Test-driven development" (Frontend Masters - 10 hrs)
- Article: "Testing pyramid pattern" (read 2 articles - 1 hr)
- Applied: Refactor 3 existing features with tests (8 hrs)
Total: 19 hours

Week 3-4: Integration
- Contribute: Write test infrastructure improvements (10 hrs)
- Read: 2 open-source projects' test strategies (4 hrs)
- Applied: Achieve 80% test coverage in your service (12 hrs)
Total: 26 hours

Total commitment: ~60 hours over 4 weeks
Realistic pace: 15 hrs/week (2 hrs/day)
```

**Resource Evaluation Criteria**:
- Hands-on (video/tutorial, not just reading)
- Recent (updated within 12 months)
- Directly applicable (not theoretical fluff)
- Project-based (build something, don't just watch)
- Reviews/reputation (verified by community)

**Resource Examples**:
```
Testing:
- Course: "The Complete Hands-On Introduction to Apache Airflow on Udemy"
- Repo: pytest documentation + real-world examples
- Applied: "Add comprehensive tests to your current service"

System Design:
- Course: "Grokking the System Design Interview"
- Book: "Designing Data-Intensive Applications"
- Project: "Design a URL shortener, then review actual implementations"

Observability:
- Course: "Complete Observability for Developers" (O'Reilly)
- Hands-on: Set up Prometheus/Grafana locally (1 project)
- Applied: Add logging/metrics to current service
```

### Step 9: Create Study Plan with Timeline
**Template**:
```
Developer Growth Plan
=====================
Name: [Developer]
Current Level: Mid-level engineer
Goal: Senior engineer within 12 months
Created: [Date]

Primary Skill Goals:
1. System design: Novice → Competent (12 weeks)
2. Testing: Competent → Proficient (4 weeks)
3. Observability: Novice → Competent (4 weeks)

Secondary Goals (if time):
- Kubernetes: Novice → Competent (6 weeks)

Month 1 (Weeks 1-4): Testing Intensive
- Time commitment: 15 hrs/week
- Resources: Testing course + applied project work
- Milestone: Achieve 80% test coverage on current service
- Accountability: Weekly code review, 1 pair programming session

Month 2-3 (Weeks 5-12): System Design Foundation
- Time commitment: 12 hrs/week
- Resources: Course + design document reviews
- Milestone: Design 2 services from scratch (review with mentor)
- Accountability: Bi-weekly architecture reviews with tech lead

Month 4 (Weeks 13-16): Observability
- Time commitment: 10 hrs/week
- Resources: Course + apply to 1-2 services
- Milestone: Implement metrics/logging/tracing in current service
- Accountability: On-call rotation, debug incidents

Months 5-12: Ongoing
- Maintain testing discipline (added to code standards)
- Lead 1-2 architectural designs (practice system design)
- Mentor 1 junior engineer (communication, teaching)
- Contribute to technical strategy (staff-level thinking)

Success Metrics:
- System design: Can design service without hand-holding
- Testing: All PRs reviewed for test quality
- Observability: Can debug production issues independently
- Leadership: Mentee completes 2+ growth goals with your help
```

### Step 10: Track Progress Over Time
**Tracking Dashboard**:

```
Metric                          | Jan | Feb | Mar | Apr | Target
────────────────────────────────┼─────┼─────┼─────┼─────┼────────
Test Coverage (%)               | 32  | 45  | 62  | 78  | 80+
Code Review: Testing feedback   | 3   | 2   | 1   | 0   | 0
Commits mentioning tests        | 0   | 2   | 5   | 8   | Regular

System design: Design docs      | 0   | 0   | 1   | 2   | 2+
Code review: Architecture notes | 0   | 1   | 3   | 4   | Regular
Technical discussions led       | 0   | 0   | 1   | 2   | 1/month

Observability metrics added     | 0   | 2   | 5   | 12  | 1/week
Production incidents debugged   | 0   | 1   | 3   | 5   | Regular
Logging quality feedback        | 0   | 0   | 0   | 0   | Regular

Mentoring: Interactions         | -   | 5   | 8   | 12  | 2/week
Junior growth goals completed   | -   | 0   | 1   | 2   | 1+
```

## Output Template

```
Developer Growth Analysis
==========================
Developer: [Name]
Analysis Date: [Date]
Review Period: [Past 12 months]

Git Activity Summary:
- Commits: [X per month average]
- Primary languages: [List with percentages]
- Primary domains: [List with percentages]
- Work style: [Steady/bursty/seasonal]

Skill Assessment:
[Skills matrix with proficiency levels]

Top 3 Growth Gaps:
1. [Gap]: Evidence → Impact → Effort to close
2. [Gap]: Evidence → Impact → Effort to close
3. [Gap]: Evidence → Impact → Effort to close

Hidden Strengths Identified:
1. [Strength]: Evidence → Market value
2. [Strength]: Evidence → Market value

Career Goal: [Specific goal]
Timeline: [X months]
Required skills: [List with proficiency targets]

Recommended Learning Plan:
[Month-by-month breakdown with resources and milestones]

Success Metrics:
[5-7 measurable indicators]

Next Review Date: [3 months from now]
```

## Quality Gates

1. **Git data spans 12+ months**: 3-month data is not representative
2. **5+ code reviews analyzed**: 1-2 reviews miss patterns
3. **Skill assessment discussed with developer**: Self-perception vs actual reality matters
4. **Career goal is specific**: "Get better" is vague; "senior engineer in 12 months" is clear
5. **Learning plan includes applied projects**: Reading courses without application = forgotten in 2 weeks
6. **Timeline is realistic**: Expert level takes 10,000 hours; plan should reflect this
7. **Accountability mechanism defined**: Without check-ins, plan becomes wall decoration

## Examples

### Good Growth Plan
```
Developer: Maya Chen
Current: Mid-level Python engineer, 3 years experience
Goal: Senior engineer at fintech company within 12 months

Git History Analysis:
- 60 commits/month average (consistent pace)
- 95% Python, 5% DevOps
- Commits show feature development (70%), debugging (20%), refactoring (10%)
- Code reviews mention: "Consider using async" (4x), "Missing error handling" (3x)

Skill Assessment:
- Python: Proficient (solid production code)
- Async/Concurrency: Competent (basic knowledge, can improve)
- System Design: Novice (feature-focused, not architecture)
- Testing: Competent (basic coverage, not comprehensive)

Top 3 Growth Gaps:
1. System Design (Evidence: No design documents, architecture reviews below peer level)
2. Async Python (Evidence: Repeated reviews on async patterns, performance concerns)
3. Observability (Evidence: Production debugging took 2+ hours, no metrics/logging in code)

Hidden Strengths:
- Debugging prowess (found 3 subtle production bugs others missed)
- Mentoring potential (clear code, good at explaining decisions)

Learning Plan:
Month 1: Async Python deep-dive
- Course: Miguel Grinberg's async Python course
- Applied: Convert existing service to async, reduce latency 20%
- Check-in: Weekly code review, pair on 2 async refactors

Months 2-3: System design foundation
- Study: Designing Data-Intensive Applications
- Applied: Design 2 services from scratch, review with tech lead
- Check-in: Bi-weekly design reviews

Month 4: Observability
- Course + hands-on: Set up Prometheus, Jaeger
- Applied: Add comprehensive observability to main service
- Check-in: Lead production debugging, implement on-call process

Months 5-12: Advanced topics
- Distributed systems patterns, scaling strategies, mentoring

Success Indicators:
- Async metrics: All new code uses async patterns (100% of PRs)
- Design: Lead 2+ architectural discussions, no guidance needed
- Observability: Resolve production issues in < 15 minutes
```

### Bad Growth Plan
```
"Maya should get better at system design by reading books and taking online courses. Should improve testing practices. Maybe learn some new tools. Check back in 6 months."

Problems:
- Too vague ("get better" vs specific proficiency level)
- No timeline or commitment (6 months is too long between check-ins)
- No applied component (reading without building = forgetfulness)
- No accountability (no weekly milestones or check-ins)
- No measurement of success (how do we know she's proficient?)
```

## Common Mistakes

1. **Ignoring git data, believing self-assessment only**: Developer says "I'm great at testing" but commits show zero test files. Use objective evidence.

2. **Assuming all developers need same growth path**: Some need breadth (learn new languages), others need depth (master one domain). Let data guide.

3. **Learning resources disconnected from job reality**: Taking advanced course when developer can't apply it for 6 months wastes momentum. Plan learning around current projects.

4. **Too many simultaneous goals**: "Learn testing, system design, Kubernetes, DevOps" in 3 months = failure. Prioritize ruthlessly.

5. **No accountability mechanism**: Plan is created, developer nods, nothing changes. Weekly check-ins + milestone tracking essential.

6. **Ignoring hidden strengths**: Focusing only on gaps misses opportunity to amplify existing strengths (teaching others, architecture thinking).

## Anti-Patterns

1. **Growth coaching as punishment**: "You're weak at testing, fix it." Better framing: "You're good at features; let's add testing to unlock senior promotions."

2. **One-size-fits-all curriculum**: Using same learning path for all developers. Each person's context (domain, career goal, learning style) is different.

3. **Theoretical learning without application**: Reading book on system design without designing a system = wasted effort. Always pair with project.

4. **Assuming 10,000 hours = instant expertise**: Steep learning curve early (0-6 months is fastest growth), then plateaus. Plan timelines realistically.

5. **Ignoring mentorship component**: Self-study is 40% effective; mentored learning is 80%. Always include mentor/pair programming in plan.

6. **Treating skill development as separate from day-job**: Best growth happens through current project work + intentional reflection, not by stopping work to "take courses."
