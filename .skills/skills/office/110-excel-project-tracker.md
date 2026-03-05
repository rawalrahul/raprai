---
name: excel-project-tracker
description: "Build project management in Excel: task lists with WBS, Gantt charts, resource allocation, status tracking (RAG), milestone tracking. Use for project planning and status."
category: office
difficulty: intermediate
model_boost: "Fixes weak project trackers: missing dependencies, no Gantt visualization, outdated status, unclear who does what."
---

# Excel Project Tracker

## Purpose
Create project plans and tracking dashboards in Excel that show tasks, timelines, dependencies, resource allocation, and status. This skill builds WBS (Work Breakdown Structure) numbering, Gantt charts using conditional formatting, status indicators (RAG—Red/Amber/Green), milestone tracking, and capacity planning views. A strong project tracker answers "Are we on schedule? Who's over-capacity? What's at risk?"

## When to Use
- "Create a project plan" with tasks and timeline
- "Build a Gantt chart" to visualize schedule
- "Track project status" week-to-week
- "Manage team capacity" and resource allocation
- **Do NOT use when**: Managing thousands of tasks (use dedicated PM software); or tracking complex dependencies (use MS Project)

## Instructions

### Step 1: Work Breakdown Structure (WBS) and Task List
Hierarchical task numbering and clear descriptions.

**WBS Numbering Scheme**
```
1              (Phase)
1.1            (Workstream within phase)
1.1.1          (Task within workstream)
1.1.1.a        (Subtask within task)
```

**Columns for Task List**
```
Column A: WBS #         | 1, 1.1, 1.1.1, 1.1.2, 1.2, 2, 2.1, etc.
Column B: Task Name     | {{Description of task}}
Column C: Owner         | {{Person responsible}}
Column D: Duration      | {{# of days}}
Column E: % Complete    | {{0%—100%}}
Column F: Status        | {{Green | Amber | Red}}
Column G: Start Date    | {{Date}}
Column H: End Date      | {{Calculated: Start Date + Duration}}
Column I: Predecessor   | {{Which task this depends on (WBS #)}}
Column J: Notes         | {{Blockers, risks, dependencies}}
```

**Example (Consulting Project)**
```
WBS  | Task Name                | Owner   | Days | Status | Start   | End     | Pred  | Notes
────────────────────────────────────────────────────────────────────────────────────────────
1    | Discovery Phase          |         | 10   | Green  | Jan 1   | Jan 10  |       |
1.1  | Intake meetings          | Jane    | 3    | Green  | Jan 1   | Jan 3   |       |
1.2  | Architecture review      | Bob     | 4    | Green  | Jan 4   | Jan 7   | 1.1   | Depends on intake
1.3  | Cost analysis            | Sarah   | 3    | Amber  | Jan 8   | Jan 10  | 1.2   | At risk—data delay
2    | Design Phase             |         | 12   | Amber  | Jan 11  | Jan 22  | 1     |
2.1  | Framework design         | Jane    | 6    | Amber  | Jan 11  | Jan 16  | 1.3   | Blocked on Sarah's data
2.2  | Governance model         | Bob     | 4    | Yellow | Jan 17  | Jan 20  | 2.1   | Can start soon
2.3  | Documentation           | Sarah   | 2    | Red    | Jan 21  | Jan 22  | 2.2   | Will be late—resource constraint
```

**Formatting Tips**
- **Indentation**: Subtasks indented 1–2 levels for visual hierarchy
- **Alternating row colors**: Light blue (parent tasks) and white (subtasks) for readability
- **Task name clarity**: "Architecture Review" not "Task 1" (readable at a glance)

### Step 2: Duration and Date Calculations
Formulas for automatic timeline calculation.

**Duration Column**
```
Column D: Duration (in days)
- Enter manually for each task (e.g., 5 days for intake)
- Duration = estimated effort; shouldn't include waiting time
```

**Start and End Dates (with Dependency Logic)**
```
Column G (Start Date): Either:
  (a) Manual for root tasks (Phase 1 starts Jan 1)
  (b) Formula for dependent tasks: =IF(Predecessor="", ManualDate, VLOOKUP(Predecessor, table, end_date_col))
      (Finds predecessor's end date and uses that as start date)

Column H (End Date): =G + D (Start Date + Duration days)
```

