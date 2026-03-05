---
name: skill-creator
description: "Design and validate high-quality AI skills/prompts that extend assistant capabilities with structured components, clarity checks, and effectiveness testing"
category: coding
difficulty: intermediate
model_boost: "Weak models write vague, untestable skills with unclear triggers and missing quality gates. This skill enforces atomic components, operational precision, and measurable verification."
---

# AI Skill Creator

## Purpose
This skill teaches you to architect reusable, high-impact prompts/instructions that AI assistants can reliably execute. A well-designed skill is modular, unambiguous, testable, and focused—it's the difference between "write better copy" (vague) and "analyze competitor headlines for emotional triggers" (actionable). This meta-skill arms you to build a library of capabilities that compound over time.

## When to Use
- You want to codify a repeatable process into an AI instruction
- You're building a personal skill library or team playbook
- You need to teach others how to accomplish complex tasks consistently
- **Do NOT use when**: The task is one-off or highly contextual without patterns

## Instructions

### Step 1: Define the Core Problem
Write one sentence answering: "What gap does this skill fill?" Example: "Developers waste hours debugging agent loops—this skill identifies root causes systematically."

Don't write: "Make debugging easier." Write: "Trace agent execution to detect infinite retry patterns, wrong tool selection, and hallucinated outputs."

### Step 2: Establish Trigger Conditions
List 3-5 specific situations where someone should use this skill. Be concrete.

**Good triggers:**
- "When an AI agent keeps calling the same tool with different parameters"
- "When a React component renders but state doesn't update after user interaction"

**Bad triggers:**
- "When something is broken" (too vague)

Also list 2-3 anti-triggers (when NOT to use it).

### Step 3: Create the Frontmatter
```yaml
---
name: kebab-case-name
description: "Action + outcome. 15-20 words. What weak models get wrong."
category: coding|data|devops|writing|research
difficulty: beginner|intermediate|advanced
model_boost: "Specific failure mode this prevents"
---
```

Name should be a verb or gerund. Bad: `api-help`, Good: `api-error-resolver`.

### Step 4: Write Purpose (2-3 sentences)
- Sentence 1: What this skill does functionally
- Sentence 2: Why it matters (consequence of not doing it)
- Sentence 3: Scope/limitations (optional)

Example: "This skill breaks down React component state bugs by isolating render triggers and verifying data flow. Without this, hours vanish debugging symptoms instead of root causes. Works best for functional components with hooks."

### Step 5: Design Numbered Steps (8-12 detailed steps)
Each step = one decision or action. Not: "Build the app." Instead:

1. Identify whether you're dealing with a state update issue or render issue (ask: did props change but component didn't re-render?)
2. Add `console.log` inside the component function to verify it's re-running
3. Check React DevTools Profiler to measure render duration
4. etc.

**Include examples.** If step 3 says "examine the API response," show a sample response and what to look for.

### Step 6: Create an Output Template
Show exactly what success looks like. Not just "a diagnosis" but:

```
## Bug Analysis Report

**Root Cause:** [Specific mechanism, e.g., "State updated via setTimeout outside effect cleanup"]
**Evidence:** [Concrete proof from logs/traces]
**Fix:** [Code change or pattern to apply]
**Verification:** [How to confirm it's fixed]
```

### Step 7: Write Quality Gates
Checklist of 5-7 yes/no items that prove the skill was executed well:

