---
name: git-workflow
description: "Generate professional Git workflows including branch strategies, Conventional Commits, PR descriptions, release notes, and changelog generation with merge conflict resolution guidance."
category: coding
difficulty: intermediate
model_boost: "Weak models struggle with Git workflow best practices and commit message consistency"
---

# Git Workflow

## Purpose
This skill guides professionals in establishing and executing disciplined Git workflows that ensure code quality, traceability, and maintainability. It covers branch strategies (Git Flow, GitHub Flow), standardized commit messages using Conventional Commits, professional PR descriptions, release note generation, automated changelog creation, and systematic merge conflict resolution. The output produces artifacts that teams can immediately adopt for improved code governance.

## When to Use
- Setting up Git workflows for new or existing projects
- Establishing Conventional Commits standards across a team
- Generating automated release notes and changelogs
- Creating comprehensive PR templates and guidelines
- Handling complex merge conflicts with strategic resolution
- Documenting branching strategies (Git Flow vs. GitHub Flow)
- **Do NOT use when**: Git is not the version control system, or teams are using custom internal VCS systems

## Instructions

### Step 1: Analyze Project Requirements and Team Structure
Determine the appropriate branching strategy based on project type (web app, library, monorepo), release frequency, and team size. Ask clarifying questions: Is this continuous deployment (GitHub Flow) or scheduled releases (Git Flow)? How many developers? What's the production stability requirement?

### Step 2: Design Branch Strategy with Naming Conventions
**Git Flow Example:**
```
main (production-ready)
├── release/v1.2.0 (release preparation)
├── hotfix/critical-bug (urgent production fixes)
develop (integration branch)
├── feature/user-authentication
├── feature/payment-integration
├── bugfix/login-redirect-issue
└── chore/update-dependencies
```

**Naming convention:** `{type}/{short-description}`
- feature: new functionality
- bugfix: bug fixes
- hotfix: production emergency fixes
- chore: maintenance, dependencies
- docs: documentation only
- refactor: code reorganization without behavior change

### Step 3: Establish Conventional Commits Format
Standardize commit messages for automated changelog generation:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:** feat, fix, docs, style, refactor, perf, test, chore, ci

**Example:**
```
feat(auth): add JWT token refresh mechanism

Implement automatic token refresh on 401 responses
using a refresh token stored in httpOnly cookie.
Prevents user session interruption during API calls.

Closes #234
BREAKING CHANGE: auth endpoint now returns token_type field
```

### Step 4: Create PR Template and Guidelines
Structure PR descriptions for code review clarity:

```markdown
## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Documentation update

## Description
Brief summary of changes and why they're needed.

## Related Issues
Closes #123

## Testing
How was this tested? Include steps to reproduce.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] Tests pass locally
```

### Step 5: Generate Automated Release Notes and Changelogs
Use git tags and Conventional Commits for automation:

```bash
# Generate changelog from commits between versions
git log v1.0.0..v1.1.0 --format="%H %s" | \
  grep -E "^feat|^fix|^BREAKING" > changelog.txt
```

**Automated Changelog Generator (Node.js example):**
```javascript
const commits = require('child_process')
  .execSync('git log --format=%B')
  .toString()
  .split('\n\n');

const grouped = {
  features: [],
  fixes: [],
  breaking: [],
  other: []
};

commits.forEach(msg => {
  if (msg.startsWith('feat')) grouped.features.push(msg);
  else if (msg.startsWith('fix')) grouped.fixes.push(msg);
  else if (msg.includes('BREAKING CHANGE')) grouped.breaking.push(msg);
  else if (msg.trim()) grouped.other.push(msg);
});

console.log('## Features\n', grouped.features.join('\n'));
console.log('## Bug Fixes\n', grouped.fixes.join('\n'));
console.log('## Breaking Changes\n', grouped.breaking.join('\n'));
```

### Step 6: Document Merge Conflict Resolution Strategy
Create systematic approach for common conflicts:

**Conflict Pattern 1: Version Numbers**
```
<<<<<<< HEAD (main)
version = "1.2.0"
=======
version = "1.1.5"
>>>>>>> feature/docs-update
```
Resolution: Keep HEAD version (higher), update the feature branch.

**Conflict Pattern 2: Dependencies**
```
<<<<<<< HEAD
"express": "^4.18.0",
"lodash": "^4.17.21"
=======
"express": "^4.17.0",
"react": "^18.0.0"
>>>>>>> feature/new-frontend
```
Resolution: Merge both, test compatibility, update lock file.