**Example Formula** (for a task dependent on predecessor 1.1)
```
G15: =IF(I15="1.1", VLOOKUP(I15, $A$2:$H$20, 8), G14+1)
     (If predecessor is 1.1, find 1.1's end date; else use previous task's end date + 1)

H15: =G15 + D15 (End Date = Start + Duration)
```

**Milestone Dates**
Separate milestone rows (or column) to track key dates:
```
WBS | Task        | Type      | Target Date
──────────────────────────────────────────────
1.5 | Kickoff     | Milestone | Jan 1
1.8 | Design Approval | Milestone | Jan 23
2.5 | Delivery    | Milestone | Feb 15
```

### Step 3: Gantt Chart Using Conditional Formatting
Visualize timeline without complex chart objects.

**Build the Gantt**
1. Create a date row (columns starting from column L): Jan 1, Jan 2, Jan 3, ... Dec 31
2. For each task, create a cell range (one cell per day) that fills if the task is "active" on that date
3. Use conditional formatting to color cells (blue = task active, blank = not active)

**Formula for Gantt Cell** (task row × date column)
```
Example: Task 1.1 (Start Jan 1, Duration 3 days, Ends Jan 3)

For each date column:
  =IF(AND($G7 <= L$1, L$1 <= $H7), "█", "")
     (If date is between start and end, show block; else blank)

Alternatively: =IF(AND($G7 <= L$1, L$1 <= $H7), CHAR(9608), "")
               (CHAR(9608) = Unicode block character █)
```

**Conditional Formatting**
1. Select the date range (entire Gantt area, columns L–... for Jan 1–Dec 31)
2. Home → Conditional Formatting → New Rule
3. Formula: =L$1 >= $G7 AND L$1 <= $H7
4. Format: Fill color (blue), font size 9 (for compactness)

**Result**
```
WBS  | Task             | Owner | Days | Start  | End    | Jan 1 | Jan 2 | Jan 3 | Jan 4 | Jan 5
─────────────────────────────────────────────────────────────────────────────────────────────────
1.1  | Intake meetings  | Jane  | 3    | Jan 1  | Jan 3  |  ███  |  ███  |  ███  |       |
1.2  | Architecture    | Bob   | 4    | Jan 4  | Jan 7  |       |       |       |  ███  |  ███
1.3  | Cost analysis   | Sarah | 3    | Jan 8  | Jan 10 |       |       |       |       |
     |                 |       |      |        |        | [Gantt bars show task timeline visually] |
```

**Compact Gantt** (show fewer columns to fit on page)
- Instead of daily columns, use weekly columns (Week 1, Week 2, etc.)
- Formula: =IF(AND($G7 <= L$1 + 6, L$1 <= $H7), "█", "") [L$1 is week start]

### Step 4: Status Tracking (RAG—Red, Amber, Green)
Track health of each task.

**Status Column Definition**
```
Column F: Status (dropdown)
- Green: On track (% complete matches % of time elapsed)
- Amber: At risk (slightly behind or at risk of delay)
- Red: Off track (significantly behind or blocked)
```

**Status Calculation Formula**
```
Days Elapsed: =TODAY() - Start Date
Days Total: = End Date - Start Date
Expected % Complete: = Days Elapsed / Days Total (what % should be done by today)
Actual % Complete: = User enters (or calculated from subtask completion)

Status: =IF(Actual >= Expected * 0.95, "Green", IF(Actual >= Expected * 0.85, "Amber", "Red"))
        (If actual is ≥95% of expected = green; 85–95% = amber; <85% = red)
```

**Visual Encoding** (Conditional Formatting)
```
Column F (Status):
  - Green cells: Fill color green, text white
  - Amber cells: Fill color orange, text white
  - Red cells: Fill color red, text white

This makes status visible at a glance
```

