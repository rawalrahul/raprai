---
name: product-requirements-doc
description: "Write PRDs using problem statements, user stories (As a/I want/so that), acceptance criteria (Given/When/Then), wireframe descriptions, data requirements, API contracts, release criteria, non-functional requirements, MoSCoW prioritization, and dependencies."
category: professional
difficulty: intermediate
model_boost: "Weak models skip acceptance criteria, conflate features with user needs, or miss non-functional requirements"
---

# Product Requirements Document (PRD)

## Purpose
A PRD translates user needs and business objectives into a detailed specification that engineers can build. It bridges the gap between strategy (why we're building this) and implementation (how to build it). Strong PRDs reduce ambiguity, prevent scope creep, and enable asynchronous work across teams. This skill combines user research (understanding the problem), feature design (scoping the solution), and technical specification (enabling implementation).

## When to Use
- **Planning a new product or major feature** (after user research, before engineering begins)
- **Defining a quarterly roadmap** (to guide team priorities)
- **Requesting engineering estimation** (engineers need detailed specs to estimate effort)
- **Cross-team coordination** (design, engineering, product all need same spec)
- **Do NOT use when**: Doing user research (use research templates first), or managing sprints day-to-day (use Jira/tickets for that level of detail)

## Instructions

### Step 1: Define the Problem Statement
Start with why, not what. What customer problem are we solving?

**Poor problem statement**: "Users want a dark mode."
**Better problem statement**: "Users report eye strain when using the app at night. Support tickets show 12% of users disable push notifications after 9pm to avoid glare. Dark mode reduces eye strain and would improve retention of evening users (our data shows 40% usage drop after 6pm)."

**Problem Statement Template**:

```
PROBLEM STATEMENT

User: [Who has the problem?]
Context: [When/where do they encounter the problem?]
Pain point: [What's frustrating?]
Current behavior: [How do they work around it today?]
Business impact: [Why does this matter to us? (retention, revenue, etc.)]
Success metric: [How will we know we've solved it?]

Example:
User: Evening and night-shift users of our analytics platform
Context: Between 9pm-6am, many users work in low-light environments (home offices, late-night analysis)
Pain point: Bright white UI causes eye strain, reducing comfort and session duration
Current behavior: Users leave the app open but reduce brightness or use blue-light filters on their devices (workaround)
Business impact: Evening usage represents 30% of daily active users but has 40% shorter session duration than daytime. Dark mode would improve evening retention and engagement
Success metric: Evening session duration increases 20%; evening active users increase 15%
```

### Step 2: Write User Stories
User stories frame the requirement from the user's perspective. Format: "As a [role], I want [action/feature], so that [benefit]."

**User Story Template**:

```
USER STORY: [Short title]

As a [user role], I want [action/feature], so that [business value/benefit].

Context: [Additional context about why this matters]
Related research/data: [User testing quotes, analytics, competitor analysis]
Acceptance criteria: [See Step 4]
Notes: [Edge cases, technical considerations]
```

**Example User Stories** (Dark Mode Feature):

**Story 1**: "Night Mode Toggle"
As an evening user, I want to toggle between light and dark themes, so that I can use the app comfortably in low-light environments without eye strain.

Context: Users working late (9pm+) report discomfort with bright screens. Support data shows 12% disable notifications to reduce glare.
Acceptance criteria: [See below]

**Story 2**: "System Theme Sync"
As a user with dark mode enabled on my device, I want the app to automatically adopt dark mode when I first log in, so that I don't have to manually toggle each time I use it.

Context: Users expect web apps to respect system preferences (like iOS and Android do).
Acceptance criteria: [See below]

**Story 3**: "Persistent Theme Preference"
As a user who prefers dark mode, I want my theme choice to be remembered across sessions, so that I don't have to set it every time I log in.

Context: Users should set preference once and it should "stick."
Acceptance criteria: [See below]

### Step 3: Define Acceptance Criteria Using Given/When/Then
Acceptance criteria are the definition of "done." Use Given/When/Then format (Gherkin language).

**Acceptance Criteria Format**:

```
GIVEN [Initial state/precondition]
WHEN [Action taken]
THEN [Expected outcome]
AND [Additional assertions]
```

**Example Acceptance Criteria** (Dark Mode feature):

**Story 1: Night Mode Toggle**

Scenario 1: User toggles dark mode on
- GIVEN user is logged into the app in light mode
- WHEN user clicks Settings > Appearance > toggle Dark Mode
- THEN all UI colors invert: white backgrounds → dark gray/black, dark text → light text
- AND images/logos maintain legibility (no contrast loss)
- AND toggle switch reflects new state (shows "Dark Mode ON")

Scenario 2: User toggles dark mode off
- GIVEN user is logged in with dark mode active
- WHEN user clicks the dark mode toggle to turn it off
- THEN app reverts to light mode
- AND all stored data remains intact (toggle doesn't clear user data)

Scenario 3: User visits dark mode while on slow network
- GIVEN user is on a slow 3G connection
- WHEN user toggles dark mode
- THEN theme change completes within 2 seconds (no spinner/loading state)
- AND theme persists if user navigates to another page

**Story 2: System Theme Sync**

Scenario 1: First login with device dark mode enabled
- GIVEN user has never logged into the app before
- AND user's operating system is set to dark mode
- WHEN user logs in for the first time
- THEN app automatically loads in dark mode
- AND no manual setup required

Scenario 2: System theme changed after app is open
- GIVEN app is open in light mode
- WHEN user changes OS theme to dark mode
- THEN app detects the change within 5 seconds
- AND app switches to dark mode automatically
- AND user is not forced to reload the page

### Step 4: Describe Wireframes or UI Mockups
Document the user interface. Text descriptions are better than vague references; link to Figma/design files for detailed mockups.

**Wireframe Description Format**:

```
SCREEN: [Screen name]

Layout:
- Header: [Description of top navigation]
- Left sidebar: [Navigation, filters, or settings]
- Main content area: [Primary UI elements, tables, forms]
- Footer: [Copyright, links, etc.]

Key UI Elements:
1. [Element name]: [Description, placement, interaction]
2. [Element name]: [Description]

Interaction flow:
[When user clicks X, Y happens]

Responsive behavior:
[On mobile, layout changes to...]

Link to design file: [Figma URL or design tool link]
```

**Example**: (Dark Mode UI)

```
SCREEN: Settings > Appearance

Layout:
- Header: "Appearance Settings" title with back button
- Content area: Theme selection
- Footer: Save/Cancel buttons

Key UI Elements:
1. Theme toggle: Binary switch labeled "Light | Dark"
   - Default: Light (for new users)
   - On toggle, entire app refreshes to new theme
   - Location: Top of Appearance settings

2. Preview: Small preview area (200x200px) showing sample UI in selected theme
   - Shows: Sample text, button, data table
   - Updates in real-time as user toggles

3. "Use system preference" checkbox: If enabled, app adopts OS theme (read-only)
   - Only appears if user is on a device that supports OS theme detection

Interaction:
- User toggles Dark/Light switch
- Preview updates immediately
- User clicks Save
- Entire app reloads in new theme

Mobile behavior:
- Switches stack vertically instead of horizontally
- Preview scales to full width
```

### Step 5: Specify Data Requirements
What data is needed? What's the schema?

**Data Requirements**:

```
DATA MODEL: User Preferences

Field name | Type | Required? | Constraints | Example |
---|---|---|---|---|
user_id | UUID | Yes | Foreign key to users table | "a1b2c3d4-e5f6-..." |
theme_preference | Enum | Yes | Allowed values: "light", "dark", "system" | "dark" |
sync_with_system | Boolean | No | Default: false | true |
last_updated | Timestamp | Yes | Auto-set to current time | "2024-03-05T14:30:00Z" |

Database impact:
- New table: `user_preferences` (if it doesn't exist)
- Or: Add columns to existing `users` table if preferred
- Storage: ~50 bytes per user
- Estimated size for 1M users: 50MB (minimal)

Backward compatibility:
- Existing users without preference: Default to light mode
- Migration: Bulk set all existing users to "light" on deploy
- No data loss risk
```

### Step 6: Define API Contracts (If Backend-Dependent)
If the feature requires new API endpoints, specify the contract.

**API Specification**:

```
ENDPOINT: PATCH /api/v1/users/:userId/preferences

Description: Update user appearance preferences

Request:
- Method: PATCH
- URL: /api/v1/users/:userId/preferences
- Authentication: Bearer token (user's session token)
- Headers: Content-Type: application/json

Request body:
{
  "theme_preference": "dark",
  "sync_with_system": true
}

Response (200 OK):
{
  "user_id": "a1b2c3d4-e5f6-...",
  "theme_preference": "dark",
  "sync_with_system": true,
  "last_updated": "2024-03-05T14:30:00Z"
}

Error responses:
- 400 Bad Request: Invalid theme_preference value (must be "light", "dark", or "system")
- 401 Unauthorized: Missing or invalid authentication token
- 404 Not Found: User not found
- 500 Server Error: Database error

---

ENDPOINT: GET /api/v1/users/:userId/preferences

Description: Retrieve user appearance preferences

Request:
- Method: GET
- URL: /api/v1/users/:userId/preferences
- Authentication: Bearer token

Response (200 OK):
{
  "user_id": "a1b2c3d4-e5f6-...",
  "theme_preference": "dark",
  "sync_with_system": true,
  "last_updated": "2024-03-05T14:30:00Z"
}

Error responses: [Same as above]

---

Performance expectations:
- Response time: <100ms for both endpoints
- No N+1 queries; use database joins if retrieving multiple users
```

### Step 7: Specify Non-Functional Requirements
Performance, security, accessibility, and other cross-cutting concerns.

**Non-Functional Requirements**:

```
PERFORMANCE:
- Theme toggle must complete within 2 seconds (perceived instant on modern browsers)
- Dark mode CSS should be <50KB (don't add bloat)
- First paint time with dark mode: no degradation vs. light mode
- API endpoint response time: <100ms

SECURITY:
- User preferences must respect authorization (user can only modify their own)
- No sensitive data stored in theme preference
- API endpoints require authentication

ACCESSIBILITY:
- Theme toggle must be keyboard accessible (tab through, enter to toggle)
- Toggle must be marked with ARIA labels: aria-label="Toggle dark mode"
- Color contrast in both light and dark modes must meet WCAG AA standard (4.5:1 for text)
- No content should be invisible in either theme

BROWSER COMPATIBILITY:
- Chrome/Firefox/Safari latest 2 versions
- Mobile browsers: iOS Safari 14+, Chrome Android 90+
- Graceful degradation if CSS variables aren't supported (fallback to light mode)

INTERNATIONALIZATION:
- Settings label text must be translatable
- No hardcoded text in UI; all strings externalized to i18n system

RELIABILITY:
- Preference persistence must not be lost if user session times out
- No data corruption if user toggles theme during network latency
```

### Step 8: Apply MoSCoW Prioritization
Prioritize requirements: Must, Should, Could, Won't.

**MoSCoW for Dark Mode Feature**:

| Requirement | Priority | Rationale |
|---|---|---|
| Basic dark/light toggle | **Must** | Core feature; essential for launch |
| Dark mode CSS styling of all UI elements | **Must** | Without this, dark mode doesn't work |
| Toggle accessible via Settings menu | **Must** | Primary way users access feature |
| Persistent theme across sessions | **Must** | Users expect it to "stick" |
| System theme sync (first login) | **Should** | Nice-to-have; improves UX for power users |
| Auto-detect OS theme change while app is open | **Could** | Requires ongoing OS API monitoring; lower priority |
| Theme preview before saving | **Should** | Helps users decide; improves confidence |
| Keyboard navigation of toggle | **Should** | Accessibility; improves usability |
| Custom theme builder (pick colors) | **Won't** | Out of scope for MVP; future enhancement |
| Sync theme across devices | **Won't** | Out of scope; requires feature flag infrastructure |

**Decision**: Implement all MUST and SHOULD items in v1.0. Defer COULD and WON'T to future releases.

### Step 9: Document Dependencies & Assumptions
What else needs to be done? What are we assuming?

**Dependencies & Assumptions**:

```
DEPENDENCIES:

Technical:
- CSS framework must support CSS variables for easy theme switching
  → Action: Design team confirms Tailwind/Material-UI compatibility
- Backend API must support PATCH /users/:userId/preferences
  → Action: Backend team spins up this endpoint (est. 4 hours)
- Database migration to add theme_preference column
  → Action: DBA reviews migration script before deploy

Team:
- Design team must provide dark mode color palette (12-15 colors)
  → Due: By [Date]; blocks frontend dev
- QA must test on 5+ browsers
  → Due: Before release

ASSUMPTIONS:

User behavior:
- We assume users will find the settings toggle within 3 clicks
- We assume dark mode will increase evening session duration by 10-20%
- We assume users with system theme preference set won't manually toggle often

Technical:
- We assume modern browsers support CSS variables (IE11 not supported)
- We assume localStorage is available for persisting user preference
- We assume no users have custom CSS overrides that would conflict

Business:
- We assume dark mode is desirable enough to prioritize over other Q2 features
- We assume no legal/compliance issues with changing UI colors

BLOCKERS:
- None identified at this time
- Color palette from design team is critical path item
```

### Step 10: Define Release & Success Criteria
How do we know this feature is done? How do we measure success?

**Release Criteria** (Definition of Done):

Before shipping to production:
- [ ] All acceptance criteria met (tested by QA)
- [ ] Dark mode works on Chrome, Firefox, Safari, Edge (latest versions)
- [ ] Mobile responsive: iOS Safari and Chrome Android
- [ ] Performance: Toggle completes in <2 seconds, API response <100ms
- [ ] Accessibility: WCAG AA color contrast verified; keyboard navigation works
- [ ] Persistence: Theme saved and restored across sessions
- [ ] Documentation: Help docs updated with dark mode instructions
- [ ] No console errors in dev tools (all warnings resolved)
- [ ] Load testing: No performance degradation under 1000 concurrent users
- [ ] Product sign-off: PM and design lead approve

**Success Metrics** (Post-launch):

Track for 2 weeks after launch:
- Dark mode adoption rate: % of active users who enable dark mode
- Session duration: Average session length (evening users) before vs. after
- Support tickets: Any dark mode-related bugs reported?
- Error rate: Any increase in errors/crashes since launch?
- Retention: Do dark mode users have higher retention?

**Success targets** (if not met, escalate to product):
- Dark mode adoption: 20% of users within 2 weeks
- Session duration: 10% increase for evening users
- Support tickets: <5 dark mode bugs reported
- Retention: No regression compared to baseline

### Step 11: Organize the Complete PRD
Template structure for easy reference.

## Output Template

```
---
PRODUCT REQUIREMENTS DOCUMENT
Product: [Product Name]
Feature: [Feature Name]
Version: 1.0
Date: [Date]
Owner: [PM Name]
---

# [Feature Name]

## 1. Problem Statement
[Who, context, pain point, business impact, success metric]

## 2. User Stories
[4-6 user stories in "As a / I want / so that" format]

## 3. Acceptance Criteria
[Given/When/Then for each user story]

## 4. Wireframes & UI
[Descriptions of screens and interactions; links to design files]

## 5. Data Model
[Schema, constraints, storage impact]

## 6. API Contracts
[Endpoint specifications with request/response examples]

## 7. Non-Functional Requirements
[Performance, security, accessibility, compatibility]

## 8. MoSCoW Prioritization
[Must/Should/Could/Won't table]

## 9. Dependencies & Assumptions
[Technical, team, blockers]

## 10. Release Criteria & Success Metrics
[Definition of done; post-launch success targets]

## Appendix
[Competitor analysis, user research data, market sizing]
```

## Quality Gates

1. **Acceptance Criteria Completeness**: Can a QA engineer read the acceptance criteria and test the feature without asking clarifying questions? If not, add detail.

2. **User Story Justification**: Does each user story have a "so that" that articulates business value (not just feature description)? If not, reframe.

3. **Wireframe Clarity**: Could a engineer build the UI from your wireframe description alone? If not, link to design tool or add more detail.

4. **API Specification Detail**: Are all request/response fields specified with types and constraints? Are error cases covered? If not, add detail.

5. **Non-Functional Completeness**: Have you specified performance, security, accessibility, and browser compatibility? If not, add these sections.

6. **MoSCoW Rigor**: For each "Won't," could you justify why it's not MVP? If a "Won't" item is critical, move it to "Must."

7. **Success Metric Measurability**: Are success metrics quantified and trackable? "Users are happy" is not measurable. "20% of users enable dark mode within 2 weeks" is.

## Examples

### Good PRD

- Problem statement backed by user research data: "Support tickets show 12 users per week reporting eye strain. Evening session duration is 40% shorter than daytime."
- User stories that explain business value: "As an evening user, I want dark mode, so that I can use the app comfortably without eye strain" (not "so that I can use dark mode").
- Detailed acceptance criteria using Given/When/Then; covers main scenario and edge cases (network latency, OS theme change).
- Wireframe description clear enough for engineer to code; links to Figma for details.
- API specification with request/response examples and error cases.
- Non-functional requirements covering performance, security, accessibility.
- MoSCoW with clear rationale for each priority.
- Success metrics quantified: "20% adoption; 10% session duration increase."

### Bad PRD

- "Users want dark mode. Build it."
- No acceptance criteria; engineer has to guess what "done" means.
- No wireframe; engineer guesses at UI placement.
- No non-functional requirements; engineer doesn't know if performance matters.
- No success metrics; no way to measure if the feature mattered.

## Common Mistakes

1. **Conflating features with user needs**: "Users want a dark mode" (feature) vs. "Users experience eye strain at night" (need). Start with the need; dark mode is one solution.

2. **Vague acceptance criteria**: "Dark mode should work" is not an acceptance criterion. Specific: "GIVEN user is in dark mode, WHEN user navigates to a new page, THEN theme persists AND all text is readable (WCAG AA contrast)."

3. **Missing edge cases**: Acceptance criteria covers the happy path but not: Network latency, OS theme change, browser refresh, old browser without CSS variables, user navigating between pages mid-toggle.

4. **No API specification**: Designer and engineer have different ideas of what the API should return. Specify the contract upfront.

5. **Ignoring accessibility**: Dark mode is great for accessibility (WCAG AAA) but can also introduce contrast issues if not designed carefully. Specify accessibility requirements.

6. **Scope creep in PRD**: Listing 20 nice-to-have features as "Should" or "Could" makes the PRD overwhelming. Ruthlessly prioritize; defer non-MVP items.

7. **No success metrics**: You ship dark mode; no one knows if it was worth the effort. Define what success looks like upfront.

## Anti-Patterns

1. **The kitchen-sink PRD**: 40 pages, 50 user stories, 200 acceptance criteria. Too much. Focus on the core feature; iterate later. 10-15 page PRD is typical for a major feature.

2. **The 1-pager**: Opposite problem. Not enough detail for engineering to estimate or start building. A 5-page PRD is too short for anything non-trivial.

3. **Designer-driven PRD**: "The UI looks like this [shows mockup]" without articulating the user need. Start with the need; design follows.

4. **Engineer-first PRD**: "Build an API endpoint that does X" without explaining why users need it. Engineer builds something technically correct but useless.

5. **Writing PRD in a vacuum**: No user research, no stakeholder input. PRD is written by one person then debated for 3 weeks. Write collaboratively; socialize early.

6. **Forgetting to update PRD post-launch**: PRD is written, shipped, then ignored. Update it post-launch with actual metrics and lessons learned. Use it for future planning.
