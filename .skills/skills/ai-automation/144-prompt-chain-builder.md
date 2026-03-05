---
name: prompt-chain-builder
description: "Build multi-step prompt chains with task decomposition, input/output contracts, variable passing, validation gates, branching logic, error handling, and cost tracking. Design chains for research-to-summary-to-write workflows."
category: ai-automation
difficulty: intermediate
model_boost: "Fixes single-prompt approaches that fail on complex tasks; enables step-wise decomposition with validation and cost control"
---

# Prompt Chain Builder

## Purpose
This skill teaches you to design multi-step AI workflows that break complex tasks into atomic steps, pass outputs between steps, validate intermediate results, branch on conditions, and track costs. You'll learn to construct chains for tasks like research→summarize→write, extract→validate→transform, and escalate→analyze→report. The output is a production-ready chain system with error handling, monitoring, and cost optimization.

## When to Use
- Tasks requiring 3+ sequential AI steps
- Complex reasoning tasks decomposed into substeps
- Workflows needing validation/approval gates between steps
- Multi-stage transformation pipelines (extract → normalize → validate)
- Cost-sensitive workflows requiring per-step optimization
- **Do NOT use when**: Single-step tasks, real-time streaming, or simple prompt completions

## Instructions

### Step 1: Task Decomposition and Step Definition
Break complex tasks into atomic, reusable steps.

**Decomposition Patterns**:

**Pattern 1: Sequential Linear Chain**
```
Input → Step1 → Step2 → Step3 → Output
(Each step's output becomes next step's input)

Example: Content Creation
Input: Topic "AI Safety"
  ↓
Step 1: Research (retrieve facts, statistics)
  ↓
Step 2: Outline (create structure)
  ↓
Step 3: Draft (write full article)
  ↓
Step 4: Edit (improve clarity, fix errors)
  ↓
Output: Published article
```

**Pattern 2: Branching Chain**
```
Input
  ↓
Step 1: Classify (what type of request?)
  ├─ Path A: Simple → Direct response
  ├─ Path B: Complex → Multi-step analysis
  └─ Path C: Sensitive → Human escalation

(Different paths based on Step 1 output)
```

**Pattern 3: Parallel Steps + Merge**
```
Input
  ├─→ Step 1A: Fetch user context (parallel)
  ├─→ Step 1B: Retrieve documents (parallel)
  └─→ Step 1C: Classify intent (parallel)
  ↓ (wait for all to complete)
Step 2: Merge results → synthesized context
  ↓
Output: Final response
```

**Pattern 4: Loop / Iterative Refinement**
```
Input
  ↓
Step 1: Generate (first draft)
  ↓
Step 2: Evaluate (check quality)
  ├─ Quality >= threshold? → Output
  └─ Quality < threshold? → Refine (loop back)
```

**Step Definition Template**:
```yaml
step:
  id: research_facts
  description: "Retrieve and verify facts for the given topic"
  inputs:
    topic: string (e.g., "AI Safety")
    max_sources: int (default: 5)
  outputs:
    facts: list[{fact: string, source: string, confidence: 0.0-1.0}]
    total_cost: float
  model_config:
    model: "gpt-4"
    temperature: 0.3 (lower = factual, deterministic)
    max_tokens: 2000
  error_handling:
    on_invalid_input: "Return empty facts list with error message"
    on_api_failure: "Retry 3x with exponential backoff"
    on_low_confidence: "Flag for human review"
  validation:
    output_schema: "facts must be list of dicts with required keys"
    expected_runtime: "2-5 seconds"
  cost_estimate:
    input_tokens: 500 (average)
    output_tokens: 1000 (average)
    cost_usd: 0.03
```

### Step 2: Input/Output Contracts Between Steps
Define explicit interfaces to avoid data format mismatches.

**Contract Definition**:
```python
from typing import TypedDict, Literal
from dataclasses import dataclass

# Step 1: Research → Output contract
class ResearchOutput(TypedDict):
    facts: list[dict]  # Each dict: {fact, source, confidence}
    total_sources_searched: int
    confidence_score: float  # Overall confidence (0-1)
    cost_usd: float

# Step 2: Outline → Input contract (must match Step 1 output)
class OutlineInput(TypedDict):
    facts: list[dict]  # Must match ResearchOutput.facts
    # Add any additional inputs specific to Outline
    tone: Literal["academic", "casual", "technical"]
    section_count: int  # How many sections to outline

# Outline → Output contract
class OutlineOutput(TypedDict):
    sections: list[{title: str, key_points: list[str]}]
    word_count_estimate: int
    cost_usd: float

# Step 3: Draft → Input contract
class DraftInput(TypedDict):
    outline: list[dict]  # Must match OutlineOutput.sections
    facts: list[dict]  # Pass facts forward for citations
    tone: Literal["academic", "casual", "technical"]

# Draft → Output contract
class DraftOutput(TypedDict):
    content: str
    word_count: int
    citations: list[str]
    cost_usd: float
```