**Example**
```
WBS | Task    | Start   | End     | % Complete | Days Elapsed | % Expected | Status
──────────────────────────────────────────────────────────────────────────────────
1.1 | Intake  | Jan 1   | Jan 3   | 100%       | 3 days       | 100%       | Green ✓
1.2 | Arch    | Jan 4   | Jan 7   | 60%        | 2 days       | 67%        | Amber ⚠
1.3 | Cost    | Jan 8   | Jan 10  | 30%        | 3 days       | 100%       | Red ✗
```

### Step 5: Resource Allocation Matrix
Who's doing what; are people over-capacity?

**Setup**
- Rows: Team members (Jane, Bob, Sarah, etc.)
- Columns: Project tasks (1.1, 1.2, 1.3, etc.)
- Cells: Hours per week allocated to that task

**Example**
```
Resource        | Task 1.1 | Task 1.2 | Task 1.3 | Task 2.1 | Task 2.2 | Total / Capacity
                |  Intake  | Arch     | Cost     | Design   | Govnce   |
────────────────────────────────────────────────────────────────────────────────────────
Jane            | 8 hrs    |          |          | 15 hrs   | 10 hrs   | 33 / 40 hrs (82%)
Bob             |          | 12 hrs   |          | 8 hrs    | 8 hrs    | 28 / 40 hrs (70%)
Sarah           |          |          | 10 hrs   |          |          | 10 / 40 hrs (25%)
────────────────────────────────────────────────────────────────────────────────────────
Total:          | 8 hrs    | 12 hrs   | 10 hrs   | 23 hrs   | 18 hrs   |

Capacity View:
Jane: 33/40 (82%) — GOOD
Bob:  28/40 (70%) — GOOD
Sarah: 10/40 (25%) — AVAILABLE (could take more work)
```

**Conditional Formatting**
- Green: <80% capacity (has room)
- Amber: 80–100% capacity (at limit)
- Red: >100% capacity (over-capacity; will miss deadlines)

**Formula for Total**
```
Total = SUM(Task1 hours + Task2 hours + ...)
Capacity % = Total / 40 hours per week
Color code: IF(Capacity % > 1, "Red", IF(Capacity % > 0.8, "Amber", "Green"))
```

### Step 6: Milestone Tracking
Key dates and deliverables that trigger phase gates.

**Milestone Table**
```
Milestone # | Milestone Name        | Type     | Target Date | Actual Date | Status | Owner
──────────────────────────────────────────────────────────────────────────────────────
M1          | Kickoff               | Event    | Jan 1       | Jan 1       | ✓ On   | PM
M2          | Discovery complete    | Gate     | Jan 10      | Jan 12      | ⚠ Late | Jane
M3          | Design approval       | Gate     | Jan 23      | TBD         | ? At risk | Bob
M4          | Final delivery        | Gate     | Feb 15      | TBD         | ? TBD  | PM
```

**Status Indicators**
```
✓ = Completed on/before target
⚠ = Completed but late
✗ = Blocked/Not started
? = In progress, on track; awaiting completion
```

**Formula for Status**
```
IF(Actual Date = "", "?", IF(Actual Date <= Target Date, "✓", "⚠"))
(If no actual date = in progress; if actual ≤ target = on time; else late)
```

**Milestone-to-Task Link**
Which tasks must be done for the milestone?
```
Milestone M2 (Discovery complete) = Tasks 1.1, 1.2, 1.3 must be 100%
Status of M2 = MIN(% complete of 1.1, 1.2, 1.3)
(Milestone is complete only when all prerequisite tasks are done)
```

### Step 7: Dependency Tracking
Task A must finish before Task B starts.

**Predecessor Column (Column I)**
```
Task 1.1: Predecessor = "" (no predecessor; starts first)
Task 1.2: Predecessor = "1.1" (can't start until 1.1 finishes)
Task 1.3: Predecessor = "1.2" (can't start until 1.2 finishes)
Task 2.1: Predecessor = "1.3" (Phase 2 can't start until Phase 1 is done)
```

**Critical Path** (longest sequence of dependent tasks)
The critical path = the task sequence that determines overall project end date. If any critical task is delayed, the whole project is delayed.

Critical path example: 1.1 (3 days) → 1.2 (4 days) → 1.3 (3 days) → 2.1 (6 days) = 16 days total

