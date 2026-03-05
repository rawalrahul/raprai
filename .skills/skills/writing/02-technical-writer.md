---
name: technical-writer
description: "Generate production documentation, API docs, READMEs, and architecture guides with clear information hierarchy, runnable code examples, versioning strategy, and audience-appropriate calibration. Targets zero ambiguity and implementer confidence."
category: writing
difficulty: intermediate
model_boost: "Weak models produce vague explanations, untested code examples, missing edge cases, and inconsistent terminology that confuse implementers and create support burden."
---

# Technical Writer

## Purpose
Create documentation that readers can implement without returning with questions. Technical documentation succeeds when implementers can follow it step-by-step without interpretation, copy-paste code without debugging, and understand why each step matters. This skill balances depth (enough detail to prevent failure) with brevity (no filler).

## When to Use
- Writing API documentation with endpoint specifications, code examples, and error handling
- Creating README files for GitHub/GitLab projects with setup, usage, and contribution guidelines
- Documenting system architecture, deployment procedures, or infrastructure decisions
- Building onboarding documentation for internal tools or complex features
- Creating troubleshooting guides and FAQs with root-cause explanations
- **Do NOT use when**: Writing marketing material, thought leadership, or end-user guides for non-technical audiences

## Instructions

### Step 1: Define Audience & Technical Depth
Identify target reader: beginner (first language, needs context), intermediate (knows the domain, wants quick reference), or advanced (expert, needs edge cases and performance implications). Every section should match one audience level consistently. Include audience callouts: "For teams new to Docker:" or "Advanced: Custom authentication flows." Determine prerequisite knowledge explicitly ("assumes familiarity with REST APIs" or "no prior experience required").

### Step 2: Create Unambiguous Terminology Map
List all key terms used in documentation and define once, at first use, in plain language. For example: "Webhook: a mechanism that notifies your application when an event occurs (like a payment confirmation)." Use identical terminology throughout (never "endpoint" and "route" interchangeably). Add a Glossary section if more than 20 technical terms used. Create this terminology map before writing, not after.

### Step 3: Build Hierarchical Structure (Not Linear)
Top-level sections answer: "What is this? Why would I use it?" → "How do I get started?" → "How do I do X?" → "What if Z happens?" Structure = Overview → Quick Start (5 min) → Detailed Guide (by use case) → API Reference (alphabetical) → Troubleshooting → Examples. Each section should be referenceable independently; readers skip around, don't read linearly.

### Step 4: Provide Copy-Paste Runnable Code Examples
Every code example must be: (a) complete (not pseudocode), (b) tested (actually runs), (c) realistic (not toy examples), (d) annotated (comments on why, not just what). Include the language/framework version (e.g., "Node.js 18+"). Show input and output. For complex examples, show the sequence: setup → call → result. Bad: `data = get_user()`. Good: `const user = await getUser({ id: '123' }); console.log(user.email);` with comment explaining the async/await pattern.

### Step 5: Document Edge Cases & Failure Modes
Add "Common Issues" or "Troubleshooting" sections tied to specific use cases. For each code example, add: "This will fail if: [specific condition]. Solution: [fix]." Include rate limits, timeout behavior, authentication errors, and data validation requirements. Show example error responses and how to handle them. Example: "If you see 'Invalid API key' error, verify your .env file has STRIPE_KEY set correctly and the key hasn't expired."

### Step 6: Version Documentation & Migration Paths
Indicate what applies to which versions immediately (e.g., "Available in v2.0+"). If documenting multiple versions, use version selector or separate sections. For breaking changes or deprecations, provide migration examples: old code → new code with explanation. Example: "v1.x: `client.fetch()` | v2.0+: `client.request()` — the method signature changed to support streaming." Include deprecation timeline.

## Output Template

```markdown
# {{Feature/Product Name}}

{{1-sentence summary of what this is and who should use it}}

**Audience:** {{beginner|intermediate|advanced}}
**Prerequisites:** {{List of assumed knowledge, tools, or accounts needed}}
**Time to implement:** {{X minutes for basic setup; Y minutes for advanced features}}

## Overview

{{What this does (1-2 sentences)}}

{{Why you'd use it (2-3 concrete scenarios)}}

{{When NOT to use it, if applicable}}

## Quick Start (5 Minutes)

{{Numbered steps 1-5 that get to "working" state}}

```language
{{Complete, runnable code example}}
```

**Expected output:**
```
{{Actual output from running the code}}
```

## Detailed Guide

### {{Use Case 1: Specific Action}}

**Goal:** {{What you'll accomplish in this section}}

{{Explanation of concept, then step-by-step instructions}}

```language
{{Code example specific to this use case}}
```

{{Edge case and failure mode: If X, then Y. Solution: Z.}}

### {{Use Case 2}}

{{Repeat pattern}}

## API Reference

### {{Endpoint Name}}

**Request**
```
{{Method}} {{Path}}
Authorization: {{Auth type}}

{{Parameter table or request body example}}
```

**Response (200 OK)**
```json
{{Example response with all fields labeled}}
```

**Error Responses**
- **{{Error code}} {{Error name}}**: {{When this occurs and how to fix it}}

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| {{Issue}} | {{Root cause}} | {{Fix with code example}} |

## Related

- {{Internal link to related feature}}
- {{External resource with brief description}}
```

## Quality Gates

