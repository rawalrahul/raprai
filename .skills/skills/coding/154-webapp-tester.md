---
name: webapp-tester
description: "Write automated tests for web applications using Playwright—covering navigation, forms, assertions, and dynamic content handling"
category: coding
difficulty: intermediate
model_boost: "Weak models write brittle tests with hardcoded waits, wrong selectors, and unclear assertions. This skill ensures stable, maintainable tests using modern selectors and proper wait strategies."
---

# Web Application Tester

## Purpose
This skill teaches you to write reliable automated tests for web apps using Playwright. Proper tests catch regressions, document expected behavior, and enable confident refactoring. You'll learn to select elements robustly (CSS, text, role-based), navigate pages, fill forms, make assertions, and handle dynamic content. A good test is fast, stable, and descriptive—it catches real bugs without false positives.

## When to Use
- You need to verify login flows, form submissions, or multi-step processes
- You want regression tests for critical user journeys
- You're automating visual checks or data validation
- You need CI/CD integration for automated testing
- **Do NOT use when**: Testing requires user authentication beyond credentials (use manual testing); you need to test mobile-specific touch gestures; browser compatibility is critical (requires Selenium)

## Instructions

### Step 1: Install Playwright
Playwright works with Python, JavaScript, Java, and .NET. Choose based on your team's stack.

**Python:**
```bash
pip install playwright pytest-playwright
playwright install  # Download browser binaries
```

**JavaScript/Node:**
```bash
npm install --save-dev @playwright/test
npx playwright install
```

**Create initial test file structure:**
```
my-tests/
├── tests/
│   ├── login.spec.js
│   ├── checkout.spec.js
│   └── fixtures.js
├── playwright.config.js
├── package.json
└── README.md
```

### Step 2: Configure Playwright
Create `playwright.config.js`:

```javascript
// @ts-check
const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
    testDir: './tests',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,  // Fail on test.only() in CI
    retries: process.env.CI ? 2 : 0,  // Retry failed tests in CI
    workers: process.env.CI ? 1 : undefined,  // Single worker in CI for stability
    reporter: 'html',  // Generate HTML report
    use: {
        baseURL: 'http://localhost:3000',
        trace: 'on-first-retry',  // Capture traces on failure
        screenshot: 'only-on-failure',  // Save screenshots on failure
    },
    webServer: {
        command: 'npm run dev',  // Start your app before tests
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
    },
    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
        {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] },
        },
    ],
});
```

### Step 3: Write Your First Test (Login Flow)
Create `tests/login.spec.js`:

```javascript
const { test, expect } = require('@playwright/test');

test('User can log in with valid credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');

    // Verify page loaded
    await expect(page).toHaveTitle('Login');

    // Fill email
    await page.fill('input[name="email"]', 'user@example.com');

    // Fill password
    await page.fill('input[name="password"]', 'correct-password');

    // Click login button
    await page.click('button:has-text("Log in")');

    // Verify redirect to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Verify user name is displayed
    await expect(page.locator('text=Welcome, John')).toBeVisible();
});

test('User sees error with invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'user@example.com');
    await page.fill('input[name="password"]', 'wrong-password');
    await page.click('button:has-text("Log in")');

    // Wait for error message
    const errorMessage = page.locator('[role="alert"]');
    await expect(errorMessage).toContainText('Invalid credentials');

    // Verify still on login page
    await expect(page).toHaveURL('/login');
});
```

**Run tests:**
```bash
npx playwright test tests/login.spec.js
# or with watch mode
npx playwright test --watch
```

### Step 4: Master Selectors (CSS, Text, Role-Based)
Choose robust selectors that survive CSS refactors:

**GOOD selectors (stable):**
```javascript
// By attribute (name, id, data-testid)
page.locator('input[name="email"]')
page.locator('#submit-button')
page.locator('[data-testid="user-menu"]')

// By text (works even if CSS changes)
page.locator('button:has-text("Log out")')
page.locator('text=Welcome, John')

// By role (best for accessibility)
page.locator('button:has-text("Submit")')  // All buttons
page.locator('role=button[name="Submit"]')  // More explicit
page.locator('role=textbox[name="Email"]')  // Form inputs by label

// Combinations
page.locator('form >> button:has-text("Submit")')
```