**Highlight Critical Path**
In Gantt chart, shade the critical path tasks in bold color (orange or red).
Formula: Mark task as critical if it's on the longest dependency chain.

**Automated Alert**
```
If Task A's % Complete < (Today - Start) / Duration, mark as Red
This flags tasks that are falling behind their critical path
```

### Step 8: Burndown Chart (Progress Tracking)
Show cumulative work completed over time.

**Setup**
- X-axis: Week or date
- Y-axis: Hours remaining (total project hours at top, trending to 0)
- Ideal line: Straight diagonal from start hours to 0
- Actual line: Bumpy line showing real progress

**Data**
```
Date        | Ideal Hours Remaining | Actual Hours Remaining | On Track?
──────────────────────────────────────────────────────────────────────
Jan 1       | 800 hours            | 800 hours              | ✓
Jan 8       | 700 hours (on track)  | 750 hours              | ⚠ Slightly behind
Jan 15      | 600 hours (on track)  | 720 hours              | ⚠ Falling further behind
Jan 22      | 500 hours (on track)  | 600 hours              | ✗ At risk
```

**Burndown Chart (Visual)**
```
Hours Remaining
800 ┌──────────────┐
    │ IDEAL (diagonal line)  │
700 │    ╱         │
    │   ╱  ACTUAL  │
600 │  ╱╱╱╱╱      │ (jagged, trending above ideal = behind)
500 │╱╱╱  ╲╱      │
400 │      ╲      │
    │       ╲     │
0   └────────╱────┘
    Jan 1   Jan 22

If actual line is above ideal = behind schedule
If actual line is below ideal = ahead of schedule
```

**Alert Logic**
```
IF(Actual Hours > Ideal Hours, "RED: Behind schedule", "GREEN: On track")
Trigger escalation if behind for 2+ weeks
```

### Step 9: Summary Dashboard Tab
Executive view of project health.

**Dashboard Elements**

**Overall Status**
```
Project: {{Project Name}}
Owner: {{Project Manager}}
Start Date: {{Date}}
Target End Date: {{Date}}
Overall Status: 🟢 GREEN / 🟡 AMBER / 🔴 RED

Progress: 45% complete (18 of 40 tasks done)
Timeline: On schedule (47 days elapsed, 45% of 104 days)
Budget: $180K / $200K (90%, on budget)
```

**Phase Summary Table**
```
Phase | Status | % Complete | Milestones | On Schedule?
──────────────────────────────────────────────────────
Phase 1: Discovery | 🟢 GREEN | 100% | M1, M2 ✓ | Yes
Phase 2: Design    | 🟡 AMBER |  60% | M3 ⚠ | At risk
Phase 3: Build     | ⚪ NOT STARTED | 0% | M4 ? | TBD
```

**Risk & Issues Register**
```
ID  | Risk/Issue       | Owner | Impact | Mitigation
──────────────────────────────────────────────────────
R1  | Data delay       | Sarah | Medium | Request expedited data by Jan 12
R2  | Resource shortage| Jane  | High   | Hire contractor for 2 weeks
I1  | Scope creep      | PM    | Medium | Enforce change order process
```

**Bottleneck Analysis**
```
Who's over-capacity?
Jane: 33/40 hrs (82%) → GOOD
Bob: 28/40 hrs (70%) → GOOD
Sarah: 10/40 hrs (25%) → AVAILABLE

What tasks are at risk?
Task 1.3 (Sarah): Red status, 30% complete, 100% due
Task 2.3 (TBD): No owner assigned; BLOCKED

What's blocking us?
Missing data for cost analysis (blocks design phase)
Approval delay from client (waiting since Jan 15)
```

## Output Template
```
# {{PROJECT NAME}} - Project Tracker

## Project Overview
- **Project Manager**: {{Name}}
- **Start Date**: {{Date}}
- **Target Completion**: {{Date}}
- **Total Duration**: {{X weeks}}
- **Overall Status**: 🟢 GREEN / 🟡 AMBER / 🔴 RED

## Task Summary
- Tasks Total: {{N}}
- Tasks Complete: {{N}} ({{%}})
- Tasks At Risk: {{N}}
- Critical Path Duration: {{X days}}

## Work Breakdown Structure (WBS)
[Task list table: WBS # | Task | Owner | Duration | Status | Start | End | Pred]

## Gantt Chart
[Visual timeline showing task bars across calendar weeks]

## Resource Allocation
[Matrix: Team members × tasks, showing hours/capacity]

## Milestone Status
[Table: Milestone | Target Date | Actual Date | Status | Owner]

## Risk Register
[Open risks/issues and mitigation plans]

## Dashboard
[Summary metrics: % complete, on/off schedule, over/under capacity, critical blockers]
```

