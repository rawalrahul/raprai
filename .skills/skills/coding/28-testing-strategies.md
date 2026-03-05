---
name: testing-strategies
description: "Design and implement comprehensive testing strategies including unit tests, integration tests, E2E tests, test coverage analysis, mocking strategies, and flaky test detection."
category: coding
difficulty: intermediate
model_boost: "Weak models write incomplete tests, create brittle tests, or design inefficient test suites"
---

# Testing Strategies

## Purpose
This skill develops production-ready testing strategies that maximize code coverage, catch regressions early, and maintain fast feedback cycles. It covers test pyramid principles (unit tests as foundation, integration and E2E as verification), mocking and stubbing for isolation, async/await testing patterns, test data management, flaky test detection and remediation, and coverage analysis. Output includes well-organized test suites with high coverage, strategies for maintaining test speed as codebases grow, and CI/CD integration for continuous verification.

## When to Use
- Establishing testing practices for new projects
- Improving test coverage from <50% to >80%
- Detecting and fixing flaky tests in existing suites
- Designing test strategy for critical features
- Setting up test infrastructure and CI/CD integration
- Creating test data factories and fixtures
- Migrating test suites between frameworks
- **Do NOT use when**: Deploying untested code to production, or skipping testing for "speed"

## Instructions

### Step 1: Understand Test Pyramid and Coverage Goals
Structure tests efficiently across levels:

```
        End-to-End Tests (few, slow, slow feedback)
           ↑
      Integration Tests (moderate)
           ↑
    Unit Tests (many, fast, quick feedback)
    ↑
  Static Analysis


Test Coverage Goals by Type:
├── Unit Tests: 70-80% of test suite
│   ├── Pure functions: 100% coverage
│   ├── Business logic: 90%+ coverage
│   ├── Utility functions: 80%+ coverage
│   └── Trivial code (getters/setters): Optional
├── Integration Tests: 15-20% of test suite
│   ├── Database interactions: covered
│   ├── API endpoints: covered
│   └── Service integrations: covered
└── E2E Tests: 5-10% of test suite
    ├── Critical user flows: covered
    ├── Payment checkout: covered
    └── Authentication: covered
```

### Step 2: Write Unit Tests with Proper Mocking
Test units in isolation:

```typescript
// Unit Test Example: Pure Business Logic
describe('calculateDiscount', () => {
  it('applies 10% discount for orders over $100', () => {
    const result = calculateDiscount(150);
    expect(result).toBe(15);
  });

  it('applies no discount for orders under $50', () => {
    const result = calculateDiscount(30);
    expect(result).toBe(0);
  });

  it('caps discount at $20 maximum', () => {
    const result = calculateDiscount(1000);
    expect(result).toBe(20);
  });
});

// Unit Test with Mocks: Database Access
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('UserService', () => {
  let mockDb: any;
  let userService: UserService;

  beforeEach(() => {
    // Mock database to avoid real DB calls
    mockDb = {
      query: vi.fn()
    };
    userService = new UserService(mockDb);
  });

  it('gets user by ID', async () => {
    const expectedUser = { id: '123', name: 'John' };
    mockDb.query.mockResolvedValue(expectedUser);

    const result = await userService.getUserById('123');

    expect(result).toEqual(expectedUser);
    expect(mockDb.query).toHaveBeenCalledWith(
      'SELECT * FROM users WHERE id = ?',
      ['123']
    );
  });

  it('handles database error gracefully', async () => {
    const error = new Error('Database connection failed');
    mockDb.query.mockRejectedValue(error);

    await expect(userService.getUserById('123')).rejects.toThrow('Database');
  });
});

// Testing Async Functions with Proper Waiting
describe('AsyncUserService', () => {
  it('waits for async operations to complete', async () => {
    const user = await fetchUserFromAPI();
    expect(user.id).toBeDefined();
  });

  it('times out if API takes too long', async () => {
    vi.useFakeTimers();

    const promise = fetchUserWithTimeout(100);
    vi.advanceTimersByTime(150);

    await expect(promise).rejects.toThrow('Timeout');

    vi.useRealTimers();
  });
});
```

### Step 3: Create Integration Tests
Test component interactions:

```typescript
// Integration Test: API Endpoint
describe('GET /api/posts/:id', () => {
  let app: Express;
  let db: Database;
  let redis: Redis;

  beforeAll(async () => {
    app = createApp();
    db = new Database();
    redis = new Redis();
    await db.connect();
  });

  afterAll(async () => {
    await db.disconnect();
    await redis.disconnect();
  });

  beforeEach(async () => {
    // Clean database before each test
    await db.query('TRUNCATE posts CASCADE');
    await redis.flushAll();
  });

  it('returns post with author information', async () => {
    // Setup: Insert test data
    const userId = await db.query(
      'INSERT INTO users (name) VALUES (?) RETURNING id',
      ['John Doe']
    );
    const postId = await db.query(
      'INSERT INTO posts (user_id, title) VALUES (?, ?) RETURNING id',
      [userId, 'Test Post']
    );

    // Execute: Make API request
    const response = await request(app)
      .get(`/api/posts/${postId}`)
      .expect(200);

    // Assert: Verify response structure
    expect(response.body).toMatchObject({
      id: postId,
      title: 'Test Post',
      author: { id: userId, name: 'John Doe' }
    });
  });

  it('returns 404 for non-existent post', async () => {
    await request(app)
      .get('/api/posts/nonexistent')
      .expect(404);
  });

  it('caches result in Redis after first request', async () => {
    const postId = '123';

    // First request: cache miss
    await request(app).get(`/api/posts/${postId}`);

    // Verify Redis was populated
    const cached = await redis.get(`post:${postId}`);
    expect(cached).toBeDefined();
  });
});

// Integration Test: Database
describe('PostRepository', () => {
  let db: Database;
  let repository: PostRepository;

  beforeAll(async () => {
    db = new Database('test');
    await db.connect();
    repository = new PostRepository(db);
  });

  it('creates post and retrieves it', async () => {
    const post = await repository.create({
      userId: '1',
      title: 'Test',
      content: 'Content'
    });

    const retrieved = await repository.getById(post.id);
    expect(retrieved).toEqual(post);
  });

  it('enforces foreign key constraint', async () => {
    await expect(
      repository.create({
        userId: 'nonexistent',
        title: 'Test',
        content: 'Content'
      })
    ).rejects.toThrow('foreign key');
  });
});
```

### Step 4: Design E2E Tests for Critical Flows
Test complete user journeys:

```typescript
// E2E Test: User Authentication and Post Creation
describe('E2E: User Registration and First Post', () => {
  let browser: Browser;
  let page: Page;

  beforeAll(async () => {
    browser = await chromium.launch();
  });

  beforeEach(async () => {
    page = await browser.newPage();
    // Reset database before each test
    await db.query('DELETE FROM users');
    await db.query('DELETE FROM posts');
  });

  afterEach(async () => {
    await page.close();
  });

  afterAll(async () => {
    await browser.close();
  });

  it('user can register, login, and create post', async () => {
    // Navigate to registration page
    await page.goto('http://localhost:3000/register');

    // Fill registration form
    await page.fill('[name="email"]', 'newuser@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.fill('[name="confirmPassword"]', 'SecurePass123!');

    // Submit form
    await page.click('[type="submit"]');

    // Wait for redirect to login
    await page.waitForNavigation();
    expect(page.url()).toContain('/login');

    // Login with new credentials
    await page.fill('[name="email"]', 'newuser@example.com');
    await page.fill('[name="password"]', 'SecurePass123!');
    await page.click('[type="submit"]');

    // Wait for redirect to dashboard
    await page.waitForNavigation();
    await page.waitForSelector('[data-testid="dashboard"]');

    // Create new post
    await page.click('[data-testid="new-post-btn"]');
    await page.fill('[name="title"]', 'My First Post');
    await page.fill('[name="content"]', 'This is my first post!');
    await page.click('[type="submit"]');

    // Verify post appears in feed
    await page.waitForSelector('[data-testid="post"]');
    const postText = await page.textContent('[data-testid="post"]');
    expect(postText).toContain('My First Post');
  });

  it('handles validation errors gracefully', async () => {
    await page.goto('http://localhost:3000/register');

    // Try to submit without filling form
    await page.click('[type="submit"]');

    // Verify error messages appear
    const errors = await page.locator('[role="alert"]').count();
    expect(errors).toBeGreaterThan(0);
  });
});
```

### Step 5: Manage Test Data and Fixtures
Use factories and fixtures for consistent test data:

```typescript
// Test Data Factory Pattern
class UserFactory {
  static create(overrides: Partial<User> = {}): User {
    return {
      id: crypto.randomUUID(),
      email: `user-${Math.random()}@test.com`,
      name: 'Test User',
      password: hashedPassword('password123'),
      createdAt: new Date(),
      ...overrides
    };
  }

  static async createInDatabase(db: Database, overrides = {}) {
    const user = this.create(overrides);
    await db.query(
      'INSERT INTO users (id, email, name, password) VALUES (?, ?, ?, ?)',
      [user.id, user.email, user.name, user.password]
    );
    return user;
  }
}

// Fixture Usage in Tests
describe('Post Service', () => {
  it('calculates engagement metrics', async () => {
    // Create test data using factory
    const author = await UserFactory.createInDatabase(db);
    const post = await PostFactory.createInDatabase(db, {
      userId: author.id
    });

    // Create engagement data
    for (let i = 0; i < 5; i++) {
      const commenter = await UserFactory.createInDatabase(db);
      await CommentFactory.createInDatabase(db, {
        postId: post.id,
        userId: commenter.id
      });
    }

    const metrics = await postService.getEngagementMetrics(post.id);
    expect(metrics.commentCount).toBe(5);
  });
});

// Fixture File Approach
// fixtures/users.json
[
  {
    id: 'user-1',
    email: 'alice@test.com',
    name: 'Alice',
    role: 'admin'
  },
  {
    id: 'user-2',
    email: 'bob@test.com',
    name: 'Bob',
    role: 'user'
  }
]

// fixtures/posts.json
[
  {
    id: 'post-1',
    userId: 'user-1',
    title: 'Post 1',
    content: 'Content 1'
  },
  {
    id: 'post-2',
    userId: 'user-2',
    title: 'Post 2',
    content: 'Content 2'
  }
]

// Usage
beforeEach(async () => {
  const users = loadFixture('fixtures/users.json');
  const posts = loadFixture('fixtures/posts.json');
  await db.insertMany('users', users);
  await db.insertMany('posts', posts);
});
```

### Step 6: Analyze and Improve Coverage
Track and improve test coverage:

```bash
# Generate coverage report
npm test -- --coverage

# Output:
# ====== Coverage summary ======
# Statements   : 85.2% ( 254 / 298 )
# Branches     : 78.5% ( 156 / 198 )
# Functions    : 82.3% ( 112 / 136 )
# Lines        : 84.6% ( 246 / 291 )

# Identify untested code
npm test -- --coverage --verbose

# Coverage by file
npm test -- --coverage --coverageReporters=text-summary

# HTML coverage report
npm test -- --coverage --coverageReporters=html
# Open coverage/index.html in browser

# Set minimum coverage threshold
// jest.config.js or vitest.config.ts
coverageThreshold: {
  global: {
    branches: 80,
    functions: 80,
    lines: 80,
    statements: 80
  }
}
```

### Step 7: Detect and Fix Flaky Tests
Eliminate unreliable tests:

```typescript
// Flaky Test Pattern 1: Timing Issues
// FLAKY: Random failure due to timing
it('loads user data', async () => {
  fetchUser('123');
  const user = await screen.findByText('John');  // May fail if not rendered fast enough
  expect(user).toBeInTheDocument();
});

// FIXED: Wait for explicit condition
it('loads user data', async () => {
  fetchUser('123');
  // Wait for specific element with proper timeout
  const user = await screen.findByText('John', {}, { timeout: 5000 });
  expect(user).toBeInTheDocument();
});

// Flaky Test Pattern 2: Test Isolation
// FLAKY: Tests share state
let counter = 0;
beforeEach(() => {
  counter++;  // Increments across tests
});

it('test 1', () => {
  expect(counter).toBe(1);  // Passes when run alone, fails in suite
});

// FIXED: Reset state properly
beforeEach(() => {
  counter = 0;  // Reset before each test
});

// Flaky Test Pattern 3: Async Race Conditions
// FLAKY: Multiple async operations race
it('processes data', async () => {
  const results = await Promise.race([
    processData1(),
    processData2()
  ]);
  expect(results).toBeDefined();  // Sometimes both fail before checks complete
});

// FIXED: Wait for all operations
it('processes data', async () => {
  const results = await Promise.all([
    processData1(),
    processData2()
  ]);
  expect(results).toHaveLength(2);
});

// Detecting Flaky Tests in CI
// Run test multiple times to catch intermittent failures
for i in {1..10}; do
  npm test -- --testNamePattern="specific test"
done

// Or use test runner feature
// vitest --run --unstable-threads.singleThread  (disable threading)
```

### Step 8: Set Up CI/CD Test Integration
Automate testing in continuous integration:

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - run: npm ci

      - name: Unit Tests
        run: npm run test:unit -- --coverage

      - name: Integration Tests
        run: npm run test:integration
        env:
          DATABASE_URL: postgresql://postgres:test@localhost/test

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

      - name: E2E Tests
        run: npm run test:e2e
        if: github.event_name == 'pull_request'

      - name: Comment PR with Results
        uses: actions/github-script@v6
        if: always()
        with:
          script: |
            const fs = require('fs');
            const coverage = JSON.parse(fs.readFileSync('./coverage/coverage-summary.json', 'utf8'));
            const lines = coverage.total.lines.pct;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Test Results\nCoverage: ${lines}%`
            });
```

## Output Template

