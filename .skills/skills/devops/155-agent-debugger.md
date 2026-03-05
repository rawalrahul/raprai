---
name: agent-debugger
description: "Debug AI agents by analyzing execution traces, tool calls, memory operations, and token usage to identify loops, hallucinations, and failures"
category: devops
difficulty: advanced
model_boost: "Weak models blame 'hallucinations' generically without systematic analysis. This skill provides frameworks to identify root causes: wrong tool selection, context overflow, infinite retries, stale memory."
---

# AI Agent Debugger

## Purpose
This skill teaches you to debug AI agents systematically by analyzing execution traces instead of guessing. When an agent fails, most developers either rerun it (hoping it works) or add random constraints ("be more careful"). This skill provides a methodology to trace exactly where the agent went wrong: Did it call the wrong tool? Did context overflow? Did it loop infinitely? Did it misread output? You'll learn to profile token usage, identify failure patterns, evaluate alternatives, and implement fixes with confidence. A well-debugged agent is a reliable agent.

## When to Use
- An agent consistently fails on a task (not one-off errors)
- You want to reduce token usage without sacrificing performance
- You're integrating agent outputs into production systems
- You need to understand why an agent chose specific tools/actions
- **Do NOT use when**: You're testing a minor prompt tweak (use A/B testing); debugging a single user's isolated issue (may be ephemeral); the agent works fine most of the time (focus on reliability first)

## Instructions

### Step 1: Capture Complete Execution Traces
You need full visibility into agent execution. Depending on your framework:

**LangChain (Python):**
```python
from langchain.callbacks import StdOutCallbackHandler
from langchain.callbacks.manager import CallbackManager
import json

# Capture detailed callbacks
class AgentTracer:
    def __init__(self):
        self.trace = {
            'tool_calls': [],
            'inputs': [],
            'outputs': [],
            'errors': [],
            'tokens': {'total': 0, 'input': 0, 'output': 0}
        }

    def trace_tool_call(self, tool_name, input_args, output, duration_ms):
        self.trace['tool_calls'].append({
            'tool': tool_name,
            'input': input_args,
            'output': output,
            'duration_ms': duration_ms,
            'timestamp': datetime.now().isoformat()
        })

    def dump(self, filename='trace.json'):
        with open(filename, 'w') as f:
            json.dump(self.trace, f, indent=2)

# Use with agent
tracer = AgentTracer()

# Instrument LangChain callbacks
callback_handler = StdOutCallbackHandler()

# Wrap tool calls to capture inputs/outputs
original_tool_run = agent.tools[0].run

def traced_run(*args, **kwargs):
    start = time.time()
    try:
        result = original_tool_run(*args, **kwargs)
        tracer.trace_tool_call(
            tool_name=agent.tools[0].name,
            input_args={'args': args, 'kwargs': kwargs},
            output=result,
            duration_ms=(time.time() - start) * 1000
        )
        return result
    except Exception as e:
        tracer.trace['errors'].append({
            'tool': agent.tools[0].name,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        raise

agent.tools[0].run = traced_run

# Run agent
result = agent.run("Your task here")
tracer.dump()
```

**LangGraph (Python):**
```python
from langgraph.graph import StateGraph
from typing import Any, Dict, List

class DebugState(TypedDict):
    messages: List[dict]
    trace: Dict[str, Any]  # Add trace to state

def create_debug_graph():
    graph = StateGraph(DebugState)

    # Instrument nodes to capture state transitions
    def agent_node(state):
        # Existing agent logic
        ...
        # Capture before/after state
        if 'trace' not in state:
            state['trace'] = {'nodes': [], 'decisions': []}

        state['trace']['nodes'].append({
            'node': 'agent',
            'input_tokens': count_tokens(state['messages']),
            'output': result,
            'timestamp': datetime.now().isoformat()
        })

        return state

    graph.add_node("agent", agent_node)
    # ... rest of graph construction
    return graph

graph = create_debug_graph()
result = graph.invoke({"messages": [...]})
trace = result['trace']
```

