---
name: ci-cd-pipeline
description: "Generate GitHub Actions and GitLab CI pipelines with build, test, lint, security scanning, and deployment stages, including caching, matrix builds, and secret management."
category: coding
difficulty: intermediate
model_boost: "Weak models create inefficient pipelines with missing security scans, poor caching, or incomplete test coverage"
---

# CI/CD Pipeline

## Purpose
This skill generates production-grade CI/CD pipelines for GitHub Actions and GitLab CI that automate code quality checks, testing, security scanning, and deployment workflows. It covers stage orchestration (build → test → lint → security → deploy), intelligent caching to reduce execution time, matrix builds for multi-version testing, secure secret handling, and conditional deployment to multiple environments. Output pipelines are optimized for speed and reliability while maintaining security standards.

## When to Use
- Setting up automated testing and deployment for new projects
- Optimizing existing slow or unreliable pipelines
- Implementing security scanning (SAST, dependency checks, container scanning)
- Creating multi-environment deployment workflows (staging, production)
- Setting up matrix builds for multiple Node versions, Python versions, or OS targets
- Configuring secret management for API keys, credentials, and deployment tokens
- **Do NOT use when**: Using non-Git VCS (Perforce, SVN), or deploying only to on-premise systems with manual processes

## Instructions

### Step 1: Define Pipeline Stages and Triggers
Structure the CI/CD workflow with clear stage ordering:

**Typical Stage Order:**
1. Trigger (on push, PR, scheduled)
2. Checkout & Setup (install dependencies, cache setup)
3. Lint & Format (style checks, type checking)
4. Build (compile/bundle application)
5. Unit/Integration Tests
6. Security Scans (SAST, dependency scanning)
7. Deploy to Staging
8. Smoke/E2E Tests
9. Deploy to Production (manual approval for production)

**GitHub Actions Example:**
```yaml
name: Build & Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
```

### Step 2: Configure Dependency Caching
Minimize installation time across pipeline runs:

**GitHub Actions Caching:**
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Cache pip dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-

      - name: Install Python deps
        run: pip install -r requirements.txt
```

**GitLab CI Caching:**
```yaml
cache:
  key:
    files:
      - package-lock.json
  paths:
    - node_modules/
    - .gradle/wrapper
    - .gradle/caches/
    - ~/.cache/pip/

test:
  image: node:20-alpine
  cache:
    - key: ${CI_COMMIT_REF_SLUG}-node
      paths:
        - node_modules/
  script:
    - npm ci
    - npm test
```

### Step 3: Implement Matrix Builds for Multi-Version Testing
Test across multiple runtimes automatically:

**GitHub Actions Matrix:**
```yaml
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        node-version: [18.x, 20.x, 21.x]
        exclude:
          - os: macos-latest
            node-version: 18.x
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
      - run: npm ci
      - run: npm test
      - run: npm run build
```

**GitLab CI Matrix:**
```yaml
test:
  image: ${CI_REGISTRY_IMAGE}:${CI_COMMIT_SHORT_SHA}
  parallel:
    matrix:
      - PYTHON_VERSION: ["3.9", "3.10", "3.11", "3.12"]
        DJANGO_VERSION: ["3.2", "4.0", "4.2"]
  script:
    - pip install Django==${DJANGO_VERSION} Django-REST-Framework
    - pytest
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### Step 4: Configure Linting and Code Quality Checks
Enforce code standards early in the pipeline:

```yaml
lint:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'

    - run: npm ci

    - name: ESLint
      run: npm run lint

    - name: Type checking
      run: npm run type-check

    - name: Format check
      run: npm run format:check

    - name: Dependency audit
      run: npm audit --production

    - name: SAST scanning
      uses: github/super-linter@v4
      env:
        DEFAULT_BRANCH: main
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Step 5: Implement Security Scanning
Integrate SAST, dependency scanning, and container scanning:

**GitHub Security Scanning:**
```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'

    - name: Upload Trivy results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'

    - name: Run OWASP Dependency-Check
      uses: dependency-check/Dependency-Check_Action@main
      with:
        project: 'MyProject'
        path: '.'
        format: 'All'

    - name: Run npm audit
      run: npm audit --audit-level=moderate

    - name: Check for exposed secrets
      uses: trufflesecurity/trufflehog@main
      with:
        path: ./
        base: ${{ github.event.repository.default_branch }}
        head: HEAD
```

### Step 6: Configure Artifact Handling and Test Reporting
Capture build artifacts and test results:

```yaml
build:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '20'
        cache: 'npm'

    - run: npm ci
    - run: npm run build
    - run: npm test -- --coverage --watchAll=false

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage/lcov.info
        flags: unittests
        name: codecov-umbrella

    - name: Upload build artifacts
      uses: actions/upload-artifact@v3
      with:
        name: build-dist
        path: dist/
        retention-days: 30

    - name: Upload test results
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: test-results
        path: test-results.xml
```

### Step 7: Configure Deployment with Environment Control
Deploy to multiple environments with approval gates:

```yaml
deploy-staging:
  needs: [lint, test, security]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/develop'
  environment:
    name: staging
    url: https://staging.example.com
  steps:
    - uses: actions/checkout@v4
    - uses: actions/download-artifact@v3
      with:
        name: build-dist

    - name: Deploy to staging
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      run: |
        aws s3 sync dist/ s3://staging-bucket/
        aws cloudfront create-invalidation --distribution-id ${{ secrets.CF_DIST_ID }} --paths "/*"

    - name: Smoke tests
      run: npm run test:smoke -- --base-url https://staging.example.com

