# Antipatterns: agent_build tasks

Known failure modes to avoid when building or modifying agents.

## AP-001: Missing Error Handling for External APIs
**Symptom:** Agent crashes on API timeout or rate limit — unrecoverable
**Avoid:** Calling external APIs without try/except and retry logic
**Do instead:** Wrap all external calls in error handling; implement exponential backoff for retries

## AP-002: Circular Tool Dependencies
**Symptom:** Agent calls Tool A which calls Tool B which calls Tool A — infinite loop
**Avoid:** Not mapping the dependency graph before wiring tools
**Do instead:** Draw tool dependency graph first; ensure no cycles; add max-depth guard

## AP-003: Wrong Tool for Task
**Symptom:** Using Bash when computer_use needed; using file_read when web_search needed
**Avoid:** Defaulting to familiar tools without checking if a better tool exists
**Do instead:** Review available tools list before designing solution; match tool capability to task need

## AP-004: No Verification Step
**Symptom:** Agent reports "done" but action had no effect
**Avoid:** Ending task execution without verifying the claimed outcome
**Do instead:** Add explicit verification step: file exists, API responded with success, UI shows expected state

## AP-005: State Not Persisted Between Steps
**Symptom:** Agent loses context between tool calls, repeats earlier steps
**Avoid:** Assuming tool call results are remembered without explicitly passing them forward
**Do instead:** Explicitly carry forward key results in the agent's reasoning between steps

## AP-006: Agent Description Too Vague
**Symptom:** Agent triggers on wrong tasks or misses tasks it should handle
**Avoid:** Generic descriptions like "helps with things" or "does tasks"
**Do instead:** Describe exact trigger conditions, input format expected, and output format produced
