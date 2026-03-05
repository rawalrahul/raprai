---
name: tutorial-writer
description: "Write comprehensive step-by-step tutorials with prerequisite review, clear learning outcomes, progressive complexity scaffolding, worked exercises, troubleshooting guides, and transfer tasks. Suitable for skills-based learning in tech, academics, and professional domains."
category: education
difficulty: intermediate
model_boost: "Fixes unclear tutorials with giant jumps in complexity, missing error handling, and no practice tasks"
---

# Tutorial Writer

## Purpose
This skill generates clear, complete tutorials that teach procedural or skill-based learning: programming, technical software, lab techniques, academic procedures (research, essay writing), artistic skills, professional workflows. Tutorials combine narrative explanation, step-by-step procedures, visual descriptions, worked examples, practice exercises (with intentional errors for debugging), and transfer tasks (applying skills in new contexts). Each tutorial has realistic pacing, prerequisites clearly stated, and contingency plans for common mistakes.

## When to Use
- Teaching software/coding skills to beginners or intermediate learners
- Creating lab procedure guides for science courses
- Writing how-to guides for academic research or writing skills
- Documenting professional workflows or processes
- Teaching artistic or technical craft skills
- **Do NOT use when**: Teaching conceptual understanding primarily (use lesson-planner or explainer), assessing mastery (use quiz-generator), or designing entire courses (use curriculum-designer)

## Instructions

### Step 1: Define Skill, Outcomes, and Prerequisites
Name the skill precisely: "Using Find & Replace in Microsoft Word," "Setting up a Python virtual environment," "Conducting a literature search," "Watercolor wet-on-wet technique." Write 3-5 specific learning outcomes: "Students will [VERB] [SKILL] as demonstrated by [EVIDENCE]." Example: "Students will configure a Python virtual environment independently, installing required packages, as demonstrated by creating and activating a venv that includes Django and PostgreSQL."

List prerequisite knowledge or skills. Example for Python venv: Assumes familiarity with command line (cd, ls, mkdir), basic understanding of what libraries are, Python already installed. Do NOT assume knowledge students might not have. If many students lack prerequisites, add a "Prerequisite Review" section that covers them in 2-3 minutes.

### Step 2: Create Prerequisite Review (if needed)
If students need foundational knowledge before starting, provide a 1-2 minute review or short video/link to refresh. Example for essay writing tutorial: "Before we start, you should be able to identify the thesis statement in a paragraph. Here's a quick refresher: A thesis is the main argument the author is making..."

Include a checkpoint: "Do you feel comfortable with [prerequisite]? If not, spend 10 minutes reviewing [resource] before continuing."

### Step 3: Set Clear Learning Outcomes and Success Criteria
Restate outcomes in student-friendly language. Include success criteria—what "done" looks like. Example: "By the end of this tutorial, you will have created a GitHub repository with an initial commit. You'll know you're successful when: (1) You can see your repository on github.com, (2) You can clone it to your local computer, (3) You have at least one file committed with a meaningful commit message."

### Step 4: Break Skill into Logical Sub-Steps (5-10 steps maximum)
Decompose the overall skill into manageable chunks. Each sub-step should be 2-5 minutes of instruction/practice, not 30 minutes. Example for "Creating a Google Scholar alert":
1. Navigate to Google Scholar
2. Search for your research topic
3. Click "Create alert" on search results page
4. Customize alert settings (frequency, email)
5. Verify alert activation

Each step should build on previous ones, increasing slightly in complexity. First steps should be the most concrete; later steps can involve decision-making or troubleshooting.