deploy-production:
  needs: [deploy-staging]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  environment:
    name: production
    url: https://example.com
    deployment-branch: main
  steps:
    - uses: actions/checkout@v4
    - uses: actions/download-artifact@v3
      with:
        name: build-dist

    - name: Create release
      uses: actions/create-release@v1
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      with:
        tag_name: v${{ github.run_number }}
        body: Automated release

    - name: Deploy to production
      env:
        AWS_ACCESS_KEY_ID: ${{ secrets.PROD_AWS_ACCESS_KEY_ID }}
        AWS_SECRET_ACCESS_KEY: ${{ secrets.PROD_AWS_SECRET_ACCESS_KEY }}
      run: |
        aws s3 sync dist/ s3://prod-bucket/
        aws cloudfront create-invalidation --distribution-id ${{ secrets.PROD_CF_DIST_ID }} --paths "/*"
```

## Output Template

```yaml
name: {{pipeline_name}}

on:
  push:
    branches: {{branches}}
  pull_request:
    branches: {{branches}}
  workflow_dispatch:

jobs:
  {{job_name}}:
    runs-on: {{runner_os}}
    strategy:
      matrix:
        {{matrix_config}}
    steps:
      - uses: actions/checkout@v4
      - name: Setup {{language}}
        uses: {{setup_action}}@v4
        with:
          {{setup_options}}
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: {{cache_path}}
          key: ${{ runner.os }}-{{cache_key}}
      - name: Install dependencies
        run: {{install_command}}
      - name: Lint
        run: {{lint_command}}
      - name: Test
        run: {{test_command}}
      - name: Security Scan
        run: {{security_command}}
      - name: Upload Results
        uses: {{upload_action}}@v3
        with:
          {{upload_options}}

  deploy:
    needs: [{{job_dependencies}}]
    environment: {{environment}}
    steps:
      - name: Deploy
        env:
          {{secrets}}
        run: {{deploy_command}}
```

## Quality Gates
- [ ] All jobs have defined dependencies and explicit `needs:` clauses
- [ ] Caching is configured for package managers (npm, pip, maven, etc.)
- [ ] Matrix builds test at least 2 major versions of each dependency
- [ ] Linting and type checking run before tests
- [ ] Security scanning includes SAST, dependency checks, and secret scanning
- [ ] Test results are uploaded and coverage tracked over time
- [ ] Deployment jobs use GitHub/GitLab environments with branch protection
- [ ] Production deployments require manual approval via environment approval rules
- [ ] Secrets are never logged or exposed in artifacts

## Examples

### Good Output (excerpt)
```yaml
name: Build & Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18.x, 20.x, 21.x]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm test -- --coverage
      - uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
          output: 'trivy-results.sarif'
      - uses: github/codeql-action/upload-sarif@v2
```

### Bad Output (what to avoid)
```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install
      - run: npm test
# Problems: no caching, no matrix builds, no linting,
# no security scanning, no artifact uploads, no separate stages
```

## Common Mistakes

1. **No Cache Configuration**: Installing 500 dependencies from scratch on every PR takes 3-5 minutes. Solution: Use actions/cache with package-lock.json or poetry.lock as cache key.

2. **Deploying on Every Commit to Main**: Accidental push to main deploys broken code immediately. Solution: Require manual approval for production via GitHub environments with branch protection.

3. **Running Sequential Jobs Without Dependencies**: All jobs run in parallel even though later stages need earlier stages to complete. Wastes resources and causes flaky tests. Solution: Use `needs: [previous_job]`.

4. **Ignoring Test Failure in Parallel Workflows**: Matrix build for Python 3.9 passes but 3.12 fails, and failure isn't caught. Solution: GitHub Actions inherently fails the whole job if any matrix variant fails.

5. **Storing Build Artifacts Indefinitely**: Disk space fills with 1000s of build artifacts. Solution: Set `retention-days: 30` on artifact uploads.

6. **Leaking Secrets to Logs**: Accidentally echoing environment variable containing API key. Solution: Use `run: npm run deploy` instead of echoing secrets; mask sensitive values.

## Anti-Patterns

1. **Monolithic Single-Job Pipeline**: Everything (lint, test, security, deploy) in one job with no stages or parallelization. Takes 20+ minutes per run. Fast feedback becomes impossible.

2. **No Test Reporting**: Tests run but results aren't captured. No way to see which tests fail or track flakiness over time. Developers have to manually re-run failed tests.

3. **Hardcoded Secrets in Pipeline YAML**: API keys visible in .github/workflows/deploy.yml in public repo. Anyone can use your production credentials. Use GitHub Secrets vault instead.

4. **Always Running Expensive Scans**: SAST scan takes 8 minutes; running on every push to PR branches. Developers wait forever for feedback. Run full security suite only on main branch.

5. **No Environmental Separation**: Staging uses same config as production. Database updates test database and production simultaneously. Hard-coded credentials in YAML that differ by environment.

6. **Deployment Without Smoke Tests**: Pushing to production without verifying that basic endpoints respond. App crashes in production; discovered in customer complaints. Add smoke test step after deployment.
