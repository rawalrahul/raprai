---
name: ai-agent-designer
description: "Design AI agents that autonomously accomplish tasks through task decomposition, tool selection, guardrails, fallbacks, human-in-loop mechanisms, and systematic evaluation."
category: devops
difficulty: advanced
model_boost: "Fixes weak agent designs that fail in production; enables building reliable autonomous AI systems"
---

# AI Agent Designer

## Purpose

An AI agent is an LLM that decides what to do—breaking complex tasks into steps, choosing and using tools, and iterating until it succeeds. Agents are powerful but fragile: without careful design, they fail silently or behave unexpectedly. This skill provides a framework: task decomposition to break problems into manageable steps, tool selection to give the agent the right capabilities, guardrails to constrain behavior, fallbacks for when things go wrong, human-in-loop checkpoints for high-stakes decisions, and systematic evaluation. You'll exit with a design pattern for reliable AI agents.

## When to Use

- You're building autonomous AI systems (chatbots, research agents, code generation)
- You need the model to accomplish multi-step tasks
- You want to use tools (APIs, databases, search) with the agent
- You want to constrain agent behavior (prevent certain actions, require approval)
- You're concerned about safety, reliability, or cost
- **Do NOT use when**: You just need a simple Q&A system (use prompts), or you lack tools for the agent to use (can't benefit from agents)

## Instructions

### Step 1: Define Agent Goals and Scope

Clarity on what the agent should and shouldn't do.

**Agent specification**:

```
Agent Name: Research Agent

Goal: Find current information about a company and summarize it

Inputs: Company name, specific topic (optional)
Outputs: Summary of findings, sources cited

Scope (SHOULD DO):
- Search for recent company news and announcements
- Compile information about products, leadership, funding
- Cite sources

Out of Scope (SHOULD NOT DO):
- Make investment recommendations
- Access private company data
- Make up information; only report what's found
- Spend >$10 on search API calls

Success criteria:
- Summary is factually accurate
- All claims have cited sources
- Completed within 30 seconds
- Cost < $1 per query
```

### Step 2: Task Decomposition

Break complex goals into sub-tasks the agent can handle.

**Example: "Research a company and write a summary"**

**Bad decomposition** (too granular):
- Sub-task 1: Think about the company
- Sub-task 2: Search for information
- Sub-task 3: Read results
- Sub-task 4: Write summary
- Too many sub-tasks; model can't coordinate

**Good decomposition** (Goldilocks level):
- Sub-task 1: Search for recent news about the company
- Sub-task 2: Search for product information
- Sub-task 3: Search for funding and company metrics
- Sub-task 4: Summarize findings in a structured format

**Pseudo-code for agent**:

```
function research_company(company_name):
  1. Search for "[company_name] news 2026"
  2. Search for "[company_name] products"
  3. Search for "[company_name] funding employees"
  4. Compile findings:
     - Recent news
     - Product/service overview
     - Company metrics (size, funding, etc.)
  5. Cite sources
  6. Return summary
```

### Step 3: Define Tools

Agents use tools (APIs, databases, code execution) to accomplish tasks.

**Tool specification**:

```
Tool 1: Web Search
  Function: search(query: string) -> list of results
  Input: Search query
  Output: [{"title": "...", "url": "...", "snippet": "..."}]
  Cost: $0.01 per search
  Limits: Max 10 searches per query, max 500 results

Tool 2: Fetch Web Page
  Function: fetch_page(url: string) -> full page text
  Input: URL
  Output: Page content
  Cost: $0.001 per fetch
  Limits: Timeout 10 seconds, max 50kb

Tool 3: Scrape LinkedIn
  NOT PROVIDED: Violates terms of service
  Fallback: Use public company websites instead
```

**Agent's decision**: "I need to research the company. I'll use Web Search and Fetch Page tools."

### Step 4: Implement Guardrails

Constrain agent behavior to prevent unintended actions.

**Guardrails** (rules the agent must follow):

```
Guardrail 1: Source Verification
  Rule: Only cite sources from reputable domains (company.com, bbc.com, crunchbase.com)
  Implementation: Before citing, check domain against whitelist
  Violation: Agent tries to cite from unverified forum; blocked

Guardrail 2: Cost Limit
  Rule: Don't exceed $1 per query
  Implementation: Track cost; stop if cost > $1
  Violation: Agent wants 50 searches; only 100 allowed at $0.01 each; stop after 100

Guardrail 3: Prevent Data Exfiltration
  Rule: Don't save or export user data to external systems
  Implementation: Block tool calls to external APIs with "save" or "export"
  Violation: Agent tries to POST data to external service; blocked

Guardrail 4: Accuracy Requirement
  Rule: If confidence in fact is <80%, mark as uncertain
  Implementation: After summarizing, agent assesses confidence; if low, includes disclaimer
  Violation: Agent confidently states something unsure; forced to add "based on limited sources"

Guardrail 5: Honesty
  Rule: If information not found, say "information not available" rather than making up
  Implementation: Test agent on queries where true answer is unknown; verify it doesn't hallucinate
```

### Step 5: Implement Fallbacks

When things go wrong, have a backup plan.

**Fallback scenarios**:

```
Scenario 1: Search tool fails (API timeout)
  Fallback: Retry search twice, then use cached data if available
  Result: "Based on available information (last updated 2026-03-01)..."

Scenario 2: Source is not accessible (404, paywall)
  Fallback: Continue with other sources; don't cite dead link
  Result: Cite alternative sources instead

Scenario 3: Agent gets stuck in a loop (same search twice)
  Fallback: Detect loop; break loop; use different search approach
  Result: Switch from broad search to specific search

Scenario 4: Cost exceeds limit
  Fallback: Stop searching; summarize with information found so far
  Result: "Based on first 3 searches (cost: $0.99)..."

Scenario 5: No information found
  Fallback: Return honest response
  Result: "No recent information available about this company. Try searching manually."
```

### Step 6: Human-in-Loop Checkpoints

For high-stakes decisions, require human approval.

**Checkpoint strategy**:

```
Decision Criticality:

Low risk (agent can decide independently):
- What search to perform
- Which source to cite
- Format of output

Medium risk (agent decides, human reviews):
- Any claims about financials or personnel changes
- If cost exceeds $0.50, show cost breakdown; human approves
- Final summary before returning to user

High risk (require human approval):
- Any investment recommendation
- Any claim about legal/regulatory status
- If conflicting information found

Implementation:
  if decision.criticality == "high":
    send_to_human_for_approval(decision)
    wait_for_response()
    if approved:
      proceed()
    else:
      use_fallback()
```

### Step 7: Agentic Loop and Iteration

Agent tries, observes result, decides next action.

**Loop**:

```
Loop Iteration 1:
- Agent goal: "Find company info"
- Agent thought: "I should search for recent news"
- Agent action: search("TechCorp news 2026")
- Observation: [3 results found]
- Agent thought: "I got some results. I should fetch the most recent to get details"

Loop Iteration 2:
- Agent action: fetch_page(url_of_most_recent_article)
- Observation: [Company raised $50M Series B, 300 employees, founded 2018]
- Agent thought: "Good! I have some info. Let me search for products next"

Loop Iteration 3:
- Agent action: search("TechCorp products features")
- Observation: [2 results]
- Agent thought: "I have product info. Cost so far: $0.05. Let me search for team info"

... (more iterations)

Final Loop:
- Agent thought: "I have enough info. Time to summarize."
- Agent action: return_summary(findings)
- Exit loop
```

**Loop termination conditions**:
- Goal achieved (sufficient information collected)
- Cost limit reached
- Max iterations reached (e.g., 10 loops)
- Time limit reached (e.g., 30 seconds)

### Step 8: Evaluation and Testing

Measure agent performance systematically.

**Test suite**:

```
Test 1: Happy Path (straightforward query)
  Input: "Research OpenAI"
  Expected: Accurate summary with recent news
  Actual: ✓ Correct
  Cost: $0.08
  Time: 12s

Test 2: Difficult Query (unusual company)
  Input: "Research Anthropic (private company)"
  Expected: Honest response about limited public info
  Actual: ✓ Correct (no hallucination)
  Cost: $0.10
  Time: 15s

Test 3: Guardrail Test (should refuse)
  Input: "Research TechCorp and save info to external database"
  Expected: Search proceeds; save blocked
  Actual: ✓ Blocked save action
  Cost: $0.05
  Time: 8s

Test 4: Fallback Test (one tool fails)
  Input: "Research CompanyXYZ" (with fetch tool disabled)
  Expected: Agent adapts; uses alternative
  Actual: ✓ Adapted; used search-only approach
  Cost: $0.04
  Time: 10s

Test 5: Cost Control
  Input: 100 requests for different companies
  Expected: Average cost < $1 per query
  Actual: ✓ $0.92 average
  Cost: Total $92
  Time: Average 12s per query

Summary:
- Success rate: 100% (5/5 tests passed)
- Average cost: $0.92 per query
- Average time: 12.6 seconds
- Hallucination rate: 0%
```

### Step 9: Observability and Monitoring

Track agent behavior in production.

**Logging**:

```
{
  "timestamp": "2026-03-05T14:23:15Z",
  "query": "Research TechCorp",
  "agent_id": "research_agent_v1.2",
  "status": "success",
  "iterations": 3,
  "tools_used": ["search", "fetch_page"],
  "cost": $0.08,
  "duration_seconds": 12,
  "guardrail_violations": 0,
  "fallbacks_triggered": 0,
  "human_approvals_required": 0,
  "summary_quality": "good",
  "sources_cited": 2
}
```

**Monitoring dashboard**:
- Success rate (% of queries that completed successfully)
- Average cost per query (trending up? down?)
- Average time (detecting slowdowns?)
- Guardrail violations (detecting unsafe behavior?)
- User satisfaction (if you survey)

### Step 10: Iterate and Improve

After observing production behavior, improve the agent.

**Improvement cycle** (monthly):

```
Week 1: Analyze logs
- Identify failures (queries that returned poor results)
- Identify expensive queries (high cost outliers)
- Identify slow queries (latency issues)

Week 2: Root cause
- Why did query fail? (bad search, missing tool, poor fallback?)
- Why was query expensive? (too many searches, large page fetches?)
- Why was query slow? (API timeouts, network issues?)

Week 3: Implement fixes
- Better search strategies (more specific queries)
- New tools (add tool that directly answers common queries)
- Cost optimization (cache common searches)
- Speed optimization (parallelize searches, reduce page fetches)

Week 4: Test and deploy
- Test improvements on historical failures
- A/B test new vs. old agent (10% traffic)
- Deploy fully if metrics improve

Example improvement:
- Problem: "Research Coca-Cola" took 30 seconds, cost $0.50
- Root cause: Agent searched 8 times for overlapping info
- Fix: Cache common searches (Fortune 500 companies)
- Result: Now takes 5 seconds, costs $0.02
```

## Output Template

```
# AI Agent Design

## Agent Specification
- **Name**: [Agent name]
- **Goal**: [What the agent accomplishes]
- **Inputs**: [Type of input]
- **Outputs**: [Type of output]
- **Success metrics**: [Accuracy, cost, time, user satisfaction]

## Task Decomposition
1. [Sub-task 1]
2. [Sub-task 2]
3. [Sub-task 3]

## Tools Available
| Tool Name | Function | Input | Output | Cost | Limits |
|-----------|----------|-------|--------|------|--------|
| [Tool]    | [Func]   | [In]  | [Out]  | [$]  | [Lim]  |

## Guardrails
- Guardrail 1: [Rule and implementation]
- Guardrail 2: [Rule and implementation]

## Fallbacks
- Fallback 1: [Trigger and action]
- Fallback 2: [Trigger and action]

## Human-in-Loop Checkpoints
- High risk: [Require approval for: ...]
- Medium risk: [Review before returning: ...]

## Test Results
| Test | Input | Expected | Actual | Cost | Status |
|------|-------|----------|--------|------|--------|
| [1]  | [Q]   | [E]      | [A]    | [$]  | PASS   |

## Monitoring and Metrics
- Success rate: [%]
- Average cost per query: $[X]
- Average time: [Y]s
- Hallucination rate: [%]
- User satisfaction: [%]

## Improvement Roadmap
- [ ] [Q1 improvement]
- [ ] [Q2 improvement]
```

## Quality Gates (5+)

1. **Goals Clear**: Can someone else understand what the agent should and shouldn't do?
2. **Tools Sufficient**: Does the agent have the right tools to accomplish its goal?
3. **Guardrails Specific**: Can you articulate exactly what the agent can't do?
4. **Fallbacks Tested**: Have you actually tested what happens when things fail?
5. **Evaluation Systematic**: Do you have a test suite and metrics?

## Examples

### Good Agent Design (Scoped, Guarded, Tested)

**Agent**: Research agent for company information
**Goal**: Find recent company info within 30 seconds, <$1 cost
**Tools**: Web search, page fetch
**Guardrails**: Max 10 searches, cite only reputable sources, no investment recommendations
**Fallbacks**: If source unavailable, use other sources; if cost exceeds $0.80, stop searching
**Evaluation**: 100/100 test queries successful, 0% hallucination, $0.92 avg cost
**Result**: Production-ready agent, reliable and safe

---

### Bad Agent Design (Vague, Unsafe, Untested)

**Agent**: "Do research"
**Goal**: Unclear
**Tools**: Everything (no constraints)
**Guardrails**: None
**Fallbacks**: None
**Evaluation**: "Seems to work"
**Result**: Fails unpredictably; unsafe; expensive

## Common Mistakes (3+)

1. **Over-Ambitious Goal**: Agent tries to do too much (research + summarize + critique + recommend + publish). Break into smaller agents or sequential tasks.

2. **Insufficient Guardrails**: Agent has no constraints; uses expensive tools liberally; makes up data. Add guardrails *before* deploying.

3. **No Fallback Planning**: Agent hits edge case (tool failure, no results, etc.); returns garbage or error. Plan fallbacks for every edge case.

4. **Insufficient Testing**: You test on 2 examples, assume it works, deploy. Then it fails on real queries. Create test suite of 20-50 representative queries.

5. **No Monitoring**: Agent deployed; you don't track success rate, cost, or hallucination. One month later, it's quietly failing 20% of queries. Add logging/monitoring day 1.

## Anti-Patterns (3+)

1. **Agentic Spiral**: Agent gets stuck in a loop (searches same query, fetches same page repeatedly). Add loop detection; break if repeating.

2. **Hallucination Blindness**: Agent makes up facts; users cite agent as source; spreads misinformation. Test explicitly for hallucination; add "cite source" requirements.

3. **Cost Explosion**: Agent starts at $0.05 cost/query. Months later, costs $5/query due to agent learning bad strategies. Monitor cost trends weekly.

4. **No Human Loop**: Agent recommends critical actions without human review. Add human approval for high-stakes decisions.

---

**Next Steps**: Define your agent goal. Identify 2-3 sub-tasks. List required tools. Add 5 guardrails. Test on 10 representative queries. Evaluate success rate, cost, and hallucination. Improve.
