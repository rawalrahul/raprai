# AI Skills Library

High-quality, production-ready skills for AI-assisted development and operations. Each skill is practical, thoroughly documented, and immediately actionable.

## Skills Overview

### Coding Skills (5 new + pre-existing)

#### Meta & Foundational
- **151: Skill Creator** (intermediate, 199 lines)
  - Design reusable AI skills with clear components
  - Meta-skill: create more skills like these
  - Use when: building prompt libraries, teaching skill design

#### Backend & Integration
- **152: MCP Server Builder** (advanced, 466 lines)
  - Build Model Context Protocol servers for LLM tool integration
  - Complete examples: database queries, error handling, deployment
  - Use when: exposing APIs/databases to Claude, production agents

#### Frontend & UI
- **153: React Artifact Builder** (intermediate, 523 lines)
  - Self-contained React components as single HTML files
  - CDN imports, hooks, Tailwind CSS, no build tools needed
  - Use when: creating demos, prototypes, shareable tools

#### Testing & Quality
- **154: Web App Tester** (intermediate, 594 lines)
  - Automated testing with Playwright
  - Selector strategies, dynamic content, CI integration
  - Use when: regression testing, login flows, form validation

### DevOps Skills (1 total)

#### Monitoring & Debugging
- **155: Agent Debugger** (advanced, 768 lines)
  - Systematically debug AI agents using execution traces
  - Root cause analysis, token profiling, A/B testing
  - Use when: agents fail, optimizing token usage, production agents

## Quick Start

### 1. Get Started with Skills
```bash
# Navigate to skills directory
cd /path/to/ai-skills

# Read a skill
cat coding/151-skill-creator.md

# Use a skill
# Copy examples and follow step-by-step instructions
```

### 2. Use Skill Creator (151)
Create your own skills following the exact structure used here.

### 3. Build MCP Servers (152)
Expose your databases and APIs to Claude:
```python
# Copy the server.py template from skill 152
# Customize for your database
# Deploy with Docker or systemd
```

### 4. Create React Artifacts (153)
Build interactive demos instantly:
```html
<!-- Copy the HTML skeleton from skill 153 -->
<!-- Paste into artifact viewer or .html file -->
<!-- Works immediately, no build step -->
```

### 5. Test Web Apps (154)
Automate regression testing:
```bash
# Follow skill 154 setup instructions
npm install --save-dev @playwright/test
npx playwright test
```

### 6. Debug Agents (155)
Trace failing agents systematically:
```python
# Use the DebugAgent class from skill 155
# Analyze traces to find root causes
# A/B test fixes with measurable improvements
```

## Structure of Each Skill

Every skill follows this proven structure:

```yaml
---
name: kebab-case-name
description: "What this does and why it matters"
category: coding|devops
difficulty: beginner|intermediate|advanced
model_boost: "What weak models get wrong"
---

# Title

## Purpose (2-3 sentences)
## When to Use (triggers + anti-triggers)
## Instructions (8-12 atomic, numbered steps)
## Output Template (expected deliverables)
## Quality Gates (5-7 checkboxes)
## Examples (good output + bad output)
## Common Mistakes (real-world errors with fixes)
## Anti-Patterns (what NOT to do)
```

## Key Features

✓ **No Generic Filler**: Every section addresses real problems
✓ **Real Code Examples**: 50+ copy-paste executable examples
✓ **Actionable Steps**: 8-12 atomic, numbered, unambiguous steps
✓ **Quality Gates**: 5-7 specific, measurable checkpoints per skill
✓ **Common Mistakes**: Documented based on actual developer issues
✓ **Anti-Patterns**: Clear guidance on what to avoid
✓ **Immediately Useful**: Follow the skill and get results the same day

## Statistics

- **Total Lines**: 2,345+
- **Code Examples**: 50+
- **Real-World Use Cases**: 30+
- **Quality Gates**: 35+ total (7 per skill)
- **Common Mistakes**: 30+ documented
- **Anti-Patterns**: 25+ listed

## Difficulty Progression

**Intermediate (Get Started)**
- 151: Skill Creator - Design reusable prompts
- 153: React Artifact Builder - Create instant UI demos
- 154: Web App Tester - Automate testing

**Advanced (Master & Deploy)**
- 152: MCP Server Builder - Production integrations
- 155: Agent Debugger - Systematic root cause analysis

## Use Cases

### I want to...

- **Create more skills** → Start with Skill Creator (151)
- **Give Claude access to my database** → Use MCP Server Builder (152)
- **Build a shareable prototype** → Use React Artifact Builder (153)
- **Automate testing** → Use Web App Tester (154)
- **Debug failing agents** → Use Agent Debugger (155)
- **Learn best practices** → Read the Common Mistakes & Anti-Patterns sections

## Technologies Covered

**Backend**: Python, FastMCP, LangChain, LangGraph, psycopg2
**Frontend**: React 18, Tailwind CSS, JavaScript
**Testing**: Playwright, pytest
**DevOps**: Docker, systemd, GitHub Actions
**Monitoring**: Token tracking, trace analysis, telemetry

## Next Steps

1. **Pick a skill** that matches your current need
2. **Read the Purpose & When to Use** sections (2 min)
3. **Follow the numbered steps** (15-120 min depending on difficulty)
4. **Check the quality gates** to verify success
5. **Reference Common Mistakes** if you get stuck
6. **Use as a template** for similar work in the future

## Support

Each skill includes:
- Detailed step-by-step instructions
- Multiple real-world code examples
- Common mistakes with solutions
- Quality gates for self-verification
- Examples of good vs. bad output
- Anti-patterns to avoid

If stuck: Check the Common Mistakes section first—your issue is probably documented there.

---

**Created**: March 5, 2026
**Format**: Markdown with embedded YAML frontmatter
**Status**: Production-ready, immediately actionable
