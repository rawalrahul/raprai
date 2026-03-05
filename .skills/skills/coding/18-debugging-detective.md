---
name: debugging-detective
description: "Systematic debugging approach: reproduce bug → isolate root cause → diagnose → fix → verify. Includes rubber duck template, binary search strategy, log analysis patterns, and root cause analysis techniques."
category: coding
difficulty: intermediate
model_boost: "Weak models guess at fixes, don't reproduce bugs systematically, miss root causes, and make assumptions without evidence"
---

# Debugging Detective

## Purpose
Production bugs are stressful; random fixes make things worse. Systematic debugging isolates the actual root cause, not symptoms. This skill walks through reproducibility, isolation, diagnosis, and verification—turning vague "it's broken" into "this specific condition causes this specific failure."

## When to Use
- When a feature stops working unexpectedly
- When bugs appear only in production (can't reproduce locally)
- When multiple fixes have been tried but the bug persists
- When you're unsure if something is a bug or expected behavior
- When the same error keeps coming back
- **Do NOT use when**: Debugging exploratory code or if the issue is already well-understood and fix is obvious

## Instructions

### Step 1: Reproduce the Bug Systematically
Reproduction is 80% of debugging. Without a repeatable case, you're guessing.

- **Ask the reporter**: Exact steps taken, environment (browser/OS/version), when it started, screenshots
- **Collect context**: Does it happen every time or intermittently? All users or specific ones? Specific data?
- **Build a minimal reproduction case**: Write the smallest code/steps that trigger it. Don't include unrelated code.

```
Good reproduction case:
1. Create user with name "O'Brien"
2. Click "Export to CSV"
3. Open the CSV file
Expected: Name is "O'Brien"
Actual: Name is "O"Brien" (quote not escaped)
```

```
Bad reproduction case:
"The export is broken"
(No steps, no expected vs actual)
```

Once you have steps that trigger the bug reliably, write them down. You'll need these when verifying the fix.

### Step 2: Isolate the Failing Component
Use binary search to narrow down where the bug is:

Example: Export feature involves:
1. UI form (collect data)
2. Validation logic (check input)
3. CSV formatter (format for export)
4. File handler (write to disk)
5. Browser (download file)

Steps to isolate:
- Is the data being collected correctly? Check browser network tab (what's being sent to server?)
- Is the data being validated? Add a log before/after validation
- Is the CSV being formatted correctly? Save the formatter's output to a file, inspect manually
- Is the file being written? Check server logs for write errors
- Is the browser handling the download? Check browser console for errors

```
// Add strategic logging to isolate
console.log('1. Form data collected:', formData);
console.log('2. Validation passed:', isValidated);
console.log('3. CSV output:', csvString);
console.log('4. File written, sending to browser');
```

Binary search narrows it: "It's the CSV formatter" (narrower than "export is broken")

### Step 3: Use Rubber Duck Debugging
Explain the code line-by-line to someone (or imagine explaining):

```
"This function takes a name and exports it.
Line 1: const name = userData.name
  - userData is passed in, gets the 'name' field
Line 2: const csvLine = name + ',' + otherField
  - Concatenates name and otherField with comma
Line 3: fs.writeFile(path, csvLine)
  - Writes to file

Wait... if name is "O'Brien", then csvLine is "O'Brien,..."
When CSV parser reads this, it sees:
  Field 1: O'Brien (with quotes)
  Field 2: ... (the rest)

OH! The issue is we're not escaping quotes in CSV format.
CSV format requires quotes to be doubled: "O""Brien"
```

Rubber duck reveals: the bug is unescaped quotes in CSV, not elsewhere.

### Step 4: Analyze Logs and Error Messages
Read error messages completely; they often say exactly what's wrong:

```
TypeError: Cannot read property 'name' of undefined at processUser (line 42)
```

This says:
- `undefined` has no property `name`
- The undefined value was supposed to have a `name` property
- It's happening at line 42 in `processUser`

Check what's being passed to `processUser`:
- Is the object parameter sometimes null/undefined?
- Is `name` missing from the object?
- Is the property named something else?

Log the actual input:
```javascript
function processUser(user) {
  console.log('Received user:', JSON.stringify(user));  // What are we actually getting?
  const name = user.name;  // Line 42
}
```

Now you can see: "Received user: null" or "Received user: {age: 30}" (missing name).

### Step 5: Trace the Data Flow
Follow the data from input to output:

Example: CSV export broken for certain users
```
Input: User object {id: 123, name: "O'Brien", email: "..."}
  ↓ (validateUser)
After validation: {id: 123, name: "O'Brien", email: "..."} (unchanged)
  ↓ (formatCSV)
CSV string: "123,O'Brien,..."
  ↓ (escapeCSV)
Escaped CSV: "123,\"O\"\"Brien\",..."
  ↓ (writeFile)
File written
  ↓ (downloadFile)
Browser downloads
```

At each step, log the data. Where does it change unexpectedly?

```javascript
function exportToCSV(users) {
  console.log('Input users:', users);

  const validated = validateUsers(users);
  console.log('After validation:', validated);

  const formatted = formatCSV(validated);
  console.log('CSV formatted:', formatted);

  const escaped = escapeCSV(formatted);
  console.log('After escaping:', escaped);

  writeFile(filename, escaped);
  console.log('File written');
}
```

### Step 6: Check Edge Cases and Boundary Conditions
Bugs often hide at boundaries:

```
If it fails only for certain names (like "O'Brien"):
- Test with quotes: "O'Brien" ✗
- Test with apostrophe: "O'Brien" ✗
- Test with normal name: "John" ✓

Conclusion: The bug is related to special characters, specifically quotes.
```

Check the CSV specification: quotes must be escaped.

### Step 7: Formulate Hypothesis and Test It
Before fixing, state your hypothesis:

```
Hypothesis: CSV export fails when user names contain quotes
because the formatter doesn't escape quotes per CSV spec.

Test:
1. Export user "O'Brien" → CSV file contains unescaped quote
2. Parse the CSV → parser fails or misinterprets fields
3. Fix: Escape quotes by doubling them ("O""Brien")
4. Verify: Export user "O'Brien" → CSV parses correctly
```

### Step 8: Implement and Verify the Fix
After fixing, verify using the original reproduction steps:

```javascript
// BEFORE (broken)
function formatCSV(users) {
  return users.map(u => u.id + ',' + u.name).join('\n');
}

// AFTER (fixed)
function formatCSV(users) {
  return users.map(u => {
    const escapedName = u.name.replace(/"/g, '""');  // Escape quotes
    return `${u.id},"${escapedName}"`;  // Quote fields with names
  }).join('\n');
}

// Test
const csv = formatCSV([{id: 1, name: "O'Brien"}]);
console.log(csv);  // Should output: 1,"O""Brien"
```

Also verify it doesn't break for normal names:
```javascript
const csv = formatCSV([{id: 1, name: "John"}]);
console.log(csv);  // Should output: 1,"John"
```

## Output Template

```
# Debug Report: [Bug Title]

## Reproduction Case
**Steps to reproduce**:
1. {{step 1}}
2. {{step 2}}

**Environment**: {{Browser/OS/version}}

**Expected**: {{expected behavior}}
**Actual**: {{actual behavior}}

## Isolation Analysis
Binary search findings:
- [ ] UI layer: {{status}}
- [ ] Business logic: {{status}}
- [ ] Data layer: {{status}}
- [ ] **Root location**: {{narrowed down}}

## Root Cause
**Diagnosis**: {{What's actually wrong}}
{{Evidence from logs/code}}

## Solution
**Fix**:
\`\`\`
[Code change]
\`\`\`

**Why it works**: {{Explanation of how fix addresses root cause}}

## Verification
**Steps to verify fix**:
1. {{Reproduce original bug}}
2. {{Confirm it's fixed}}
3. {{Confirm no regression}}

**Test cases added**: {{Prevent future recurrence}}
```

## Quality Gates
- [ ] Bug reproduction is specific with steps, not vague
- [ ] Root cause is identified with evidence (logs, code), not guessed
- [ ] Hypothesis is tested before fix is deployed
- [ ] Fix addresses root cause, not just the symptom
- [ ] Original reproduction case verifies the fix
- [ ] No new tests means same bug will return

## Examples

### Good Output (excerpt)
```
## Reproduction
1. Create user with name containing quote: "O'Brien"
2. Export to CSV
3. Open CSV file in Excel
4. Excel shows broken columns: "O" then "Brien" in separate columns

## Isolation
Network request shows: {name: "O'Brien"} (correct)
CSV output in logs: 1,O'Brien (WRONG: quote not escaped)
File on disk: 1,O'Brien (WRONG: quote not escaped)

Root: CSV formatter doesn't escape quotes

## Root Cause
CSV RFC 4180 specifies: quotes must be doubled within quoted fields
Current code does not escape: `"${name}"` produces `"O'Brien"`
Correct format: `"${name.replace(/"/g, '""')}"` produces `"O""Brien"`