**Conflict Pattern 3: Long-lived Feature Branches**
```bash
# Strategy: rebase feature onto main periodically
git checkout feature/large-refactor
git rebase main  # resolve conflicts here
git push origin feature/large-refactor --force-with-lease
```

### Step 7: Configure Merge Strategies and Policies
Define team rules for code integration:

```bash
# Prevent direct pushes to main
git config --local receive.denyDirectPushes true

# Squash commits for cleaner history
git merge --squash feature/user-auth

# Rebase for linear history
git rebase main feature/fix-cache
git checkout main && git merge feature/fix-cache --ff-only
```

## Output Template

```markdown
# Git Workflow Guide for {{project_name}}

## Branch Strategy: {{strategy_type}}

### Main Branches
- **main**: {{main_description}}
- **develop**: {{develop_description}}

### Supporting Branches
- **feature/**: {{feature_description}}
- **bugfix/**: {{bugfix_description}}
- **hotfix/**: {{hotfix_description}}
- **release/**: {{release_description}}

## Conventional Commits

### Format
\`\`\`
{{type}}({{scope}}): {{subject}}

{{body}}

{{footer}}
\`\`\`

### Examples
{{commit_examples}}

## Pull Request Checklist
{{pr_checklist_items}}

## Release Process
1. {{release_step_1}}
2. {{release_step_2}}
3. {{release_step_3}}

## Changelog Generation
\`\`\`bash
{{changelog_script}}
\`\`\`

## Merge Conflict Scenarios
{{conflict_resolutions}}
```

## Quality Gates
- [ ] Branch naming convention follows {type}/{description} format
- [ ] All Conventional Commits follow type(scope): subject pattern
- [ ] PR template includes type, description, testing, and checklist sections
- [ ] Changelog generation script tested with real commits from project history
- [ ] Merge conflict resolution examples match actual patterns in project
- [ ] Strategy document addresses both normal flow and emergency hotfix scenarios

## Examples

### Good Output (excerpt)
```markdown
# Git Workflow for E-commerce Platform

## Branch Strategy: Git Flow

### Main Branches
- **main**: Production-ready code, tagged with semantic versions
- **develop**: Integration branch for next release

### Pull Request Template
Type of Change: Bug fix
Description: Fixed race condition in checkout process
Related Issues: Closes #1203
Testing: Manual testing with 10 concurrent checkouts
Checklist: All items checked ✓
```

### Bad Output (what to avoid)
- Vague commit messages: "fixed stuff", "update code"
- Inconsistent branch names: sometimes `feature-x`, sometimes `feature_x`, sometimes `featurex`
- PR descriptions that are one line with no context
- Changelog with no structure or categories
- Conflict resolution that picks one side without testing compatibility

## Common Mistakes

1. **Mixing Commit Types**: Using "feat" for a documentation-only change (should be "docs"). This breaks changelog automation and misrepresents project velocity.

2. **Long-lived Feature Branches Without Rebasing**: Branches that diverge significantly from main accumulate conflicts and become unmergeable. Solution: rebase frequently (`git rebase origin/main`).

3. **Squashing History Indiscriminately**: Squashing all commits loses granular history and makes bisecting difficult. Solution: squash only when merging to main, preserve meaningful commits on develop.

4. **Ignoring Merge Conflicts Until Emergency**: Resolving conflicts under pressure causes mistakes. Solution: rebase feature branches weekly against main.

5. **No Automated Changelog Testing**: Assuming the changelog script works. Solution: test the script against last 10 releases.

## Anti-Patterns

1. **"Everything to Main" (No Strategy)**: Pushing directly to main with no branch protection, PR reviews, or strategy. Causes unpredictable production states and rollback nightmares.

2. **Commit Messages as Novel Chapters**: Writing commit messages longer than the actual code change. Makes git log unreadable; move details to PR description instead.

3. **Hotfixing Without Process**: Creating hotfixes directly on main without proper tracking or version bumping. Loses audit trail and deploys untested code.

4. **Changelog Maintenance by Hand**: Manually editing CHANGELOG.md for every release. Becomes out of sync, loses automation benefits.

5. **Rebasing Shared Branches**: Running `git rebase` on branches other developers are using, causing "your branch diverged" errors. Only rebase feature branches you own.