**Contract Validation**:
```python
def validate_output(output: dict, expected_schema: TypedDict) -> tuple[bool, list[str]]:
    """Validate step output matches expected schema"""
    errors = []

    for field, expected_type in expected_schema.__annotations__.items():
        if field not in output:
            errors.append(f"Missing required field: {field}")
            continue

        actual_value = output[field]

        # Type checking
        if not isinstance(actual_value, expected_type):
            errors.append(
                f"Field '{field}' has wrong type: "
                f"expected {expected_type}, got {type(actual_value)}"
            )

    return len(errors) == 0, errors

# Usage:
research_output = {"facts": [...], "total_sources": 5, "cost_usd": 0.03}
is_valid, errors = validate_output(research_output, ResearchOutput)
if not is_valid:
    raise ValueError(f"Invalid output: {errors}")
```

### Step 3: Variable Passing and Template Rendering
Transport data between steps using clean templating.

**Variable Passing Patterns**:

**Pattern 1: Direct Pass-Through**
```python
# Step 1: Research
research_output = await research_step(topic="AI Safety")
facts = research_output["facts"]
sources = research_output["total_sources"]

# Step 2: Outline (receive Step 1 outputs)
outline_output = await outline_step(
    facts=facts,
    sources=sources,
    tone="academic"
)
```

**Pattern 2: Template Rendering** (populate variables into prompt)
```python
# Define template with {variables}
outline_template = """
Based on the following {fact_count} facts about {topic}:

{facts_formatted}

Create a {section_count}-section outline for an {tone} article.
Each section should have 3-5 key points.

Outline:
"""

# Render template with actual values
facts_formatted = "\n".join([
    f"- {fact['fact']} (Source: {fact['source']})"
    for fact in facts
])

prompt = outline_template.format(
    fact_count=len(facts),
    topic="AI Safety",
    facts_formatted=facts_formatted,
    section_count=5,
    tone="academic"
)

outline_output = await call_model(prompt)
```

**Pattern 3: Context Manager** (thread context through chain)
```python
class ChainContext:
    """Holds state for entire chain execution"""
    def __init__(self):
        self.variables = {}
        self.step_outputs = {}
        self.total_cost = 0.0
        self.execution_log = []

    def set(self, key: str, value: any):
        self.variables[key] = value

    def get(self, key: str) -> any:
        return self.variables.get(key)

    def add_step_result(self, step_name: str, output: dict, cost: float):
        self.step_outputs[step_name] = output
        self.total_cost += cost
        self.execution_log.append({
            "step": step_name,
            "timestamp": now(),
            "cost": cost
        })

async def execute_chain(topic: str):
    ctx = ChainContext()
    ctx.set("topic", topic)

    # Step 1: Research
    research_output = await research_step(topic=ctx.get("topic"))
    ctx.add_step_result("research", research_output, cost=0.03)

    # Step 2: Outline (pull from context)
    outline_output = await outline_step(
        facts=ctx.step_outputs["research"]["facts"],
        topic=ctx.get("topic")
    )
    ctx.add_step_result("outline", outline_output, cost=0.02)

    # Step 3: Draft (pull from context)
    draft_output = await draft_step(
        outline=ctx.step_outputs["outline"]["sections"],
        facts=ctx.step_outputs["research"]["facts"]
    )
    ctx.add_step_result("draft", draft_output, cost=0.05)

    print(f"Total chain cost: ${ctx.total_cost:.2f}")
    return draft_output
```

### Step 4: Validation Gates and Quality Checkpoints
Verify intermediate outputs before passing to next step.

**Validation Gate Types**:

**Gate 1: Schema Validation** (structural)
```python
class ValidationGate:
    async def validate(self, output: dict, schema: TypedDict) -> tuple[bool, str]:
        """Check output structure"""
        is_valid, errors = validate_output(output, schema)
        if not is_valid:
            return False, f"Schema validation failed: {errors}"
        return True, "OK"

# Usage in chain:
research_output = await research_step(...)
is_valid, msg = await validation_gate.validate(research_output, ResearchOutput)
if not is_valid:
    # Fallback: Use default facts or escalate
    research_output = {"facts": [], "cost_usd": 0}
```

**Gate 2: Quality Validation** (semantic)
```python
class QualityGate:
    async def validate_facts(self, facts: list[dict]) -> tuple[bool, str]:
        """Check fact quality: non-empty, high confidence"""
        if len(facts) == 0:
            return False, "No facts retrieved"

        avg_confidence = sum(f["confidence"] for f in facts) / len(facts)
        if avg_confidence < 0.7:
            return False, f"Low confidence: {avg_confidence:.2f}"

        return True, "OK"

    async def validate_outline(self, outline: list[dict]) -> tuple[bool, str]:
        """Check outline completeness"""
        if len(outline) < 3:
            return False, "Too few sections"

        for section in outline:
            if len(section.get("key_points", [])) < 2:
                return False, f"Section '{section['title']}' has too few key points"

        return True, "OK"

# Usage:
is_valid, msg = await quality_gate.validate_facts(research_output["facts"])
if not is_valid:
    # Escalate for human review
    await escalate_to_human(research_output, reason=msg)
```

**Gate 3: Conditional Validation** (pass if condition met)
```python
async def conditional_gate(output: dict, condition_func) -> bool:
    """Validate based on custom condition"""
    if condition_func(output):
        return True

    # Condition failed; take action
    return False

# Usage:
is_valid = await conditional_gate(
    draft_output,
    condition_func=lambda x: len(x["content"]) > 1000  # Minimum 1000 words
)
if not is_valid:
    # Retry with higher word count request
    draft_output = await draft_step(word_count_target=2000)
```

**Implementing Gates in Chain**:
```python
async def execute_chain_with_gates(topic: str):
    ctx = ChainContext()

    # Step 1: Research + Gate
    research_output = await research_step(topic)
    is_valid, msg = await quality_gate.validate_facts(research_output["facts"])
    if not is_valid:
        print(f"Research gate failed: {msg}. Retrying with different query...")
        research_output = await research_step(topic, num_sources=10)  # Retry

    ctx.add_step_result("research", research_output, cost=0.03)

    # Step 2: Outline + Gate
    outline_output = await outline_step(facts=research_output["facts"])
    is_valid, msg = await quality_gate.validate_outline(outline_output["sections"])
    if not is_valid:
        print(f"Outline gate failed: {msg}")
        return {"error": msg, "status": "failed_at_outline"}

    ctx.add_step_result("outline", outline_output, cost=0.02)

    # Step 3: Draft
    draft_output = await draft_step(outline=outline_output["sections"])
    return draft_output
```

### Step 5: Branching Logic (Conditional Routing)
Route execution based on intermediate outputs.

**Branching Patterns**:

**Pattern 1: If/Else Based on Classification**
```python
async def execute_with_branching(user_input: str):
    ctx = ChainContext()

    # Step 1: Classify request complexity
    classification = await classify_step(user_input)
    complexity = classification["complexity"]  # "simple" | "medium" | "complex"

    ctx.set("complexity", complexity)

    # Branch based on complexity
    if complexity == "simple":
        # Path A: Direct response
        response = await simple_response_step(user_input)

    elif complexity == "medium":
        # Path B: Analyze + respond
        analysis = await analyze_step(user_input)
        response = await detailed_response_step(user_input, analysis)

    else:  # complexity == "complex"
        # Path C: Research → Analysis → Response
        research = await research_step(user_input)
        analysis = await analyze_step(research)
        response = await comprehensive_response_step(research, analysis)

    return response
```

**Pattern 2: Conditional Chain Continuation**
```python
async def execute_with_conditional_continuation(topic: str):
    # Step 1: Research
    facts = await research_step(topic)

    # Check quality gate
    if len(facts) < 5:
        # Low fact coverage; take different path
        print("Low coverage, using Wikipedia as fallback")
        facts = await fetch_from_wikipedia(topic)
        skip_verify_step = True
    else:
        skip_verify_step = False

    # Step 2: Verify (conditional)
    if not skip_verify_step:
        verified_facts = await verify_facts_step(facts)
    else:
        verified_facts = facts

    # Continue with rest of chain
    outline = await outline_step(verified_facts)
    return outline
```