**Custom agent (most transparent):**
```python
class DebugAgent:
    def __init__(self, model, tools, trace_file='agent_trace.json'):
        self.model = model
        self.tools = {t.name: t for t in tools}
        self.trace = {
            'steps': [],
            'total_tokens': 0,
            'errors': [],
            'tool_calls': []
        }
        self.trace_file = trace_file

    def run(self, task):
        messages = [{"role": "user", "content": task}]
        step_num = 0

        while step_num < 20:  # Max iterations to prevent infinite loops
            step_num += 1

            # Get agent decision
            response = self.model.call(
                messages=messages,
                tools=[{
                    'name': name,
                    'description': tool.description,
                    'input_schema': tool.schema
                } for name, tool in self.tools.items()]
            )

            # Record step
            self.trace['steps'].append({
                'step': step_num,
                'agent_request': len(messages),  # Context length
                'agent_response': response.content,
                'tokens': response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0,
                'tool_calls': getattr(response, 'tool_calls', [])
            })
            self.trace['total_tokens'] += response.usage.total_tokens

            # Parse tool calls
            if not response.tool_calls:
                # Final response
                self.trace['final_answer'] = response.content
                break

            # Execute tools
            for tool_call in response.tool_calls:
                tool_name = tool_call.name
                tool_input = tool_call.args

                try:
                    tool_result = self.tools[tool_name].run(**tool_input)

                    self.trace['tool_calls'].append({
                        'step': step_num,
                        'tool': tool_name,
                        'input': tool_input,
                        'output': tool_result,
                        'success': True
                    })

                    # Add to messages for next iteration
                    messages.append({
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Tool result: {tool_result}"
                    })

                except Exception as e:
                    self.trace['errors'].append({
                        'step': step_num,
                        'tool': tool_name,
                        'error': str(e),
                        'input': tool_input
                    })
                    messages.append({
                        "role": "user",
                        "content": f"Tool error: {str(e)}"
                    })

            if step_num >= 20:
                self.trace['errors'].append({'type': 'max_iterations_exceeded'})
                break

        # Dump trace
        with open(self.trace_file, 'w') as f:
            json.dump(self.trace, f, indent=2)

        return self.trace['final_answer']

# Usage
agent = DebugAgent(model=claude, tools=[db_query, api_call])
result = agent.run("Fetch user data and summarize trends")
# Trace is automatically dumped to agent_trace.json
```

### Step 2: Analyze Trace for Failure Patterns
Once you have the trace, look for these patterns:

**Pattern 1: Infinite Retries**
```json
{
  "steps": [
    {"step": 1, "tool": "search", "input": "Python best practices", "output": "200 results"},
    {"step": 2, "tool": "search", "input": "Python best practices", "output": "200 results"},
    {"step": 3, "tool": "search", "input": "Python best practices", "output": "200 results"}
  ],
  "total_tokens": 50000
}
```

**Diagnosis:** Agent is stuck in a loop calling the same tool with the same input.
- **Cause A:** Tool didn't return what agent expected (agent doesn't know how to interpret result)
- **Cause B:** Agent's instruction is ambiguous ("research until you're confident")—never terminates
- **Cause C:** Tool output is identical every time, agent doesn't learn anything new

**Fix:**
```python
# Limit retries per tool
tool_call_counts = {}
if tool_name in tool_call_counts:
    tool_call_counts[tool_name] += 1
    if tool_call_counts[tool_name] > 2:  # Only call search twice max
        messages.append({
            "role": "user",
            "content": f"Search tool called 3 times with similar input. Use results from previous calls or try a different approach."
        })
        continue
```

**Pattern 2: Wrong Tool Selection**
```json
{
  "tool_calls": [
    {"step": 1, "tool": "web_search", "context": "Need to query company database"},
    {"step": 2, "tool": "web_search", "context": "Need recent transaction data"},
    {"step": 3, "tool": "web_search", "context": "Need user account details"}
  ]
}
```