## Verification
Before fix: Open CSV in Excel, column breaks at quote
After fix: CSV parses correctly, "O'Brien" in single column
```

### Bad Output (what to avoid)
```
"Export is broken. Fix the CSV code."
```
No reproduction case, no evidence, no root cause.

## Common Mistakes

1. **Mistake**: Assuming you know the bug without reproducing it; fix is wrong
   → **Fix**: Reproduce first. Understanding the exact failure prevents wrong fixes.

2. **Mistake**: Fixing symptoms instead of root cause; same bug appears again
   → **Fix**: Trace to the actual cause. "CSV not escaping quotes" is the cause, not "export button broken."

3. **Mistake**: Not adding tests after fixing; same bug reappears in next release
   → **Fix**: Write a test that fails with the bug, passes with the fix. Prevents regression.

4. **Mistake**: Logging too much (everything), then drowning in output
   → **Fix**: Log strategically at boundaries. Start with coarse logging, narrow down, then add detailed logging.

5. **Mistake**: Assuming the bug is in the code you changed recently
   → **Fix**: Binary search to find actual location. Bug might be in unmodified code.

## Anti-Patterns

- Never apply a random fix and hope it works; you'll apply more fixes, making it worse
- Never assume the logs are complete; missing logs mean you can't trace the data flow
- Never skip reproducing the bug because "I know what's wrong"; you don't, and the fix will be wrong
- Never mix fixing a bug and refactoring code; if something breaks, you won't know what caused it
- Never ignore error messages; they contain critical debugging information (line numbers, types, values)