**Pattern 3: Error Recovery Branching**
```python
async def execute_with_error_recovery(topic: str):
    try:
        # Primary path
        facts = await research_step(topic)
        outline = await outline_step(facts)
        return outline

    except APIError as e:
        print(f"API error: {e}. Using fallback path...")
        # Fallback: Use cached data
        facts = await get_cached_facts(topic)
        if facts:
            outline = await outline_step(facts)
            return outline
        else:
            # Double fallback: Simple outline without facts
            return await simple_outline_step(topic)

    except ValueError as e:
        print(f"Validation error: {e}. Escalating to human...")
        await escalate_to_human(topic, error=str(e))
        return {"status": "escalated", "error": str(e)}
```

### Step 6: Error Handling and Retry Logic
Handle failures gracefully with retries and fallbacks.

**Retry Strategies**:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class StepExecutor:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def execute_with_retry(self, step_func, *args, **kwargs):
        """Execute step with automatic retry"""
        return await step_func(*args, **kwargs)

# Usage:
research_output = await executor.execute_with_retry(
    research_step,
    topic="AI Safety"
)
```

**Error Categorization & Handling**:
```python
class ChainErrorHandler:
    async def handle_step_error(self, step_name: str, error: Exception,
                               ctx: ChainContext) -> dict:
        """Decide how to handle different error types"""

        # Categorize error
        if isinstance(error, RateLimitError):
            # Transient: Retry with backoff
            return await self.retry_with_backoff(step_name, ctx)

        elif isinstance(error, ValidationError):
            # Input invalid: Check input schema, don't retry
            return await self.escalate_to_human(step_name, error, ctx)

        elif isinstance(error, TimeoutError):
            # Transient: Retry with increased timeout
            return await self.retry_with_increased_timeout(step_name, ctx)

        elif isinstance(error, InsufficientTokensError):
            # Structural: Use smaller model or split input
            return await self.use_fallback_model(step_name, ctx)

        else:
            # Unknown: Log and escalate
            return await self.escalate_to_human(step_name, error, ctx)

    async def retry_with_backoff(self, step_name: str, ctx: ChainContext):
        """Retry with exponential backoff"""
        for attempt in range(3):
            try:
                await sleep(2 ** attempt)  # 1s, 2s, 4s
                result = await self.get_step(step_name).execute(ctx)
                return result
            except Exception as e:
                if attempt == 2:
                    raise

    async def use_fallback_model(self, step_name: str, ctx: ChainContext):
        """Use cheaper/faster fallback model"""
        print(f"Primary model failed. Using fallback for {step_name}...")
        fallback_step = self.get_fallback_step(step_name)
        return await fallback_step.execute(ctx)

    async def escalate_to_human(self, step_name: str, error: Exception,
                               ctx: ChainContext):
        """Send to human for manual intervention"""
        escalation = {
            "step_name": step_name,
            "error": str(error),
            "context": ctx.step_outputs,
            "timestamp": now()
        }
        await self.queue_for_human_review(escalation)
        return {"status": "escalated"}
```

### Step 7: Cost Tracking and Estimation
Monitor and predict costs per chain execution.

**Cost Tracking Implementation**:
```python
class CostTracker:
    def __init__(self):
        self.step_costs = {}  # {step_name: [costs]}
        self.total_cost = 0.0

    async def track_step(self, step_name: str, step_func, *args, **kwargs):
        """Execute step and track cost"""
        result = await step_func(*args, **kwargs)

        # Extract cost from result
        cost = result.get("cost_usd", 0.0)
        self.step_costs.setdefault(step_name, []).append(cost)
        self.total_cost += cost

        print(f"Step '{step_name}' cost: ${cost:.4f} (Total: ${self.total_cost:.4f})")

        return result

    def get_cost_summary(self) -> dict:
        """Return cost breakdown"""
        summary = {}
        for step_name, costs in self.step_costs.items():
            summary[step_name] = {
                "calls": len(costs),
                "total": sum(costs),
                "average": sum(costs) / len(costs)
            }
        return summary

# Calculate token costs:
PRICING = {
    "gpt-4": {
        "input": 0.03 / 1000,  # $0.03 per 1K input tokens
        "output": 0.06 / 1000   # $0.06 per 1K output tokens
    },
    "gpt-3.5-turbo": {
        "input": 0.0005 / 1000,
        "output": 0.0015 / 1000
    }
}

