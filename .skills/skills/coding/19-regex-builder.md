---
name: regex-builder
description: "Build and explain regex patterns step-by-step with test cases, edge cases, performance considerations, and plain-English explanations. Generate regex for common patterns with clear documentation."
category: coding
difficulty: intermediate
model_boost: "Weak models generate untested regex, miss edge cases, don't explain patterns, and create inefficient patterns that timeout"
---

# Regex Builder

## Purpose
Regular expressions are powerful but cryptic. A poorly-written regex can timeout on certain inputs, making websites hang. This skill builds regex patterns systematically, tests them thoroughly, explains them clearly, and identifies performance pitfalls.

## When to Use
- Validating email, phone, URL, or other structured data
- Parsing log files, CSV, or unstructured text
- Finding patterns in large documents
- Writing search/replace logic
- **Do NOT use when**: Simple string operations (use indexOf, split, replace), or for parsing structured formats (use proper parsers like JSON.parse, XML libraries)

## Instructions

### Step 1: Define the Pattern Precisely
Before writing regex, describe what to match in plain English:

```
Pattern: Email address
Matching rules:
- Starts with 1+ alphanumeric or special chars: . _ -
- Followed by @ symbol
- Followed by domain name (alphanumeric, dots, hyphens)
- Ends with . and 2-6 letter TLD (com, org, co.uk)

Matching: user@example.com ✓, user.name@sub.domain.com ✓
Not matching: user@.com (no domain), user@domain (no TLD), @example.com (no local)
```

This specification prevents regex sprawl and clarifies requirements.

### Step 2: Build Regex Step by Step
Don't write the entire regex at once. Build incrementally:

```
Step 1: Match alphanumeric only
Regex: \w+
Matches: abc123 ✓

Step 2: Add special characters to character class
Regex: [\w.-]+
Matches: abc.123 ✓, abc-123 ✓

Step 3: Add the @ symbol
Regex: [\w.-]+@
Matches: abc@  ✓

Step 4: Add domain name
Regex: [\w.-]+@[\w-]+
Matches: abc@example ✓

Step 5: Add dot and TLD
Regex: [\w.-]+@[\w-]+\.[a-z]{2,6}
Matches: abc@example.com ✓

Final: Add anchors to match entire string
Regex: ^[\w.-]+@[\w-]+\.[a-z]{2,6}$
```

Each step adds one piece, testable independently.

### Step 3: Test Against Known Cases
Create test cases covering normal use and edge cases:

```javascript
const emailRegex = /^[\w.-]+@[\w-]+\.[a-z]{2,6}$/i;

// Should match
const validEmails = [
  'user@example.com',
  'user.name@example.com',
  'user-name@example.co.uk',
  'john123@domain.org'
];

// Should NOT match
const invalidEmails = [
  'userexample.com',      // missing @
  'user@',                 // missing domain
  '@example.com',          // missing local
  'user@example',          // missing TLD
  'user@.com',             // missing domain name
  'user name@example.com', // space not allowed
  'user@exam ple.com'      // space in domain
];

validEmails.forEach(email => {
  console.assert(emailRegex.test(email), `${email} should match`);
});

invalidEmails.forEach(email => {
  console.assert(!emailRegex.test(email), `${email} should NOT match`);
});
```

### Step 4: Identify and Test Edge Cases
Edge cases are where regex fails. Test:

```
Boundary cases:
- Minimum length: "a@b.co" (1 char local, 1 char domain, 2 char TLD)
- Maximum length: very long email
- Special but valid characters: user+tag@example.com (+ not in our regex!)
- Unicode: café@example.com (accents)
- Uppercase: USER@EXAMPLE.COM
- Multiple dots: user.name.last@example.co.uk

For email, our regex ^[\w.-]+@[\w-]+\.[a-z]{2,6}$ has issues:
- \w includes underscore (_) which is rarely valid in domain names
- Doesn't handle + (common in Gmail: user+tag@gmail.com)
- TLD max of 6 chars fails for .museum (7 chars)
```

Refine based on edge cases:
```javascript
// Improved email regex
const emailRegex = /^[a-zA-Z0-9._+%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// New tests
console.assert(emailRegex.test('user+tag@example.com'), 'should support +');
console.assert(emailRegex.test('user@example.museum'), 'should support long TLDs');
console.assert(!emailRegex.test('user_name@domain.com'), 'underscore in domain disallowed');
```

### Step 5: Explain the Regex Clearly
Break down each part:

```
Regex: ^[a-zA-Z0-9._+%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$

Part by part:
^                           # Start of string (anchor)
[a-zA-Z0-9._+%-]+          # One or more: letters, digits, dot, underscore, plus, percent, hyphen
@                           # Literal @ symbol
[a-zA-Z0-9.-]+             # One or more: letters, digits, dot, hyphen (domain name)
\.                          # Literal dot (escaped)
[a-zA-Z]{2,}               # 2+ letters (TLD)
$                           # End of string (anchor)

Plain English:
"A string that starts with an email local part (letters, numbers, special chars),
then @, then a domain name, then a dot, then 2+ letter TLD, then ends."
```

### Step 6: Check for Performance Issues
Some regex patterns cause exponential backtracking (ReDoS - Regex Denial of Service):

```
DANGEROUS regex:
^(a+)+b$

Why: If input is "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaac" (no final 'b'),
the + operator tries combinations:
- Try: all a's match with first +, second + fails, backtrack
- Try: all but one a's match with first +, remaining a matches second +, fails
- ... continues exponentially (2^n attempts for n a's)

Input length 30: 2^30 attempts = 1 billion+ iterations = TIMEOUT

SAFE regex:
^a+b$

Why: No nested quantifiers (no + next to +), so linear matching without backtracking.
```

