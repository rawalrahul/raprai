---
name: test-writer
description: "Generate comprehensive unit, integration, and end-to-end tests with edge case identification, mock strategies, coverage analysis, proper naming conventions, and AAA (Arrange-Act-Assert) pattern throughout."
category: coding
difficulty: intermediate
model_boost: "Weak models write shallow tests, miss edge cases, don't mock external dependencies, and use unclear test names"
---

# Test Writer

## Purpose
Tests are documentation that proves code works. Good tests catch regressions early, enable refactoring safely, and clarify expected behavior. This skill generates tests with proper structure (AAA pattern), meaningful names, comprehensive edge cases, and appropriate mocking for speed and isolation.

## When to Use
- Writing unit tests for new functions or classes
- Adding tests when code has low coverage (< 80%)
- Testing critical paths (auth, payments, data access)
- Ensuring edge cases are handled (boundary values, null, empty)
- Planning integration tests for multi-component workflows
- **Do NOT use when**: Tests already exist and cover the code well, or prototyping spike code (test later when design settles)

## Instructions

### Step 1: Understand Code Under Test and Identify Scenarios
Read the function/class you're testing. Understand its contract: inputs, outputs, side effects, dependencies, error cases. List scenarios to test:
```
Function: calculateDiscount(quantity, memberStatus)
Scenarios:
- Non-member, small quantity: discount = 0%
- Non-member, large quantity (>100): discount = 10%
- Member, any quantity: discount = 20%
- Invalid quantity (negative): throw error
- Invalid memberStatus: throw error
- Boundary: quantity = 0 → error
- Boundary: quantity = 100 (threshold): 10% discount
```

### Step 2: Identify Edge Cases
For each input type, think of edge cases:
- **Numbers**: 0, negative, very large (overflow), floating point precision
- **Strings**: empty, null, very long, special characters, SQL keywords
- **Collections**: empty, single element, null items
- **Booleans**: true, false (simple but test both)
- **Dates**: past, future, boundary dates (year 2000, 2038)
- **State**: initialized, uninitialized, partially initialized

Example:
```
Function: trimWhitespace(input)
Edge cases:
- Empty string ""
- Null/undefined
- Only whitespace "   "
- Leading/trailing whitespace "  hello  "
- Internal whitespace "hello world" (should preserve)
- Unicode whitespace (non-ASCII spaces)
```

### Step 3: Use AAA Pattern Consistently
**Arrange**: Set up test data and mocks
**Act**: Call the function
**Assert**: Verify the result

```javascript
// GOOD: Clear AAA structure
test('calculateDiscount returns 10% for non-members with 100+ items', () => {
  // Arrange
  const quantity = 100;
  const memberStatus = 'non-member';

  // Act
  const discount = calculateDiscount(quantity, memberStatus);

  // Assert
  expect(discount).toBe(0.10);
});

// BAD: Vague setup, unclear test
test('discount test', () => {
  const x = 100;
  const result = calculateDiscount(x, 'non-member');
  expect(result).toBe(0.10);
  expect(result).toBeGreaterThan(0);  // Multiple assertions confuse intent
});
```

### Step 4: Write Descriptive Test Names
Test names should read as documentation: "given X, when Y happens, then Z is expected"

```javascript
// GOOD: Specific, executable
test('calculateDiscount returns 20% for members regardless of quantity', () => { ... });
test('calculateDiscount throws error for negative quantity', () => { ... });
test('calculateDiscount returns 0% for non-members with fewer than 100 items', () => { ... });

// BAD: Vague
test('test discount', () => { ... });
test('discount works', () => { ... });
test('edge case', () => { ... });
```

### Step 5: Mock External Dependencies
Unit tests isolate the code under test; mock (replace) external dependencies:

```javascript
// Function being tested
class PaymentProcessor {
  constructor(gateway) {
    this.gateway = gateway;  // Injected dependency
  }

  processPayment(amount) {
    if (amount < 0) throw new Error('Invalid amount');
    return this.gateway.charge(amount);  // Calls external service
  }
}

// Test with mock
test('processPayment calls gateway with correct amount', () => {
  // Arrange
  const mockGateway = { charge: jest.fn().mockResolvedValue({ success: true }) };
  const processor = new PaymentProcessor(mockGateway);

  // Act
  processor.processPayment(100);

  // Assert
  expect(mockGateway.charge).toHaveBeenCalledWith(100);
  expect(mockGateway.charge).toHaveBeenCalledTimes(1);
});

test('processPayment throws for negative amount without calling gateway', () => {
  // Arrange
  const mockGateway = { charge: jest.fn() };
  const processor = new PaymentProcessor(mockGateway);

  // Act & Assert
  expect(() => processor.processPayment(-10)).toThrow('Invalid amount');
  expect(mockGateway.charge).not.toHaveBeenCalled();
});
```

### Step 6: Test Error Cases and Validation
Explicitly test that errors are thrown and have correct messages:

```javascript
test('validateEmail throws for invalid format', () => {
  // Arrange
  const invalidEmails = ['notanemail', 'missing@domain', '@example.com', ''];

  // Act & Assert
  invalidEmails.forEach(email => {
    expect(() => validateEmail(email)).toThrow('Invalid email format');
  });
});

test('divide throws when divisor is zero', () => {
  expect(() => divide(10, 0)).toThrow(RangeError);
  expect(() => divide(10, 0)).toThrow('Division by zero');
});
```

