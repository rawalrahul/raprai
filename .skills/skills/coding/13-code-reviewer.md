---
name: code-reviewer
description: "Perform deep code reviews identifying bugs, security vulnerabilities, performance issues, style violations, and maintainability problems. Provide severity-ranked findings with concrete fix suggestions and refactored code examples."
category: coding
difficulty: advanced
model_boost: "Weak models miss security issues, suggest vague fixes without examples, and confuse style with substance"
---

# Code Reviewer

## Purpose
Professional code review is not line-by-line grammar checking—it's systematic analysis for correctness, security, performance, and long-term maintainability. This skill provides structured reviews that catch subtle bugs, security anti-patterns, and architectural debt before production. Each finding includes severity, root cause, and refactored code demonstrating the fix.

## When to Use
- Before merging pull requests to identify issues early
- When onboarding code from new team members
- During security hardening sprints
- Before shipping critical paths (auth, payments, data access)
- When code feels "brittle" but you can't articulate why
- **Do NOT use when**: Code is still in exploration/spike phase, or for minor style preference discussions

## Instructions

### Step 1: Establish Context and Scope
Ask about the code's purpose, language, framework, and target audience (embedded system, web service, library). Understand constraints: performance SLAs, security requirements, compliance needs (HIPAA, PCI-DSS). This context determines whether something is a bug or acceptable trade-off.

### Step 2: Security Analysis First
Scan for OWASP Top 10 patterns: SQL injection, XSS, CSRF, authentication bypass, insecure deserialization, sensitive data exposure. Check for:
- Unchecked user input flowing into queries or templates
- Hardcoded secrets, API keys, or credentials
- Missing or weak authentication/authorization checks
- Timing attacks in comparison functions (use constant-time comparison)
- Unsafe deserialization or eval() usage

Security issues are always CRITICAL regardless of code path probability.

### Step 3: Correctness and Logic Analysis
Trace data flow for invariant violations:
- Off-by-one errors in loops and array indexing
- Null/undefined pointer dereferences
- Type mismatches or implicit coercions hiding bugs
- Race conditions in concurrent code (check locks, atomicity)
- Integer overflow/underflow in arithmetic
- Unreachable code paths or unreachable error handlers
- Logic errors: wrong comparison operators, inverted conditions, missing cases in switch statements

### Step 4: Performance Analysis
Identify algorithmic complexity issues:
- N+1 query problems (loop issuing database queries)
- Unnecessary object allocations in hot paths
- Inefficient string concatenation (use StringBuilder/buffer)
- Redundant calculations (move out of loops)
- Unbounded cache growth or memory leaks
- Unnecessary synchronous operations that should be async
- Database queries missing indexes or fetching unnecessary columns

### Step 5: Style and Maintainability
Check against language conventions and the project's established style:
- Inconsistent naming conventions (camelCase vs snake_case)
- Functions exceeding 30 lines (suggests extraction needed)
- Missing docstrings for public APIs
- Magic numbers without explanation
- Deep nesting (>3 levels) suggesting extraction
- Dead code or unreachable branches
- Comments describing "what" instead of "why"

### Step 6: Rank by Severity and Provide Fixes
Categorize findings:
- **CRITICAL**: Security holes, data loss risk, silent failures, crashes
- **HIGH**: Bugs causing incorrect behavior, severe performance degradation
- **MEDIUM**: Logic that only breaks in edge cases, maintainability debt
- **LOW**: Style inconsistencies, minor performance improvements, documentation gaps

For each finding, provide: location, description, risk/impact, refactored code example with explanation.

## Output Template

```
# Code Review: [file/module name]

## Summary
[1-2 sentences on overall quality and main concerns]

## Findings

### 1. [CRITICAL] [Issue Title] - Line XX
**Issue**: [Specific problem and why it matters]
**Risk**: [Actual impact if unfixed]
**Fix**:
\`\`\`
[Refactored code]
\`\`\`
**Explanation**: [Why this fix works, what changed]

### 2. [HIGH] [Issue Title] - Line XX
...

## Quality Checklist
- [x] Security scan complete
- [x] Correctness verified
- [x] Performance acceptable
- [x] Maintainability assessed
- [x] Style consistent with project

## Approved To Merge
[Yes/No with conditions]
```

## Quality Gates
- [ ] Every security issue is explicitly named (SQL injection, XSS, etc.), not vague
- [ ] Each finding includes refactored code, not just "fix this"
- [ ] Severity levels are justified by actual risk, not preference
- [ ] Performance issues include complexity analysis (O(n), O(n²), etc.)
- [ ] At least 3 independent review passes (security, correctness, performance)

## Examples

### Good Output (excerpt)
```
### 1. [CRITICAL] SQL Injection in User Search - Line 47
**Issue**: User input `searchTerm` concatenated directly into SQL query without parameterization.
**Risk**: Attacker can execute arbitrary SQL, reading/modifying all user data.
**Fix**:
\`\`\`python
# Before (VULNERABLE):
query = f"SELECT * FROM users WHERE name LIKE '%{search_term}%'"
results = db.execute(query)

# After (SAFE):
query = "SELECT * FROM users WHERE name LIKE ?"
results = db.execute(query, (f"%{search_term}%",))
\`\`\`
**Explanation**: Parameterized queries ensure input is treated as data, not code. Database driver escapes automatically.
```

### Bad Output (what to avoid)
```
"Line 47 has SQL injection. Use prepared statements."
```
This is vague and doesn't show the actual fix. A reviewer reading this still wouldn't know what code to write.

## Common Mistakes

1. **Mistake**: Flagging style issues as critical
   → **Fix**: Separate style (LOW priority) from bugs (HIGH/CRITICAL). Style doesn't cause outages.

2. **Mistake**: Suggesting fixes without context ("just use async/await")
   → **Fix**: Always show before/after code with explanation of why the fix works.

3. **Mistake**: Missing N+1 query problems in data-heavy code
   → **Fix**: Trace every loop that touches the database. Count queries: if N+1, it's a problem.

4. **Mistake**: Ignoring type safety and null checking
   → **Fix**: In dynamically-typed languages, explicitly check for null/undefined before calling methods.

5. **Mistake**: Treating all findings equally
   → **Fix**: Rank severity. A missing comment is not the same as a security hole.

## Anti-Patterns

- Never say "this is bad" without explaining why or showing how to fix it—the developer won't learn and may ignore the feedback
- Never assume the code is wrong without understanding its constraints; sometimes "inefficient" code is correct for embedded systems with memory limits
- Never flag large functions as bad without checking if they're unavoidably complex due to domain logic (vs. just poor organization)
- Never miss off-by-one errors in array/string indexing by skipping manual trace-through of boundary conditions
- Never ignore concurrency issues by reviewing single-threaded code paths only; check locks, atomicity, race windows