**AVOID (brittle):**
```javascript
page.locator('button.btn-primary.mt-4')  // Class names change constantly
page.locator('div > div > div > button')  // HTML structure fragile
page.locator('button.btn:nth-of-type(3)')  // Order-dependent, breaks easily
```

**Find good selectors with Inspector:**
```bash
npx playwright codegen http://localhost:3000
# This launches a browser where you can click elements to see selectors
```

### Step 5: Handle Forms and Input
Form filling with validation and error handling:

```javascript
test('User can update profile', async ({ page }) => {
    // Navigate to profile
    await page.goto('/profile');

    // Fill text input
    await page.fill('input[name="firstName"]', 'Jane');

    // Fill dropdown
    await page.selectOption('select[name="country"]', 'US');

    // Check checkbox
    await page.check('input[type="checkbox"][name="subscribe"]');

    // Uncheck checkbox
    await page.uncheck('input[type="checkbox"][name="marketing"]');

    // Fill textarea
    await page.fill('textarea[name="bio"]', 'Software engineer from California');

    // Choose file upload
    await page.locator('input[type="file"]').setInputFiles('path/to/avatar.jpg');

    // Submit form
    await page.click('button:has-text("Save")');

    // Wait for success message
    await expect(page.locator('text=Profile updated')).toBeVisible();
});
```

**Form patterns:**
```javascript
// Disable auto-wait with noWaitAfter (if submit is immediate)
await page.click('button:has-text("Delete")', { noWaitAfter: true });

// Wait for navigation after form submit
const navigationPromise = page.waitForNavigation();
await page.click('form >> button[type="submit"]');
await navigationPromise;  // This resolves when page navigates

// Fill form with object
const credentials = { email: 'test@example.com', password: 'secret' };
await page.fill('input[name="email"]', credentials.email);
await page.fill('input[name="password"]', credentials.password);
```

### Step 6: Navigate and Wait Strategies
Proper waits prevent flaky tests:

```javascript
test('User navigates through multi-step wizard', async ({ page }) => {
    await page.goto('/wizard/step-1');

    // Verify step 1 content
    await expect(page.locator('h1')).toContainText('Step 1');

    // Click next
    await page.click('button:has-text("Next")');

    // Wait for step 2 to load (BEST: wait for expected content)
    await expect(page.locator('h1')).toContainText('Step 2');

    // Wait for specific element to appear
    await page.locator('[data-testid="step-2-content"]').waitFor({ state: 'visible' });

    // Fill step 2
    await page.fill('input[name="address"]', '123 Main St');

    // Click next
    await page.click('button:has-text("Next")');

    // Wait for step 3 (alternative: wait for URL change)
    await page.waitForURL('**/wizard/step-3');

    // Verify final step
    await expect(page.locator('button:has-text("Submit")')).toBeVisible();
});
```

**Wait strategies:**
```javascript
// GOOD: Wait for element appearance
await page.locator('[data-testid="success"]').waitFor({ state: 'visible' });

// GOOD: Wait for URL change
await page.waitForURL('/dashboard');

// GOOD: Wait for specific network request
await page.waitForResponse(response => response.url().includes('/api/users'));

// AVOID: Hard waits (slow, flaky)
await page.waitForTimeout(2000);  // Only use as last resort

// GOOD: Wait for navigation (click triggers nav)
await Promise.all([
    page.waitForNavigation(),
    page.click('a[href="/next-page"]')
]);
```

### Step 7: Make Precise Assertions
Assertions verify expected behavior. Be specific:

```javascript
test('Shopping cart displays correct totals', async ({ page }) => {
    await page.goto('/cart');

    // Count items
    const items = page.locator('[data-testid="cart-item"]');
    await expect(items).toHaveCount(3);

    // Check text content
    await expect(page.locator('[data-testid="subtotal"]')).toContainText('$29.99');

    // Check visibility
    await expect(page.locator('[data-testid="checkout-btn"]')).toBeVisible();

    // Check disabled state
    await expect(page.locator('button[name="promo"]')).toBeDisabled();

    // Check attribute value
    await expect(page.locator('input[name="qty"]')).toHaveValue('2');

    // Check CSS class
    await expect(page.locator('[data-testid="express-shipping"]')).toHaveClass('selected');

    // Screenshot comparison (visual regression)
    await expect(page).toHaveScreenshot('cart-page.png');
});
```