**Diagnosis:** Agent has better tools available but keeps using the wrong one.
- **Cause A:** Tool descriptions are weak or missing (agent doesn't know what they do)
- **Cause B:** Agent instruction doesn't mention available tools clearly
- **Cause C:** Web search seemed to work on task 1, agent assumes it solves everything

**Fix:**
```python
# Provide tool descriptions with examples
tools_description = """
Available tools:

1. database_query(sql: str) -> JSON
   Use ONLY for internal data (users, transactions, accounts).
   Example: database_query("SELECT * FROM users WHERE id = 123")

2. web_search(query: str) -> str
   Use ONLY for external information (news, public APIs).
   Example: web_search("latest Python 3.12 features")

3. internal_api(endpoint: str, params: dict) -> JSON
   Use for company APIs (auth required, fast).
   Example: internal_api("/api/reports", {"date_range": "last_30_days"})

IMPORTANT: database_query and internal_api are faster and more reliable for company data.
Only use web_search if you need external information.
"""

# Include in system prompt
system_prompt = f"{base_prompt}\n\n{tools_description}"
```

**Pattern 3: Context Overflow**
```json
{
  "steps": [
    {"step": 1, "token_count": 2000},
    {"step": 2, "token_count": 4000},
    {"step": 3, "token_count": 7000},
    {"step": 4, "token_count": 10000, "error": "context_length_exceeded"}
  ]
}
```

**Diagnosis:** Token count grows with each step, eventually hitting limit.
- **Cause A:** Agent appends all previous messages (memory leak)
- **Cause B:** Tool outputs are massive (raw database dump instead of summary)
- **Cause C:** No summary/compression of old steps

**Fix:**
```python
# Implement message compression
def compress_old_messages(messages, keep_recent=5):
    """Keep last N messages, summarize earlier ones."""
    if len(messages) <= keep_recent:
        return messages

    old_messages = messages[:-keep_recent]
    new_messages = messages[-keep_recent:]

    # Summarize old messages
    summary = f"Earlier conversation summary:\n"
    for msg in old_messages:
        if msg['role'] == 'assistant':
            summary += f"- Agent decided to call tool\n"
        else:
            summary += f"- Tool returned: {msg['content'][:100]}...\n"

    return [
        {"role": "user", "content": summary},
        *new_messages
    ]

# Apply before each call
messages = compress_old_messages(messages)
response = model.call(messages)
```

**Pattern 4: Hallucinated Tool Calls**
```json
{
  "tool_calls": [
    {"step": 1, "tool": "calculate_route"},
    {"step": 2, "tool": "send_sms"},
    {"step": 3, "tool": "book_flight"}
  ],
  "errors": [
    "Tool 'calculate_route' not found",
    "Tool 'send_sms' not found",
    "Tool 'book_flight' not found"
  ]
}
```

**Diagnosis:** Agent invents tools that don't exist.
- **Cause A:** Model was trained on fictional tool APIs
- **Cause B:** Tool list wasn't provided clearly in prompt
- **Cause C:** Agent wasn't given permission to skip a subtask

**Fix:**
```python
# Explicit tool list in system prompt
available_tools = """
TOOLS YOU CAN USE:
1. get_user_profile(user_id: str) -> dict
2. query_database(table: str, filter: dict) -> list[dict]
3. send_email(to: str, subject: str, body: str) -> bool

You CANNOT use tools that aren't in this list. If a task requires a tool you don't have,
tell the user clearly: "I don't have access to [tool_name]. I can help by [alternative]."
"""

# Validate before execution
allowed_tool_names = set(t.name for t in tools)

for tool_call in response.tool_calls:
    if tool_call.name not in allowed_tool_names:
        messages.append({
            "role": "user",
            "content": f"Error: Tool '{tool_call.name}' doesn't exist. Available tools: {list(allowed_tool_names)}"
        })
        continue
```

### Step 3: Profile Token Usage
Understand where tokens are spent:

```python
def analyze_token_usage(trace):
    """Break down token usage by component."""
    usage = {
        'system_prompt': count_tokens(system_prompt),
        'tool_descriptions': count_tokens(tools_description),
        'user_input': 0,
        'tool_outputs': 0,
        'agent_responses': 0,
        'total': 0
    }

    for step in trace['steps']:
        if 'input_tokens' in step:
            usage['user_input'] += step['input_tokens']
        if 'tool_response' in step:
            usage['tool_outputs'] += count_tokens(step['tool_response'])
        if 'agent_output' in step:
            usage['agent_responses'] += count_tokens(step['agent_output'])

    usage['total'] = sum(v for k, v in usage.items() if k != 'total')

    # Print breakdown
    print("Token Usage Breakdown:")
    for component, tokens in usage.items():
        pct = (tokens / usage['total'] * 100) if usage['total'] > 0 else 0
        print(f"  {component}: {tokens:,} ({pct:.1f}%)")

    return usage

# Usage
usage = analyze_token_usage(trace)
# Token Usage Breakdown:
#   system_prompt: 500 (2.5%)
#   tool_descriptions: 800 (4%)
#   user_input: 1000 (5%)
#   tool_outputs: 12000 (60%)  ← TOO HIGH, compress or filter
#   agent_responses: 6000 (30%)
#   total: 20,300
```

**Common optimizations:**
- **Tool outputs too large?** Add `max_results=5` or `summarize=true` to tool calls
- **System prompt too long?** Move examples to few-shot in task prompt
- **Agent responses verbose?** Add constraint: "Keep responses under 100 words"

### Step 4: Implement Root Cause Analysis Framework
Create a systematic diagnosis checklist:

```python
def diagnose_failure(trace, failed_task):
    """Root cause analysis for agent failure."""

    diagnosis = {
        'task': failed_task,
        'trace_length': len(trace['steps']),
        'issues': [],
        'recommendations': []
    }

    # Check 1: Did it loop?
    if trace['total_tokens'] > 50000:
        diagnosis['issues'].append('HIGH_TOKEN_USAGE')
        diagnosis['recommendations'].append('Add step limit or message compression')

    # Check 2: Did it use wrong tools?
    tool_calls_per_tool = {}
    for call in trace['tool_calls']:
        tool = call['tool']
        tool_calls_per_tool[tool] = tool_calls_per_tool.get(tool, 0) + 1

    repeated_tools = {t: c for t, c in tool_calls_per_tool.items() if c > 3}
    if repeated_tools:
        diagnosis['issues'].append(f'REPEATED_TOOL_CALLS: {repeated_tools}')
        diagnosis['recommendations'].append('Improve tool descriptions or agent instruction')

    # Check 3: Did tools fail?
    error_rate = len(trace['errors']) / len(trace['tool_calls']) if trace['tool_calls'] else 0
    if error_rate > 0.3:
        diagnosis['issues'].append(f'HIGH_ERROR_RATE: {error_rate:.1%}')
        diagnosis['recommendations'].append('Fix tool implementation or error handling')

    # Check 4: Did agent hit iteration limit?
    if trace['steps'][-1].get('error') == 'max_iterations_exceeded':
        diagnosis['issues'].append('ITERATION_LIMIT_HIT')
        diagnosis['recommendations'].append('Agent couldn\'t finish task. Check for loops or ambiguous instructions.')

    # Check 5: Did context overflow?
    if any('context_length' in str(e) for e in trace['errors']):
        diagnosis['issues'].append('CONTEXT_OVERFLOW')
        diagnosis['recommendations'].append('Compress messages or limit tool output')

    return diagnosis

# Usage
diagnosis = diagnose_failure(agent.trace, "Find users who purchased in last 7 days")
print(f"Issues: {diagnosis['issues']}")
print(f"Fixes: {diagnosis['recommendations']}")
```

### Step 5: Test Fixes Incrementally
Don't change everything at once. Use A/B testing:

```python
def compare_agents(task, n_trials=5):
    """Compare original vs fixed agent."""

    results = {
        'original': {'successes': 0, 'avg_tokens': 0, 'errors': []},
        'fixed': {'successes': 0, 'avg_tokens': 0, 'errors': []}
    }

    for trial in range(n_trials):
        # Original agent
        orig_trace = original_agent.run(task)
        if orig_trace.get('final_answer'):
            results['original']['successes'] += 1
        results['original']['avg_tokens'] += orig_trace['total_tokens']
        results['original']['errors'].extend(orig_trace['errors'])

        # Fixed agent
        fixed_trace = fixed_agent.run(task)
        if fixed_trace.get('final_answer'):
            results['fixed']['successes'] += 1
        results['fixed']['avg_tokens'] += fixed_trace['total_tokens']
        results['fixed']['errors'].extend(fixed_trace['errors'])

    # Normalize
    results['original']['avg_tokens'] /= n_trials
    results['fixed']['avg_tokens'] /= n_trials

    print(f"Original: {results['original']['successes']}/{n_trials} successes, {results['original']['avg_tokens']:.0f} tokens/run")
    print(f"Fixed: {results['fixed']['successes']}/{n_trials} successes, {results['fixed']['avg_tokens']:.0f} tokens/run")
    print(f"Improvement: {(results['original']['successes'] - results['fixed']['successes'])} more successes, {(results['original']['avg_tokens'] - results['fixed']['avg_tokens']):.0f} fewer tokens")

    return results

# Usage
compare_agents("Summarize Q3 sales for tech sector")
# Original: 3/5 successes, 18500 tokens/run
# Fixed: 5/5 successes, 9200 tokens/run
# Improvement: 2 more successes, 9300 fewer tokens
```

### Step 6: Document Debugging Results
Create a runbook for future issues:

```yaml
# AGENT_RUNBOOK.md

## Issue: Agent calls web_search for internal data

### Symptoms
- 5+ failed runs on database queries
- Error: "Web search returned unrelated results"
- Token usage: 30K+ per run

### Root Cause
Agent didn't understand internal_api tool existed.
Tool descriptions were ambiguous.

### Fix Applied
1. Added "Use internal_api for company data" to system prompt
2. Provided example: `internal_api("/api/users", {"filter": "premium"})`
3. Added: "internal_api is 10x faster than web search"

### Verification
- A/B test: 5/5 runs succeeded with fixed agent
- Token reduction: 30K → 8K tokens
- No false web searches

### Prevention
- Always include examples in tool descriptions
- Highlight which tool is best for which task
- Test with 5+ diverse prompts before deployment
```

### Step 7: Monitor Production Agents
Implement telemetry in production:

```python
class ProductionAgent:
    def __init__(self, model, tools):
        self.model = model
        self.tools = tools
        self.metrics = {
            'runs': 0,
            'successes': 0,
            'failures': 0,
            'avg_tokens': 0,
            'avg_duration_ms': 0,
            'tool_error_rate': {}
        }

    def run_with_monitoring(self, task, user_id=None):
        """Run agent and collect metrics."""
        start = time.time()

        try:
            result = self.run(task)
            self.metrics['successes'] += 1
            return result

        except Exception as e:
            self.metrics['failures'] += 1
            # Send to error tracking (Sentry, DataDog, etc.)
            logger.error(f"Agent failed for user {user_id}: {str(e)}")
            raise

        finally:
            self.metrics['runs'] += 1
            duration = (time.time() - start) * 1000
            self.metrics['avg_duration_ms'] = (
                (self.metrics['avg_duration_ms'] * (self.metrics['runs'] - 1) + duration) /
                self.metrics['runs']
            )

    def get_health_check(self):
        """Return agent health metrics."""
        return {
            'success_rate': self.metrics['successes'] / max(1, self.metrics['runs']),
            'avg_duration_ms': self.metrics['avg_duration_ms'],
            'total_runs': self.metrics['runs'],
            'failures': self.metrics['failures']
        }

# Usage
agent = ProductionAgent(model, tools)

# Every hour, check health
health = agent.get_health_check()
if health['success_rate'] < 0.9:
    alert("Agent success rate below 90%")
```

### Step 8: Create Runnable Debug Artifacts
For complex issues, create minimal reproducers:

```python
# debug_agent.py - Standalone reproduction

import json
from datetime import datetime

# Minimal agent
class DebugAgent:
    def __init__(self, model, tools):
        self.model = model
        self.tools = tools

    def run_with_trace(self, task):
        trace = {'steps': []}
        messages = [{"role": "user", "content": task}]

        for step in range(10):
            response = self.model.call(messages)
            trace['steps'].append({
                'step': step + 1,
                'response': response.content,
                'tool_calls': getattr(response, 'tool_calls', [])
            })

            if not response.tool_calls:
                break

            for call in response.tool_calls:
                result = self.tools[call.name](**call.args)
                messages.append({"role": "user", "content": f"Tool result: {result}"})

        with open('debug_trace.json', 'w') as f:
            json.dump(trace, f, indent=2)

        return trace

# Test
if __name__ == "__main__":
    agent = DebugAgent(model, tools)
    trace = agent.run_with_trace("Your failing task here")
    print(json.dumps(trace, indent=2))
```

## Output Template

A complete debugging session produces:

```
/debug/
├── trace.json                 (full execution trace)
├── diagnosis.md               (root cause analysis)
├── token_analysis.txt         (token breakdown)
├── comparison_results.txt     (A/B test results)
├── runbook.md                 (fix documentation)
└── debug_agent.py             (minimal reproducer)
```

Each artifact should include:
- Issue description and symptoms
- Root cause analysis (not assumptions)
- Trace evidence (tool calls, errors, tokens)
- Fixes applied (with before/after metrics)
- Prevention strategy (how to detect this in future)

## Quality Gates
- [ ] Trace captures all tool calls, inputs, and outputs
- [ ] Diagnosis identifies specific root cause (not vague)
- [ ] Token usage is analyzed and optimized (>20% reduction or shows why not possible)
- [ ] A/B test shows measurable improvement (success rate, tokens, latency)
- [ ] Runbook documents the issue and fix for team reference
- [ ] Agent passes at least 5 test cases with fixed version
- [ ] No new issues introduced (regressions checked)

## Examples

### Good Output (excerpt)
```json
{
  "issue": "Agent loops calling web_search",
  "root_cause": "Tool description too vague, agent didn't know about database_query",
  "evidence": {
    "tool_calls": [
      {"step": 1, "tool": "web_search", "input": "User purchase history"},
      {"step": 2, "tool": "web_search", "input": "User purchase history"},
      {"step": 3, "tool": "web_search", "input": "User purchase history"}
    ],
    "total_tokens": 45000,
    "errors": ["Web search returned news articles, not user data"]
  },
  "fix": "Added database_query to tool list with example: 'database_query(\"SELECT * FROM orders WHERE user_id = 123\")'",
  "verification": {
    "before": "2/5 runs succeeded, 45K tokens",
    "after": "5/5 runs succeeded, 8K tokens",
    "improvement": "+3 successes, -37K tokens"
  }
}
```
✓ Specific root cause ✓ Evidence from trace ✓ Measured improvement

### Bad Output (what to avoid)
```
Issue: Agent sometimes fails
Cause: Hallucination
Fix: Try better prompt
Results: Seems better now
```
✗ Vague issue ✗ No evidence ✗ No metrics ✗ Unrepeatable

## Common Mistakes

1. **Mistake:** Attributing all failures to "hallucinations" → **Fix:** Analyze the trace. Is it tool choice, context overflow, or something else?

2. **Mistake:** Changing multiple things at once → **Fix:** Fix one issue at a time and A/B test. You won't know what worked.

3. **Mistake:** Not measuring improvement → **Fix:** Run 5+ trials before/after. Success rate and token count must improve.

4. **Mistake:** Ignoring token cost → **Fix:** Optimize token usage alongside success rate. A slower, expensive agent isn't a win.

5. **Mistake:** Not documenting fixes → **Fix:** Create a runbook. Next issue will be faster to debug.

6. **Mistake:** Tweaking prompt randomly → **Fix:** Use traces to diagnose. Prompt changes should target specific root causes.

## Anti-Patterns

- Never debug without a full trace (you're guessing)
- Never claim success without A/B testing (improvement might be random)
- Never ignore tool descriptions (weak descriptions cause wrong tool selection)
- Never set iteration limits without understanding the task (some tasks legitimately need 10+ steps)
- Never compress all old messages into one (agent loses conversation thread, makes mistakes)