### Step 5: Write Each Step with Multiple Modalities
For each step, include: (a) Narrative explanation (what you're doing and why), (b) Specific instructions (numbered sub-actions), (c) Visual description (what you should see; where to look on screen), (d) Caution notes (common mistakes for this step). Do not assume students can infer steps—be explicit.

Example Step 2 (Search for your research topic):
Narrative: "Now you'll search for your topic. Google Scholar indexes millions of academic papers, so be strategic with keywords. More specific keywords help you find relevant papers and get fewer irrelevant results."

Specific Instructions:
1. In the search box at the top of the page, type your research topic (3-5 keywords)
2. Example: If studying climate change effects on coral, type: "climate change coral bleaching"
3. Press Enter or click the search icon
4. Review the first 3-5 results to see if they're relevant

Visual Description: "The search box is a white text field near the top of the page. Once you search, you'll see a list of papers with the title in blue, the authors below, and a snippet of text. The papers are ranked by relevance, so most relevant usually appear first."

Caution Notes: "Avoid very general searches like 'climate change'—you'll get thousands of papers. Avoid super specific searches like 'climate change coral bleaching in the Great Barrier Reef in 2019'—you might miss important papers. Find the middle ground."

### Step 6: Provide Worked Examples and Screenshots/Illustrations
Include at least one worked example showing the complete process from start to finish. For each major step, provide a visual (screenshot if technical, illustration if procedural, detailed description if written skill). Annotate visuals with arrows, labels, or callouts showing exactly where to click, what to look for, what should change.

Example annotation for screenshot: "↓ Click here (red arrow). You'll see a dropdown menu appear (like in the next screenshot below)."

For written/procedural skills (essay writing, lab techniques), describe in precise detail: "Your introduction should be about 100-150 words, indented 0.5 inches, in a 12-point font. It should include [X]."

### Step 7: Build Progressive Practice Exercises
Create 2-3 practice tasks that build in difficulty:
- **Guided practice**: Detailed instructions provided; students follow and practice. Scaffold heavily. Include answer checks.
- **Partially guided practice**: Some instructions provided; students make decisions. More independence.
- **Independent practice**: Minimal instructions; students apply skill in a new context (transfer).

Crucially, include intentional errors in practice exercises that students must debug. Example for Python tutorial: "Run this code (intentionally missing a package import). What error message do you get? What does it mean? Fix it. This is a real error you'll encounter; now you know how to solve it."

Example for essay writing: "Here's a thesis statement with a common problem (too broad, multiple claims, unclear). Identify the problem. Rewrite to make it more specific."

### Step 8: Create Troubleshooting Guide
Anticipate 3-5 things that commonly go wrong and create a troubleshooting section. For each: (a) Symptom (what the student sees), (b) Likely cause, (c) Solution with steps. Include error messages if relevant. Make this searchable—students should be able to find help quickly.

Example for Git tutorial:
**Problem**: "I get 'fatal: not a git repository' error"
Symptom: This error appears when you try a Git command
Likely Cause: You're in a folder that hasn't been initialized as a Git repository yet
Solution:
1. Type `pwd` to see which folder you're in
2. Type `git init` to initialize that folder as a Git repository
3. Try your original command again
Prevention: Always run `git init` in your project folder before using other Git commands.

### Step 9: Include Transfer Tasks and Extension
Provide 1-2 "transfer tasks" where students apply the skill in a new, slightly different context. These deepen learning and show whether students understand the underlying skill or just memorized steps.

Example for Vlookup tutorial: "You learned Vlookup to find student grades. Now use Vlookup to find which students are on the honor roll (GPA > 3.5) by looking up names from a student list in a second table."

Include optional extensions for advanced learners: "Once you're comfortable with Vlookup, try combining it with an IF statement to create conditional lookups."

### Step 10: Design Realistic Pacing and Time Allocation
Estimate time for each step: prerequisite review (5 min), each step (2-5 min), worked example (5-10 min), practice exercises (10-20 min), troubleshooting (as needed), transfer task (10-15 min). Total realistic time. Example: "This tutorial takes 45-60 minutes if you work through all sections. If you're short on time, skip optional extensions but do the practice exercises."

Provide checkpoint guidance: "After Step 4, pause and verify you've completed [milestone]. You should be able to [do X]. If not, review Step 4 before continuing."

## Output Template

```
TUTORIAL: [Skill Name] | Level: [Beginner/Intermediate/Advanced] | Time: [X minutes]

LEARNING OUTCOMES
By the end of this tutorial, you will be able to:
1. [Outcome 1]
2. [Outcome 2]
3. [Outcome 3]

SUCCESS CRITERIA
You'll know you've succeeded when:
1. [Specific, observable criterion 1]
2. [Specific, observable criterion 2]
3. [Specific, observable criterion 3]

PREREQUISITES
Before starting, you should be familiar with:
- [Prerequisite 1 with brief definition/resource link if needed]
- [Prerequisite 2]

PREREQUISITE REVIEW [if needed]
[1-2 minute explanation of critical prerequisite knowledge]

OVERVIEW
[Big picture explanation: What is this skill? Why learn it? When will you use it? (1-2 paragraphs)]

STEP 1: [Step Name]
Narrative: [What you're doing and why]
Instructions:
1. [Sub-action 1]
2. [Sub-action 2]
3. [Sub-action 3]
Visual Description: [What you should see; where things are on screen]
Caution: [Common mistakes for this step]
Checkpoint: [Brief verification task]

[Repeat STEP 2-10 with same structure]

WORKED EXAMPLE
[Complete walkthrough of the skill from start to finish with annotations/screenshots]

PRACTICE EXERCISES
Guided Practice 1: [Detailed instructions; students follow exactly]
[Task description; expected outcome; answer provided]

Partially Guided Practice 2: [Some scaffolding; students make decisions]
[Task description; hints provided; answer with explanation]

Independent Practice 3: [Minimal scaffolding; students apply in new context]
[Task description; students must problem-solve]

DEBUGGING & COMMON ERRORS
[For practice exercises that intentionally include errors]
Error 1: [Symptom] → [Cause] → [Solution]
Error 2: [Symptom] → [Cause] → [Solution]

TROUBLESHOOTING GUIDE
Problem 1: [Symptom students might see]
Likely Cause: [What went wrong]
Solution: [Step-by-step fix]

Problem 2: [Symptom]
Likely Cause: [What went wrong]
Solution: [Step-by-step fix]

[Repeat for 3-5 common problems]

TRANSFER TASK (Apply in New Context)
[Task requiring students to apply skill in a different but related scenario]

OPTIONAL EXTENSION
[Deeper or more advanced application of the skill]

PACING GUIDE
- Prerequisite Review: [X min]
- Steps 1-3: [X min]
- Steps 4-6: [X min]
- Worked Example: [X min]
- Practice Exercises: [X min]
- Troubleshooting (as needed): [X min]
- Transfer Task: [X min]
Total Time: [X-Y minutes]

NEXT STEPS
[What to do after completing this tutorial; related skills or advanced applications]
```

## Quality Gates
1. **Outcome Clarity**: Learning outcomes are specific, measurable, observable; aligned to skill being taught
2. **Step Granularity**: Each step is 2-5 minutes max; no giant jumps in complexity; builds progressively
3. **Modality Variety**: Each step includes narrative, specific instructions, visual description, caution/common mistakes
4. **Worked Example Completeness**: Shows full start-to-finish process with annotations; student can follow along
5. **Progressive Practice**: Guided → Partially Guided → Independent progression; intentional errors included for learning
6. **Troubleshooting Specificity**: Each problem includes symptom, likely cause, and solution; not vague ("try again")
7. **Transfer Task Authenticity**: Requires applying skill in genuinely different context, not just "do the same thing again"
8. **Realistic Pacing**: Time estimates are honest; total time doesn't overestimate student attention span

## Examples

### Good: GitHub Repository Setup (Beginner)
**Learning Outcomes**:
1. Create a new GitHub repository
2. Clone the repository to your local computer
3. Add files and make your first commit

**Success Criteria**:
1. Repository is live on github.com with your username visible
2. You can run `git clone [your-repo-url]` and get the files on your computer
3. You've made at least one commit with a meaningful message (not "first commit")

**Prerequisites**:
- GitHub account created (sign up at github.com if needed)
- Git installed on your computer (verify by running `git --version` in terminal)
- Comfortable using command line (cd, ls, mkdir, text editor)

**Step 1: Create Repository on GitHub**
Narrative: "Your repository is like a project folder in the cloud. GitHub hosts it and tracks all changes you make. Creating a repository is the first step."
Instructions:
1. Go to github.com and log in
2. Click the "+" icon in the top right → "New repository"
3. Name your repository [something descriptive without spaces, use hyphens like "my-first-project"]
4. Add a description (optional but helpful)
5. Choose "Public" (visible to others) or "Private" (only you)
6. Check "Add a README file"
7. Click "Create repository"
Visual Description: "You'll see a new page with your repository name at the top, a code button (green), and your first file README.md listed."
Caution: "Don't add spaces in your repository name. GitHub converts them to hyphens, which is awkward. Use hyphens yourself."

**Worked Example**:
Complete walk-through with screenshots showing each step, then showing final result (repository page with README visible).

**Guided Practice 1**:
"Create a new repository named 'my-learning-project' and add a README. Take a screenshot of your new repository page. Does it show your name and the repository name in the URL?"

**Transfer Task**:
"Create a second repository for a project you're interested in (not 'my-first-project' but something real you'll use). This time, don't follow step-by-step—do it from memory. If you get stuck, refer back to Troubleshooting."

### Bad: Git Tutorial
"Git is a version control system. To use it, initialize a repository with `git init`, add files with `git add`, commit with `git commit -m`, push with `git push`. See GitHub for more info."

**Problems**:
- No learning outcomes (what will students actually do?)
- No prerequisites (assumes command line knowledge)
- No worked example (students see no visual reference)
- No practice (students don't actually try)
- No troubleshooting (students stuck with no help)
- Commands listed but not explained in context
- Giant jumps in complexity; no progression

## Common Mistakes

1. **Steps Too Large**: "Step 2: Set up your environment" without breaking down the actual sub-steps. Students don't know which buttons to click or what to expect. Instead: 6-8 granular steps, each 2-5 minutes max.

2. **Assuming Prior Knowledge**: "Use your IDE to compile the code" without explaining what an IDE is or how to open one. Instead: State prerequisites explicitly. If many students lack them, include a Prerequisite Review section.

3. **No Worked Example**: Students read instructions but have no visual reference or example showing the complete process. Instead: Include a full worked example with screenshots/annotations showing exactly what should happen at each step.

4. **Practice Exercises Without Debugging**: "Try this code" but code works perfectly on first try. Students don't learn error handling. Instead: Include practice with intentional errors students must debug. Label: "This code has a bug. Find it and fix it. This error is common in real projects."

5. **Vague Troubleshooting**: "If you get an error, try again" or "If that doesn't work, ask for help." Instead: Specific troubleshooting with symptom, cause, and solution. Searchable by error message or symptom.

## Anti-Patterns

1. **Procedure Manual Masquerading as Tutorial**: Instructions that list steps without explanation or context. No "why," just "what." Students follow steps mechanically and can't apply skill in new contexts. Instead: Include narrative explanation of what you're doing and why. Help students understand underlying logic.

2. **Single Path, No Branching**: Tutorial assumes everyone follows the same path successfully. No acknowledgment of mistakes or variations. Instead: Include troubleshooting, alternate paths ("If you use Mac instead of Windows, step 3 is different"), and contingency plans.

3. **No Transfer Beyond Repetition**: Practice exercises are identical to examples or change only values, not context. Students can't apply skill in new situations. Instead: Include transfer tasks where students apply the skill in genuinely different contexts.

4. **Overwhelming Length**: 30-page tutorial with no checkpoints. Students lose track or lose focus. Instead: Break into smaller, standalone tutorials (each 15-30 minutes max). Include checkpoints after major sections: "Pause and verify you can do X before continuing."