- [ ] Steps are numbered and atomic (one decision per step, not "do steps 1-3 together")
- [ ] Examples include actual code/output, not just descriptions
- [ ] The output addresses the original problem statement
- [ ] Anti-triggers are documented (when NOT to use this)
- [ ] Someone without domain knowledge could follow these steps
- [ ] No circular reasoning (step 5 doesn't rely on step 8)
- [ ] Time estimate is provided (e.g., "takes 15-30 minutes")

### Step 8: Document Common Mistakes
List 2-3 real errors people make when executing this skill:

**Mistake:** Assuming the first tool call that fails is the root cause.
**Fix:** Trace back 2-3 tool calls earlier to find the actual bad state.

**Mistake:** Skipping manual verification and trusting automated checks only.
**Fix:** Always run the fix manually in a controlled environment first.

### Step 9: Include Anti-Patterns
Call out what NOT to do:

- Never assume the error message is accurate—trace the actual execution
- Never skip the "when NOT to use" section when teaching others

### Step 10: Test on a Real Case
Walk through your skill using a genuine example from your domain. Can someone else follow it blindly and succeed?

### Step 11: Add a Worked Example
Show a before/after. Include:

**Scenario:** "User reports form not submitting after data entry"
**Bad Approach:** "Run the form and see what happens" (relies on intuition)
**Good Approach:** [Your 8-12 steps applied to this scenario]
**Outcome:** "Identified that form validation reset state, which cleared the submission callback"

### Step 12: Iterate Based on Feedback
If someone uses your skill and gets stuck on step 4, that step needs more detail or an example. Refine.

## Output Template

A complete skill file should:
```
---
[frontmatter with all required fields]
---

# Title

## Purpose
[Functional description + why it matters]

## When to Use
- [3+ specific trigger scenarios]
- **Do NOT use when**: [2+ anti-triggers]

## Instructions
### Step 1-12: [Detailed, numbered, with examples]

## Output Template
[Concrete template showing deliverable format]

## Quality Gates
- [ ] [5+ verification checkboxes]

## Examples
### Good Output (excerpt)
### Bad Output (with explanation)

## Common Mistakes
1. **Mistake**: ... → **Fix**: ...
2. ...

## Anti-Patterns
- Never...
```

## Quality Gates
- [ ] Skill solves a real, repeatable problem (not a one-off task)
- [ ] Each step is atomic and doesn't depend on later steps
- [ ] At least 2 real code examples or concrete outputs are included
- [ ] When/when-not triggers are specific and unambiguous
- [ ] A beginner could execute this skill without domain expertise
- [ ] Common mistakes reflect genuine errors, not theoretical ones
- [ ] The skill can be completed in the stated difficulty timeframe (beginner: <30min, intermediate: 30-90min, advanced: >90min)

## Examples

### Good Output (excerpt)
**Skill:** api-response-validator
**Name field:** `api-response-validator` ✓ (verb-based, clear)
**Step 2:** "Make a GET request to `/users/{id}` and print the response to inspect field names" ✓ (specific action with example endpoint)
**Quality gate:** "Someone without API experience could follow these steps" ✓ (includes curl/fetch examples)

### Bad Output (what to avoid)
**Skill:** api-help
**Name field:** `api-help` ✗ (too generic, no action)
**Step 2:** "Check the API" ✗ (vague, doesn't say how)
**Quality gate:** Assumes reader understands REST/JSON already ✗ (excludes beginners)

## Common Mistakes

1. **Mistake:** Writing skills for "anything that might be useful" → **Fix:** Focus on recurring problems you've solved 5+ times. Specificity beats breadth.

2. **Mistake:** Omitting examples because "it's obvious" → **Fix:** Nothing is obvious. If you can't write an example, the step is too vague.

3. **Mistake:** Skipping the "when NOT to use" section → **Fix:** Anti-triggers prevent misapplication. A debugging skill that applies to all code is useless.

4. **Mistake:** Writing 20+ steps → **Fix:** Consolidate to 8-12 atomic steps. Long skills are hard to follow.

5. **Mistake:** Testing only with your own context → **Fix:** Have someone unfamiliar with the domain follow your steps blindly. Where they get stuck = where you need clarity.

## Anti-Patterns

- Never write a skill that only applies to your specific codebase (no portability)
- Never skip the "time estimate" (people can't tell if it's a 10-minute task or 2-hour project)
- Never assume terminology without defining it first
- Never mix multiple unrelated problems into one skill (a skill should solve one problem well, not five poorly)