def estimate_step_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING[model]
    return (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

# Usage:
cost = estimate_step_cost("gpt-4", input_tokens=500, output_tokens=1000)
print(f"Estimated cost: ${cost:.4f}")
```

**Cost Optimization**:
```python
class CostOptimizer:
    async def choose_model_for_step(self, step_type: str,
                                   input_complexity: float) -> str:
        """Select cheapest model that achieves quality threshold"""

        # High complexity → Use GPT-4
        if input_complexity > 0.8:
            return "gpt-4"

        # Medium complexity → Use GPT-3.5 (10x cheaper)
        elif input_complexity > 0.5:
            return "gpt-3.5-turbo"

        # Low complexity → Use smaller model (100x cheaper)
        else:
            return "gpt-3.5-turbo"

    async def estimate_chain_cost(self, chain_definition: dict) -> float:
        """Estimate total cost for entire chain"""
        total = 0.0

        for step in chain_definition["steps"]:
            estimated_input_tokens = step["expected_input_tokens"]
            estimated_output_tokens = step["expected_output_tokens"]
            model = step["model"]

            cost = estimate_step_cost(model, estimated_input_tokens, estimated_output_tokens)
            total += cost

        return total
```

## Output Template

**Prompt Chain Design Document**:
```markdown
# [Chain Name] Specification

## Chain Overview
[Purpose, use cases, typical execution time]

## Step Definitions
[For each step: description, inputs, outputs, model config, cost estimate]

## Data Flow Diagram
[ASCII diagram showing steps and data passing]

## Input/Output Contracts
[Formal types/schemas for each step boundary]

## Branching Logic
[Conditions for different execution paths]

## Error Handling
[Recovery strategies for each error type]

## Cost Estimation
[Per-step and total chain cost]

## Example Execution
[Walkthrough with real inputs and outputs]
```

## Quality Gates

1. **Contract Validation**: 100% of inter-step data passes schema validation
2. **Gate Success Rate >= 95%**: QA gates pass without fallback
3. **Error Recovery Success >= 90%**: Failures recovered without escalation
4. **Cost within Budget**: Actual cost <= estimated cost × 1.2
5. **Latency Target Met**: Chain completes within expected time
6. **No Data Loss**: All outputs properly persisted
7. **Audit Trail**: Full execution log maintained for debugging

## Examples

### Good Chain: Research → Summarize → Write
```
Step 1: Research (retrieve 5 high-confidence facts)
  Input: {topic: "AI Safety"}
  Output: {facts: [...], avg_confidence: 0.85, cost: $0.03}
  Gate: confidence >= 0.7? ✓

Step 2: Summarize (distill facts to 3-5 key points)
  Input: {facts, topic}
  Output: {summary: "...", key_points: [...], cost: $0.02}
  Gate: word_count < 200? ✓

Step 3: Write (expand to full article)
  Input: {summary, key_points, topic}
  Output: {article: "...", word_count: 2500, citations: [...], cost: $0.05}

Total cost: $0.10 ✓
Total time: 8s ✓
```

## Common Mistakes

1. **No Validation Between Steps**
   - ❌ Step 1 output invalid → Step 2 fails downstream
   - ✓ Validate output before passing to next step

2. **Hidden Assumptions / No Contracts**
   - ❌ Step 1 returns {facts} → Step 2 expects {results}
   - ✓ Define explicit TypedDict contracts

3. **Uncontrolled Cost Spiraling**
   - ❌ No cost tracking → Month-end surprise $500+ bill
   - ✓ Track per-step, set budgets, alert on overage

4. **No Error Recovery / Chain Stops on First Error**
   - ❌ Research step fails → entire chain aborts
   - ✓ Implement fallbacks, use default values, escalate selectively

## Anti-Patterns

1. **Sequential Retry at Chain Level (Not Step Level)**
   - ❌ Entire chain fails → retry from beginning (expensive)
   - ✓ Retry individual step; continue from checkpoint

2. **No Branching / All-or-Nothing Logic**
   - ❌ High-complexity requests go through same 5-step process
   - ✓ Branch early: simple requests skip 3 steps

3. **Passing Raw Data Without Transformation**
   - ❌ Step 1 output → Step 2 input (no cleaning/validation)
   - ✓ Transform between steps: normalize, dedup, enrich