## Quality Gates
- [ ] WBS numbering is hierarchical and consistent (1, 1.1, 1.1.1, etc.)
- [ ] All tasks have an owner assigned (no unowned work)
- [ ] Dependencies are documented (predecessors column filled)
- [ ] Gantt chart shows task timelines visually (bars or blocks visible)
- [ ] Status indicators (RAG) are updated weekly
- [ ] Resource allocation doesn't exceed capacity (no >100% allocation)
- [ ] Milestones are tracked and flagged if at risk
- [ ] Critical path is identified (longest dependency chain)
- [ ] Actual vs. planned dates are tracked for completed tasks

## Examples

### Good Output (excerpt)
```
[Gantt Chart Section]
Jan ────────────────── Feb ─────────────── Mar ────
WBS | Task         | Owner | Status |█████ █████ █
1.1 | Intake       | Jane  | Green  |██
1.2 | Architecture | Bob   | Amber  |      ███
1.3 | Cost         | Sarah | Red    |           ██
2.1 | Design       | Jane  | Yellow |           ████
2.2 | Governance   | Bob   | TBD    |                ████

[Resource Allocation]
Jane:  32/40 hrs (80%) — At capacity
Bob:   28/40 hrs (70%) — Room for more
Sarah: 10/40 hrs (25%) — Available (but task 1.3 is red/late)

[Milestone Status]
M1: Kickoff — Jan 1 — ✓ On time
M2: Discovery — Jan 10 — ⚠ Late (actual Jan 12)
M3: Design Approval — Jan 23 — ? At risk (60% complete)
M4: Delivery — Feb 15 — ? TBD

[Risk Register]
R1: Data Delay — Sarah — Blocks design (mitigation: expedite request)
I1: Scope Creep — PM — Enforce change order process
```

### Bad Output (what to avoid)
```
Task list with no WBS numbering (just "Task 1, Task 2...")
No owner assigned; unclear who's responsible
No dependencies; tasks scheduled in isolation
Gantt chart doesn't exist or is unreadable
Status never updated (showing Green for overdue tasks)
Resource allocation ignored; Jane assigned 80 hours per week (>40)
Milestones missing or vague ("TBD")
Critical path not identified; don't know what drives schedule
Risk register not maintained; surprises come out of nowhere
```

## Common Mistakes

1. **Mistake**: Tasks have no owner; work falls through cracks.
   → **Fix**: Every task must have a name in the Owner column. Assign explicitly; revisit weekly.

2. **Mistake**: Gantt chart is never updated; executives rely on stale chart.
   → **Fix**: Update dates/% complete weekly. Automate: formula-based dates recalculate automatically.

3. **Mistake**: Status is marked Green even though task is late.
   → **Fix**: Use formula: IF(Actual % Complete < Expected % Complete, Red, Green).

4. **Mistake**: Dependencies aren't tracked; Task B starts before Task A finishes.
   → **Fix**: Fill Predecessor column for all dependent tasks. Highlight critical path.

5. **Mistake**: Resource allocation ignored; people over-capacity, project late.
   → **Fix**: Check capacity matrix weekly. If >100%, escalate or add resources.

## Anti-Patterns
- Never skip WBS numbering. (Hierarchy is how you track tasks and dependencies.)
- Never leave a task un-owned. (Unowned work slips and defaults.)
- Never ignore dependencies; schedule tasks in isolation. (Critical path drives schedule.)
- Never keep two versions of the tracker (one spreadsheet, one email). (Single source of truth.)
- Never update status manually without a formula. (Manual updates get stale; formulas auto-update.)
- Never ignore when someone is over-capacity. (Over-capacity causes delays and quality issues.)