Red flags for ReDoS:
- Nested quantifiers: `(a+)+`, `(a*)*`, `(a{2,}){3,}`
- Alternation with overlapping: `(a|ab)+` (a and ab overlap)
- Complex lookaheads with backtracking

Test performance:
```javascript
const dangerousRegex = /^(a+)+b$/;
const input = 'a'.repeat(30) + 'c';  // 30 a's, then c (no b to match)
console.time('regex');
dangerousRegex.test(input);  // HANGS
console.timeEnd('regex');
```

Always test regex with slightly-wrong input to catch ReDoS.

### Step 7: Document Regex Usage
Provide context for maintainers:

```javascript
// Validate email addresses per RFC 5322 (simplified)
// Does not handle: comments, quoted strings, international domains
// Use for: user registration, contact forms
// Do NOT use for: sending emails (RFC 5322 is complex)
const emailRegex = /^[a-zA-Z0-9._+%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// Test cases:
// ✓ user@example.com, user+tag@example.com
// ✗ user @example.com (spaces), user@domain (no TLD)

export function validateEmail(email) {
  return emailRegex.test(email);
}
```

## Output Template

```
# Regex Pattern: [Pattern Name]

## Requirements
[Plain English description of what to match]

## Pattern Specification
[What should match, what shouldn't]

## Regex Expression
\`\`\`
{{regex}}
\`\`\`

## Step-by-Step Construction
**Step 1**: {{Component}} → `{{regex}}`
**Step 2**: {{Component}} → `{{regex}}`
...

## Plain English Explanation
[Break down each part]

## Test Cases

### Should Match
\`\`\`javascript
const validCases = [
  '{{valid}}',
  '{{valid}}'
];

validCases.forEach(c => console.assert(regex.test(c)));
\`\`\`

### Should NOT Match
\`\`\`javascript
const invalidCases = [
  '{{invalid}}',
  '{{invalid}}'
];

invalidCases.forEach(c => console.assert(!regex.test(c)));
\`\`\`

### Edge Cases
\`\`\`javascript
{{edge case tests}}
\`\`\`

## Performance Analysis
- **Type**: {{Linear / Exponential / Risky}}
- **Backtracking**: {{Yes/No}}
- **ReDoS Risk**: {{None / Low / Medium}}
- **Notes**: {{Any concerns}}

## Limitations
- {{Cannot handle X}}
- {{Not designed for Y}}

## Usage Example
\`\`\`javascript
{{Real usage code}}
\`\`\`
```

## Quality Gates
- [ ] Regex is tested against valid AND invalid cases, not just one
- [ ] Each part of regex is explained in plain English, not left cryptic
- [ ] Edge cases tested (boundary values, special characters, unicode)
- [ ] Performance checked (no nested quantifiers, no overlapping alternation)
- [ ] Limitations documented (what it doesn't match and why)
- [ ] Usage example provided for maintainers

## Examples

### Good Output (excerpt)
```
## Pattern: Phone Number (US)
Matches: (555) 123-4567, 555-123-4567, 5551234567
Not matches: 555 123 4567 (spaces), 555-12-4567 (wrong format)

## Regex
^(\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?[2-9]\d{2}[-.\s]?\d{4}$

## Step-by-Step
Step 1: Optional country code
^(\+?1[-.\s]?)?

Step 2: Area code (2-9 start, 2 more digits)
(\+?1[-.\s])?\(?[2-9]\d{2}\)?

Step 3: Exchange code (2-9 start, 2 more digits)
... [2-9]\d{2}

Step 4: Line number (4 digits)
...\d{4}$

## Plain English
"Optionally starts with +1 or 1, then 3-digit area code (2-9 start),
then 3-digit exchange (2-9 start), then 4-digit line number,
with optional formatting (spaces, dashes, parentheses)."

## Test Cases
Matches: (555)123-4567 ✓, +1-555-123-4567 ✓, 5551234567 ✓
Rejects: 555-123-4567 with area code 555 (2-9 rule) ✓, (555) 123-456 (4 digits) ✓

## Performance
Type: Linear (no backtracking)
ReDoS Risk: None (no nested quantifiers)
```

### Bad Output (what to avoid)
```
"Use this regex for email: ^[^@]+@[^@]+\.[^@]+$"
```
No explanation, poor coverage (matches "a@b.c" which is invalid), no tests.

## Common Mistakes

1. **Mistake**: Regex matches substrings instead of entire input
   → **Fix**: Always use ^ and $ anchors: `^pattern$` matches whole string, not substrings

2. **Mistake**: No test cases; regex breaks in production
   → **Fix**: Test valid AND invalid cases before deploying

3. **Mistake**: Nested quantifiers causing ReDoS timeout on certain input
   → **Fix**: Avoid `(a+)+`, `(a*)*`; use `a+` instead

4. **Mistake**: Regex too permissive, matches invalid data
   → **Fix**: Be specific with character classes `[a-z]` not `\w`, use anchors

5. **Mistake**: Forgetting to escape special regex characters (. $ * + ?)
   → **Fix**: Escape with backslash: `\.` for literal dot, `\$` for literal dollar sign

## Anti-Patterns

- Never use `.*` to match "anything"; it's greedy and slow. Use `.+` (one or more), `.{0,n}` (limited), or `.+?` (non-greedy)
- Never write regex without test cases; you will deploy a broken pattern
- Never nest quantifiers `(a+)+`; this causes exponential complexity and timeout attacks
- Never use character classes too broadly `[^a]` (anything except a); be specific what you DO want, not don't want
- Never regex code that could use simpler string methods; `email.includes('@')` is faster than regex for simple checks