**Assertion reference:**
```javascript
// Text
await expect(element).toContainText('text')
await expect(element).toHaveText('exact text')

// Visibility
await expect(element).toBeVisible()
await expect(element).toBeHidden()

// State
await expect(element).toBeEnabled()
await expect(element).toBeDisabled()
await expect(element).toBeChecked()

// Values
await expect(element).toHaveValue('value')
await expect(element).toHaveAttribute('href', '/path')
await expect(element).toHaveClass('class-name')

// Counts
await expect(locator).toHaveCount(3)

// Page
await expect(page).toHaveTitle('Expected Title')
await expect(page).toHaveURL('/expected-url')
```

### Step 8: Handle Dynamic Content and AJAX
Modern apps load content asynchronously. Wait correctly:

```javascript
test('Search results load dynamically', async ({ page }) => {
    await page.goto('/search');

    // Type in search box
    await page.fill('input[placeholder="Search..."]', 'playwright');

    // Wait for results to appear (not just request complete)
    await expect(page.locator('[data-testid="result-item"]').first()).toBeVisible();

    // Verify specific result exists
    await expect(page.locator('text=Playwright: Fast and reliable E2E testing')).toBeVisible();

    // Count results
    const resultCount = await page.locator('[data-testid="result-item"]').count();
    console.log(`Found ${resultCount} results`);
});

test('Infinite scroll loads more content', async ({ page }) => {
    await page.goto('/feed');

    // Initial load
    let itemCount = await page.locator('[data-testid="feed-item"]').count();
    console.log(`Initial items: ${itemCount}`);

    // Scroll to bottom
    await page.locator('[data-testid="feed-container"]').evaluate(el => el.scrollTop = el.scrollHeight);

    // Wait for more items to load
    await expect(page.locator('[data-testid="feed-item"]')).toHaveCount(itemCount + 10, { timeout: 5000 });

    itemCount = await page.locator('[data-testid="feed-item"]').count();
    console.log(`After scroll: ${itemCount}`);
});
```

### Step 9: Debug Failed Tests
When tests fail, Playwright captures evidence:

```bash
# Run with headed browser (see what happens)
npx playwright test --headed --debug

# View HTML report with screenshots/traces
npx playwright show-report

# Slow down execution to watch
npx playwright test --headed --workers=1
```

**Add debugging to tests:**
```javascript
test('Debug test', async ({ page }) => {
    await page.goto('/');

    // Take screenshot
    await page.screenshot({ path: 'screenshot.png' });

    // Print page content
    console.log(await page.content());

    // Debug element
    const button = page.locator('button:has-text("Submit")');
    console.log(await button.textContent());
    console.log(await button.getAttribute('disabled'));

    // Stop test here for manual inspection
    await page.pause();
});
```

### Step 10: Run Tests in CI/CD
Integrate with GitHub Actions:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - run: npm install
      - run: npx playwright install --with-deps

      - run: npm run build  # Build your app
      - run: npx playwright test

      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

### Step 11: Organize Tests with Fixtures and Hooks
Reuse setup/teardown code:

```javascript
const { test: baseTest, expect } = require('@playwright/test');

// Create custom fixture
const test = baseTest.extend({
    authenticatedPage: async ({ page }, use) => {
        // Setup: login before each test
        await page.goto('/login');
        await page.fill('input[name="email"]', 'test@example.com');
        await page.fill('input[name="password"]', 'password');
        await page.click('button:has-text("Log in")');
        await page.waitForURL('/dashboard');

        // Provide authenticated page to test
        await use(page);

        // Cleanup: logout after test
        await page.click('[data-testid="user-menu"]');
        await page.click('text=Logout');
    },
});

// Use fixture in test
test('Authenticated user can create project', async ({ authenticatedPage: page }) => {
    await page.click('button:has-text("New Project")');
    await page.fill('input[name="name"]', 'My Project');
    await page.click('button:has-text("Create")');
    await expect(page.locator('h1')).toContainText('My Project');
});
```