### Step 7: Write Integration Tests
Integration tests verify multiple components work together. Use real dependencies (or test databases), not mocks:

```javascript
// Integration test: Database + Service
test('createUser saves to database and returns created record', async () => {
  // Arrange
  const testDb = new TestDatabase();
  await testDb.connect();
  const userService = new UserService(testDb);

  // Act
  const createdUser = await userService.createUser({
    email: 'test@example.com',
    name: 'John Doe'
  });

  // Assert
  expect(createdUser.id).toBeDefined();

  // Verify actually saved to database
  const retrievedUser = await testDb.query('SELECT * FROM users WHERE id = ?', [createdUser.id]);
  expect(retrievedUser.email).toBe('test@example.com');

  // Cleanup
  await testDb.close();
});
```

### Step 8: Measure and Analyze Coverage
Use coverage tools to identify untested code:
```bash
jest --coverage
```

Output shows:
- **Statements**: What % of lines executed
- **Branches**: What % of if/else paths taken
- **Functions**: What % of functions called
- **Lines**: What % of lines covered

Target: 80%+ coverage for business logic, 60%+ for infrastructure code.

```
File              | Stmts | Branch | Funcs | Lines | Uncovered Line
PaymentProcessor  | 95%   | 85%    | 100%  | 95%   | 42
```

Line 42 is uncovered—that's a code path not tested.

## Output Template

```
# Test Suite: [Function/Class Name]

## Overview
[2-3 sentences on what's being tested and why these tests matter]

## Test Cases

### Unit Tests

#### Scenario 1: [Specific behavior under condition]
\`\`\`javascript
test('{{test description}}', () => {
  // Arrange
  {{setup}}

  // Act
  {{execute}}

  // Assert
  {{verify}}
});
\`\`\`

#### [Additional scenarios...]

### Edge Cases
\`\`\`javascript
test('handles empty input', () => {
  // Arrange & Act & Assert
  {{test}}
});

test('handles null input', () => {
  {{test}}
});
\`\`\`

### Integration Tests
[Multi-component tests using real dependencies]

## Coverage Analysis
[Target coverage %, current status, gaps]

## Mock Strategy
[What's mocked, why, and how]
```

## Quality Gates
- [ ] Every test uses AAA pattern with clear Arrange/Act/Assert sections
- [ ] Test names are specific and describe the behavior being tested
- [ ] All public functions have at least 2 test cases
- [ ] Error cases are tested (invalid input, exceptions thrown)
- [ ] Edge cases are tested (boundary values, empty collections, null)
- [ ] External dependencies are mocked in unit tests
- [ ] Target coverage is met (80%+ for critical code)

## Examples

### Good Output (excerpt)
```javascript
describe('Password Validator', () => {
  test('accepts password with 8+ chars, uppercase, lowercase, number, symbol', () => {
    // Arrange
    const password = 'MyPass123!';

    // Act
    const isValid = validatePassword(password);

    // Assert
    expect(isValid).toBe(true);
  });

  test('rejects password with fewer than 8 characters', () => {
    expect(validatePassword('Short1!')).toBe(false);
  });

  test('rejects password missing uppercase letter', () => {
    expect(validatePassword('mypass123!')).toBe(false);
  });

  test('rejects null input', () => {
    expect(() => validatePassword(null)).toThrow('Password cannot be null');
  });

  test('rejects empty string', () => {
    expect(validatePassword('')).toBe(false);
  });
});
```

### Bad Output (what to avoid)
```javascript
test('password test', () => {
  const p = 'MyPass123!';
  expect(validatePassword(p)).toBe(true);
  const p2 = 'short';
  expect(validatePassword(p2)).toBe(false);
  const p3 = 'ALLUPPERCASE123!';
  expect(validatePassword(p3)).toBe(false);
});
```
Multiple behaviors in one test, unclear names, no AAA structure.

## Common Mistakes

1. **Mistake**: Testing multiple behaviors in one test ("test login and user creation together")
   → **Fix**: One assertion goal per test. If it fails, you know exactly what broke.

2. **Mistake**: Not mocking external calls; tests hit real APIs/databases, making them slow and brittle
   → **Fix**: Mock external services in unit tests. Use test databases in integration tests.

3. **Mistake**: Missing boundary tests; code breaks at edge values nobody tested
   → **Fix**: Explicitly test 0, negative, empty, null, max value, min value.

4. **Mistake**: Asserting on multiple unrelated things (method call AND return value AND side effect)
   → **Fix**: Each test has one purpose. If needed, split into 2-3 focused tests.

5. **Mistake**: Not testing error cases; code throws but tests never check exceptions
   → **Fix**: Explicitly test that exceptions are thrown, have correct type, and correct message.

## Anti-Patterns

- Never write tests that depend on other tests; each test must be independent and able to run in any order
- Never use real credentials, API keys, or production data in tests; always use test data or mocks
- Never make tests so brittle they break with minor refactoring; test behavior, not implementation details
- Never skip testing edge cases with "it's unlikely to happen"; unlikely cases are where bugs hide
- Never leave commented-out test code; if it's not needed, delete it; if it might be needed, document why it's disabled