```markdown
# Testing Strategy: {{application_name}}

## Test Pyramid
- Unit Tests ({{unit_count}} tests): {{unit_coverage}}% coverage
- Integration Tests ({{integration_count}} tests): {{integration_coverage}}% coverage
- E2E Tests ({{e2e_count}} tests): Critical user flows covered

## Critical Paths to Test
{{critical_user_journeys}}

## Test Data Strategy
- Factories for {{entity_types}}
- Fixtures in {{fixture_format}}
- Seed scripts for complex scenarios

## Coverage Goals
- Overall: {{target_coverage}}%
- Business Logic: {{logic_coverage}}%
- API Endpoints: {{endpoint_coverage}}%

## CI/CD Integration
- Tests run on: {{trigger_events}}
- Minimum coverage enforced: {{enforced_threshold}}%
- Flaky tests tracked: {{tracking_method}}

## Quality Metrics
{{coverage_report}}
```

## Quality Gates
- [ ] Unit tests cover >80% of business logic
- [ ] All public API endpoints have integration tests
- [ ] Critical user journeys have E2E tests
- [ ] Test data factories/fixtures documented
- [ ] Coverage reports uploaded to CI/CD
- [ ] Flaky tests identified and fixed or skipped with reason
- [ ] Tests run in <5 minutes (for feedback speed)
- [ ] Tests run consistently (no random failures)
- [ ] Setup/teardown properly isolates tests
- [ ] Mocking strategy prevents external dependencies

## Examples

### Good Output (excerpt)
```markdown
# Testing Strategy: Payment API

## Test Distribution
- Unit Tests: 150 tests covering utility functions, business logic (89% coverage)
- Integration Tests: 25 tests covering API endpoints with test database
- E2E Tests: 5 critical flows (registration, payment, checkout)

## Coverage
- Statements: 87%
- Branches: 82%
- Functions: 85%
- Lines: 87%

## Test Data
Using UserFactory, PaymentFactory for consistent test data
Database reset before each integration test
Fixtures for payment failure scenarios

## Performance
- Unit tests: 3 seconds
- Integration tests: 12 seconds
- E2E tests: 45 seconds
- Total: <2 minutes for full suite

## Flaky Tests
None detected; 10 runs of full suite shows 100% consistency
```

### Bad Output (what to avoid)
```
# Testing

We use Jest. Run "npm test".

Tests pass. Coverage is good.

# Problems:
- No test strategy documented
- No clear testing patterns
- No coverage metrics
- No E2E tests
- No data isolation discussed
```

## Common Mistakes

1. **100% Coverage Obsession Without Value**: Achieving 100% coverage by testing trivial getters/setters while missing edge cases in business logic. Illusion of safety without actual quality. Solution: Target 80%+ coverage focusing on business logic; skip trivial code.

2. **E2E Tests for Everything**: Writing E2E tests for every edge case. Test suite takes 2 hours to run. Feedback cycle becomes too slow; developers ignore results. Solution: Use E2E for critical user flows only; unit tests for edge cases.

3. **Not Isolating Tests**: Test A populates database; Test B depends on Test A's data. Running tests individually passes, but running full suite fails. Extremely hard to debug. Solution: Clean database before each test; use factories to create needed data.

4. **Mocking External APIs Without Contract Testing**: Mocking API responses that don't match actual API. Code passes tests but fails in production when real API returns different format. Solution: Use contract testing (e.g., Pact) to ensure mock matches reality.

5. **Flaky Async Tests**: Tests with hardcoded delays (`await sleep(1000)`). Sometimes passes, sometimes fails depending on system load. Solution: Wait for specific conditions (`waitFor`, `waitForElement`), not arbitrary time.

6. **Test Data Not Representative**: Tests pass with simple data (1 user, 5 posts) but fail in production with realistic data (10M users, 1B posts). N+1 queries hidden by small dataset. Solution: Test with production-scale data.

## Anti-Patterns

1. **Testing Implementation Instead of Behavior**: Tests verify internal function calls and argument counts. Implementation changes (refactoring) break tests even though behavior unchanged. Solution: Test input/output behavior, not internal implementation.

2. **Shared Test State Across Suite**: Using `beforeAll()` to set up data once for all tests. Tests become interdependent; running one test fails if earlier test didn't run. Solution: Use `beforeEach()` for proper isolation.

3. **Not Testing Error Cases**: Tests only verify happy path. Edge cases and errors never tested. Production crashes on edge case. Solution: Test error scenarios, boundary conditions, invalid inputs.

4. **Ignoring Test Readability**: Tests with unclear variable names, complex setup, unclear assertions. New developer spends 30 minutes understanding what test does. Solution: Write tests as documentation; clear names and structure.

5. **Coupling Tests to Database Schema**: Tests directly query database tables (brittle to schema changes). Refactoring schema breaks dozens of tests. Solution: Test through application API/service layer, not directly against database.

6. **Tests That Are Slower Than Feature**: Test takes 5 seconds; feature takes 2 seconds to verify manually. Developers skip tests and verify manually. Solution: Keep unit tests <100ms; integration tests <1s each.