### Step 12: Test Coverage and Continuous Improvement
Track what you're testing:

```javascript
// tests/user-flows.spec.js - Group related tests
test.describe('User Authentication', () => {
    test('Login with valid credentials', async ({ page }) => { ... });
    test('Login with invalid credentials', async ({ page }) => { ... });
    test('Logout clears session', async ({ page }) => { ... });
});

test.describe('Product Search', () => {
    test('Search by keyword', async ({ page }) => { ... });
    test('Filter by category', async ({ page }) => { ... });
    test('Sort results', async ({ page }) => { ... });
});
```

Run with tag filtering:
```bash
# Only run auth tests
npx playwright test --grep @auth

# Skip slow tests in CI
npx playwright test --grep-invert @slow
```

## Output Template

A complete test suite includes:

```
tests/
├── auth.spec.js         (login, signup, logout)
├── checkout.spec.js     (cart, payment, order)
├── search.spec.js       (search, filter, sort)
├── fixtures.js          (reusable setup/teardown)
└── utils.js             (helper functions)

playwright.config.js     (configuration)
package.json             (dependencies)
.github/workflows/       (CI/CD workflow)
README.md                (documentation)
```

Each test should:
- Have a descriptive name describing expected behavior
- Use robust selectors (role-based or data-testid preferred)
- Wait for expected content (not hard timeouts)
- Make specific assertions
- Include comments for non-obvious steps

## Quality Gates
- [ ] All tests pass consistently (no flakiness)
- [ ] Selectors are role-based or data-testid (not class/CSS-dependent)
- [ ] Tests wait for content, not arbitrary timeouts
- [ ] At least 3 distinct test scenarios (happy path, error path, edge case)
- [ ] Each test is independent (can run in any order)
- [ ] Failed tests produce clear error messages
- [ ] CI/CD pipeline runs tests on every commit
- [ ] At least one multi-step flow test (login → action → logout)

## Examples

### Good Output (excerpt)
```javascript
test('User can filter products by category', async ({ page }) => {
    await page.goto('/products');

    // Wait for initial products to load
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Click filter
    await page.click('[data-testid="category-filter"]');
    await page.click('text=Electronics');

    // Wait for filtered results
    await page.locator('[data-testid="loading"]').waitFor({ state: 'hidden' });

    // Verify all visible products are in Electronics
    const categories = await page.locator('[data-testid="product-category"]').allTextContents();
    categories.forEach(cat => expect(cat).toContain('Electronics'));
});
```
✓ Uses data-testid ✓ Waits for expected content ✓ Specific assertions

### Bad Output (what to avoid)
```javascript
test('Filter works', async ({ page }) => {
    await page.goto('/products');
    await page.click('.filter-btn');  // ✗ Class name brittle
    await page.waitForTimeout(2000);  // ✗ Hard wait, slow
    await expect(page).toHaveTitle('Products');  // ✗ Doesn't verify filter actually worked
});
```
✗ Vague test name ✗ Brittle selectors ✗ Hard timeout

## Common Mistakes

1. **Mistake:** Hard timeouts instead of wait-for-content → **Fix:** Use `waitFor()`, `toBeVisible()`, `waitForURL()`. Hard waits are slow and flaky.

2. **Mistake:** Brittle CSS selectors (`.btn-primary.mt-4`) → **Fix:** Use data-testid, role attributes, or text selectors. CSS refactors will break your tests.

3. **Mistake:** Tests that depend on order (Test A must run before Test B) → **Fix:** Each test is independent. Use fixtures for shared setup.

4. **Mistake:** Not waiting for navigation after clicks → **Fix:** Most clicks cause navigation or AJAX. Wait for expected URL or content.

5. **Mistake:** Checking error messages instead of functionality → **Fix:** Test the actual bug fix, not just the error message appearance.

6. **Mistake:** Screenshot comparisons without version control → **Fix:** Use `toHaveScreenshot()` with proper baseline management.

## Anti-Patterns

- Never use hardcoded waits (`waitForTimeout`) except as absolute last resort
- Never test implementation details (CSS classes, internal state)—test user-visible behavior
- Never make tests that depend on test execution order
- Never use selectors that change with styling refactors
- Never skip assertions (just checking no errors isn't verification)