- [ ] First section (Overview) answers "what is this and why would I use it" without jargon
- [ ] Every code example is complete, runnable, and includes input/output (no pseudocode)
- [ ] All technical terms defined at first use in plain language; terminology consistent throughout
- [ ] At least one "Common Issues" or "Troubleshooting" section with specific error examples and solutions
- [ ] Audience level specified (beginner/intermediate/advanced); prerequisites listed explicitly
- [ ] For API docs: request and response examples shown; all possible error codes documented
- [ ] Quick Start section achievable in stated time (5-10 min max) with copy-paste code
- [ ] Structure is hierarchical and referenceable (reader can jump to section they need)
- [ ] Version information clear: "Available in v2.0+" or "Deprecated in v3.0, use [alternative] instead"
- [ ] At least one worked example showing the full flow: setup → call → output

## Examples

### Good Output (Excerpt)

# Webhook Integration Guide

Webhooks notify your application when events happen in our system (like a payment received or user created). Instead of polling for changes, we push data to you when it matters.

**Audience:** intermediate
**Prerequisites:** Ability to write HTTP request handlers; familiarity with JSON
**Time to implement:** 10 minutes for basic setup; 30 minutes to handle all event types

## Overview

When an event occurs (e.g., `customer.created`), we send an HTTP POST to your webhook URL with a JSON payload. Your application receives it, processes it, and returns a 200 status. If you don't return 200 within 30 seconds, we retry up to 3 times with exponential backoff.

**Use cases:**
- Send a welcome email when a customer signs up
- Update inventory when a purchase completes
- Log transaction data to your analytics system

**When NOT to use webhooks:** If you need real-time sub-second latency, use the REST API with polling instead (though slower).

## Quick Start (5 Minutes)

1. Go to Settings > Webhooks in the dashboard
2. Click "Add Webhook"
3. Enter your URL: `https://yourapp.com/webhooks/events`
4. Select event type: `customer.created`
5. Click Save and test with the "Send Test Event" button

Your endpoint should return:
```javascript
// Node.js Express example
app.post('/webhooks/events', (req, res) => {
  console.log('Event received:', req.body.event_type);
  res.status(200).send('OK');
});
```

**Expected behavior:** Dashboard shows "Delivery successful" ✓

### Common Issues

**Problem:** Dashboard shows "Delivery failed (401)"
**Cause:** Your webhook URL requires authentication
**Solution:** Check that your endpoint does NOT require API keys. If it must, add the key to your URL or use our Webhook Secrets (see "Advanced: Securing Webhooks" below).

---

**Problem:** Test event sends, but real events don't arrive
**Cause:** Your handler is returning 500 or taking >30 seconds
**Solution:** Add logging to identify where it's failing: `console.log('Webhook received at', new Date())`. If slow, move processing to a background job.

### Good Output Analysis
- Defines webhook in plain language with concrete examples
- Audience and prerequisites stated
- Time estimate given
- Quick Start achieves working state in 5 min with copy-paste code
- Shows expected output
- Common Issues section with specific causes and solutions
- Terminology consistent ("webhook URL", "event type")

### Bad Output (What to Avoid)

# Webhooks

Webhooks are a pattern for asynchronous event notification. The server sends data to a client-specified endpoint via HTTP POST when an event occurs. The client must handle the request and return an appropriate HTTP status code.

Webhooks can be configured in the dashboard. Events include various types of system changes. Authentication can be implemented through various mechanisms.

Example:
```
post("/webhook", () => {
  // handle event
})
```

**Issues Identified:**
- No audience level specified
- Unclear what the reader should do first
- Vague explanation using jargon ("asynchronous event notification")
- Code example is pseudocode, not runnable
- No edge cases mentioned
- No troubleshooting guidance
- Doesn't explain WHY you'd use webhooks
- No expected output shown
- Inconsistent terminology ("webhook" vs "client-specified endpoint")

## Common Mistakes

1. **Mistake**: Writing explanations before code, burying the "how to do it" part
   → **Fix**: Show working code first (Quick Start), then explain concepts. Readers scan for examples; place code high and prominently.

2. **Mistake**: Code examples that are incomplete, pseudocode, or don't run (missing imports, environment setup, etc.)
   → **Fix**: Every code example must be copy-paste ready. Include imports, full function signatures, and expected output. Test it yourself before including.

3. **Mistake**: Explaining only the happy path; ignoring what happens when things go wrong
   → **Fix**: For every major section, add "What if X fails?" with specific error messages and solutions. Include timeout behavior, rate limits, and validation rules.

4. **Mistake**: Using inconsistent terminology ("endpoint" one section, "route" the next)
   → **Fix**: Create a terminology map before writing. Define each term once, at first use. Use identical language throughout.

5. **Mistake**: Linear structure forcing readers to read sequentially instead of jumping to what they need
   → **Fix**: Organize hierarchically: Overview → Quick Start → Detailed Use Cases → Reference → Troubleshooting. Each section must be self-contained.

## Anti-Patterns

- **Never** assume reader knowledge. Even for "intermediate" audiences, define technical terms at first use ("token: a string that authenticates your requests").
- **Never** provide pseudocode or incomplete examples. If you can't provide complete, runnable code, provide a detailed written walkthrough instead.
- **Never** forget to document error cases, rate limits, timeouts, or authentication requirements. These cause 80% of implementation failures.
- **Never** mix multiple audience levels in one section. Use separate sections: "Beginner: Simple Setup" vs. "Advanced: Custom Authentication."
- **Never** leave version ambiguity. Always specify: "Available in v2.0+", "Deprecated since v3.0, use X instead", or "Works in all versions".
