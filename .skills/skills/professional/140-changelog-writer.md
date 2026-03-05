---
name: changelog-writer
description: "Write clear, user-friendly release notes and changelogs following Keep a Changelog format. Translates technical changes into business/user value with migration guidance for breaking changes."
category: professional
difficulty: beginner
model_boost: "Weak models default to technical jargon; this skill ensures user-focused language, clear value communication, and seamless categorization"
---

# Changelog Writer

## Purpose
A changelog is the record of what changed in each software release. Unlike commit messages (technical) or roadmap updates (forward-looking), changelogs answer: "What's new for me as a user, and do I need to do anything?" Clear changelogs reduce support burden (fewer "what changed?" questions), build trust (transparency about improvements and fixes), and help users understand the product evolution. This skill walks you through writing changelogs that are user-friendly, searchable, and actionable.

## When to Use
- Publishing every software release (new features, improvements, bug fixes)
- Documenting breaking changes or migrations needed
- Building a searchable history of product changes
- Communicating product roadmap (what's coming) vs. what shipped
- Marketing product improvements (best changelog entries become blog posts)
- **Do NOT use when**: change is trivial (typo fixes, internal refactors), user-facing impact is zero, or you're releasing without testing (test first, then document)

## Instructions

### Step 1: Understand Changelog Structure and Standards
Follow "Keep a Changelog" format for consistency and findability.

**Standard Categories** (in order):

**Added**: New features or functionality
- "Added dark mode toggle in settings"
- "Added ability to bulk export data to CSV"
- "Added webhook support for project creation events"

**Changed**: Improvements to existing features (not breaking)
- "Improved dashboard loading time by 40%"
- "Redesigned task creation form for clarity"
- "Enhanced email notifications with better formatting"

**Deprecated**: Features that will be removed (advance warning)
- "Deprecated /legacy-api endpoint; migrate to /v2 endpoint by June 1st"
- "Deprecated CSV import; use new data sync feature instead"

**Removed**: Features that are gone
- "Removed Internet Explorer 11 support"
- "Removed deprecated /legacy-api endpoint"

**Fixed**: Bug fixes
- "Fixed typo in welcome email"
- "Fixed date picker not working in Safari"
- "Fixed export failing when dataset exceeds 100K rows"

**Security**: Security improvements or vulnerability fixes
- "Patched SQL injection vulnerability in search"
- "Updated encryption algorithm for API keys"
- "Added two-factor authentication support"

**Versioning**:
Follow Semantic Versioning (SemVer): Major.Minor.Patch (e.g., 1.2.3)
- **Major** (1.x.x): Breaking changes (users must take action)
- **Minor** (x.2.x): New features, backwards-compatible
- **Patch** (x.x.3): Bug fixes, backwards-compatible

**Format**:
```
## [Version] - [YYYY-MM-DD]

### Added
- Feature 1
- Feature 2

### Changed
- Improvement 1
- Improvement 2

### Fixed
- Bug fix 1
- Bug fix 2

### Removed
- Removed feature 1

### Security
- Security fix 1
```

### Step 2: Write User-Focused Descriptions (50-100 words per change)
Avoid technical jargon. Translate features into user benefit.

**Bad Descriptions** (Technical):
- "Refactored Redux state management for scalability"
- "Optimized database queries with eager loading"
- "Implemented OAuth 2.0 refresh token rotation"

**Good Descriptions** (User-Focused):
- "Improved app performance—your dashboard now loads 40% faster, even with thousands of tasks"
- "Fixed slow loading on the analytics page when viewing large datasets"
- "Added automatic account security refreshes—no action needed from you"

**Formula**: [What Changed] + [Why It Matters to User] + [How to Use (if applicable)]

**Examples**:

**Bad**: "Added filtering capability to data export"
**Good**: "Filter your exported data by date, status, or owner before exporting to CSV—saves time when you need specific records"

**Bad**: "Implemented lazy loading for infinite scroll"
**Good**: "Infinite scroll now loads faster—browse your project list without the page freezing"

**Bad**: "Updated API rate limits"
**Good**: "API rate limits increased from 100 to 1,000 requests/minute for all plans—no code changes required"

**Bad**: "Fixed race condition in concurrent operations"
**Good**: "Fixed bug where saving multiple tasks simultaneously would lose data—bulk operations are now reliable"

### Step 3: Highlight Breaking Changes and Migrations (100-200 words per breaking change)
Breaking changes require special attention. Provide migration path and timeline.

**Breaking Change Template**:

**Heading**: Clear and alarming (users need to notice)
"Removed: Internet Explorer 11 Support"
or
"Breaking Change: Redesigned Email API Parameters"

**What Changed**:
"We've discontinued support for Internet Explorer 11. The app will no longer load or function in IE 11; users will see a 'browser not supported' message."

**Why**:
"IE 11 is outdated and unmaintained. Supporting it limits our ability to use modern web technologies and slows development. Removing IE 11 support lets us deliver faster, more secure updates for all users."

**Timeline**:
"IE 11 support ends on [Date]. If you or your users still use IE 11, plan to upgrade to a modern browser (Chrome, Firefox, Safari, Edge)."

**Impact** (specific):
"If you use the email API, your request parameters need updating:
- Old: `{ to_email: 'user@example.com' }`
- New: `{ recipient: { email: 'user@example.com' } }`"

**Migration Guide**:
"See the [Email API Migration Guide] for step-by-step instructions. Most users can update in <30 minutes."

**Support**:
"Need help? Contact support@company.com or visit our [migration FAQ]."

### Step 4: Use Semantic Commit Message Standards
Leverage conventional commits for consistency.

**Format**: `type(scope): description`

**Types** (matching changelog categories):
- `feat`: New feature (Added)
- `fix`: Bug fix (Fixed)
- `docs`: Documentation change
- `style`: Code style (no functional change)
- `refactor`: Code refactoring (no functional change)
- `perf`: Performance improvement (Added or Changed)
- `test`: Test additions
- `ci`: CI/CD changes

**Examples**:
- `feat(dashboard): add dark mode toggle`
- `fix(export): handle large datasets >100K rows`
- `perf(api): reduce response time by 40%`
- `security(auth): add two-factor authentication support`
- `docs(api): update authentication guide`

**Changelog Automation**:
Many tools (Commitizen, semantic-release) auto-generate changelogs from commit messages. If your team uses semantic commits, leverage this—ensures consistency and reduces manual work.

### Step 5: Structure Changelogs by Release with Dates (300-500 words)
Organize chronologically. Include dates for reference.

**Changelog Template** (Full File):

```
# Changelog

All notable changes to [Project] are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
(Features in development, coming in next release)

### Added
- Dark mode toggle in user settings (releasing in v2.1.0)
- Bulk export to Excel (beta, available for Pro+ users)

### Changed
- Redesigned onboarding flow (feedback from user interviews)

---

## [2.0.0] - 2024-01-15

### Added
- **Two-factor authentication**: Secure your account with SMS or authenticator app
- **Custom webhooks**: Subscribe to events and receive HTTP callbacks
- **Bulk import**: Upload CSV with 1,000+ records (instead of 100 limit)
- **Dark mode**: Toggle in Settings → Appearance (thanks to community requests)
- **Collaboration comments**: Comment on tasks and @mention teammates

### Changed
- **Improved dashboard**: Reorganized widgets for faster insights
- **Faster exports**: CSV export is now 50% faster, even for large datasets
- **Enhanced API documentation**: Added more code examples (Python, Go, Node.js)
- **Redesigned settings**: Cleaner interface, easier to find options

### Deprecated
- `/api/v1/projects` endpoint: Use `/api/v2/projects` instead (identical functionality; v1 support ends June 1st, 2024)
- CSV import: Use new bulk import feature instead

### Removed
- Internet Explorer 11 support: Use Chrome, Firefox, Safari, or Edge (released in v1.9.0; fully removed in v2.0.0)
- Deprecated webhook format: Old webhooks will no longer be sent; migrate to new format by June 1st

### Fixed
- **Critical**: Fixed data loss bug when saving multiple tasks simultaneously
- Fixed date picker not working in Safari
- Fixed email notifications missing for @mentions
- Fixed export failing when dataset exceeds 100K rows
- Fixed typo in welcome email ("welcom" → "welcome")

### Security
- Patched SQL injection vulnerability in search (no user action required)
- Upgraded encryption algorithm for stored API keys
- Added rate limiting to prevent abuse (100 requests/min for free users, 1,000 for paid)

---

## [1.9.0] - 2023-12-01

### Added
- **Webhooks beta**: Subscribe to project creation events (more events coming)
- Dark mode (beta): Toggle in Settings (feedback welcome; officially released in v2.0.0)

### Fixed
- Fixed slow loading on analytics page with large datasets
- Fixed email notification formatting issues

---

## [1.8.0] - 2023-11-01

### Added
- Advanced search with filters (status, priority, assignee)
- Export to PDF (in addition to CSV)

### Changed
- Improved performance of dashboard (15% faster load time)

---

[See earlier releases: v1.7.0, v1.6.0, ...]

---

## Guidelines for Maintainers

### Release Checklist
- [ ] Update CHANGELOG.md with all changes
- [ ] Update version number in package.json, pyproject.toml, etc.
- [ ] Run tests (all must pass)
- [ ] Build and test in production-like environment
- [ ] Create git tag: `git tag v2.0.0`
- [ ] Push to remote: `git push origin main && git push origin v2.0.0`
- [ ] Publish to package manager (npm, PyPI, etc.)
- [ ] Send release announcement email
- [ ] Update roadmap with next priorities

### Changelog Writing Standards
- Use active voice ("Added" not "We added"; "Fixed" not "Fixes for")
- Be specific ("Improved dashboard loading by 40%" not "Improved performance")
- Highlight breaking changes prominently
- Include migration guide for any breaking changes
- Thank community contributors
- Group related changes
```

### Step 6: Provide Migration Guides for Major Versions (200-400 words)
Dedicated page for upgrading between major versions.

**Migration Guide Template**:

**Title**: "Migrating from v1 to v2"

**Overview** (50-100 words):
"Version 2 includes significant improvements to API and UI. Most users can upgrade seamlessly; however, some breaking changes require action. This guide walks you through the upgrade process and highlights what changed."

**Prerequisites**:
- Current version: v1.x (specify which versions)
- Estimated migration time: 30 minutes (1 hour if using the API)
- Tools needed: None (except for API users: cURL or SDK)

**Step 1: Update the Application** (50-100 words):
```bash
pip install --upgrade example-api==2.0.0
# or
npm install example-api@2.0.0
# or
Go to Settings → About → Check for Updates
```

**Step 2: Migrate API Calls** (if applicable, 100-200 words):
If you use the API, update your code:

Old (v1):
```python
from example_api import Client
client = Client(api_key="...")
project = client.get_project(project_id="proj_123")
```

New (v2):
```python
from example_api import Client
client = Client(api_key="...")
project = client.projects.get(id="proj_123")
```

See [API Migration Guide] for all endpoint changes.

**Step 3: Verify Everything Works** (50-100 words):
- Log in and verify dashboard loads
- Create a test project
- Test any integrations or scripts
- If errors occur, see [Troubleshooting] or contact support

**Common Issues**:
- "API calls return 404 after upgrade" → Endpoint path changed; see API Migration Guide
- "Dark mode setting is gone" → Moved to Settings → Appearance
- "Webhooks not firing" → Old webhook format discontinued; migrate to new format in Settings

**Still Having Issues?**
Contact support@company.com with your version number and the issue. We're here to help.

### Step 7: Create a Searchable Release Notes Page (150-250 words)
Make changelogs discoverable through search and browser.

**Release Notes Page Structure**:

**URL**: https://company.com/changelog (or /releases, /docs/changelog)

**Search**: Full-text search for changes ("dark mode", "export", "fix", "v2.0.0")

**Filtering**:
- By version
- By category (Added, Fixed, Security, etc.)
- By date range

**Display Options**:
- Chronological view (newest first)
- By version
- Grouped by category across all versions

**Subscribe**:
"Get notified when new releases are available: [RSS feed] | [Email subscription]"

**Archive**:
"Viewing: Latest releases | [See older versions (v1.0+)]"

### Step 8: Write Release Announcement (150-250 words)
Use the changelog to create a blog post or email announcement.

**Email/Blog Announcement Template**:

**Subject Line**: "[v2.0] Dark Mode, Webhooks, and 2FA Now Available"

**Opening**: Hook readers with biggest benefit
"We've released v2.0—our biggest update ever. Dark mode is finally here (you asked for it!), webhooks are ready for integrations, and two-factor authentication keeps your account secure."

**Key Highlights** (3-5 bullets):
- Dark mode (available in Settings)
- Webhooks for automations
- Two-factor authentication
- 40% faster exports
- See [full changelog] for all changes

**What You Need to Do** (if anything):
"Most users can upgrade automatically. If you use our API, [see the migration guide] for endpoint changes. IE 11 users: please upgrade your browser."

**Questions?**
"Check [FAQ], see [migration guide], or email support@company.com."

**Call-to-Action**:
"Try the new dark mode and let us know what you think in the comments!"

## Output Template

```
---
project_name: "[Project Name]"
changelog_version: "[YYYY-MM-DD]"
current_version: "[e.g., 2.0.0]"
semver_format: "Major.Minor.Patch"
---

# Changelog

All notable changes to [Project Name] are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- [Feature in development]

### Changed
- [Improvement in development]

---

## [Version] - [YYYY-MM-DD]

### Added
- [Feature 1]
- [Feature 2]

### Changed
- [Improvement 1]
- [Improvement 2]

### Deprecated
- [Deprecated feature 1]

### Removed
- [Removed feature 1]

### Fixed
- [Bug fix 1]
- [Bug fix 2]

### Security
- [Security fix 1]

---

## [Earlier Versions]

[Version history continues...]

---

## Migration Guides
- [v1 → v2 Migration Guide]
- [v0 → v1 Migration Guide]

---

## Release Notes and Announcements
- [v2.0 Release Announcement Blog Post]
- [Previous Announcements Archive]
```

## Quality Gates
1. **User-Focused Language**: Does each change entry explain why it matters to users, not just technical implementation?
2. **Breaking Change Clarity**: Are breaking changes prominently marked with migration guidance?
3. **Completeness**: Does changelog cover all user-facing changes (including bug fixes)?
4. **Consistency**: Are categories, formatting, and language consistent across all entries?
5. **Searchability**: Can users find information about specific features or fixes?
6. **Dates and Versions**: Is every release dated and versioned consistently (SemVer)?
7. **Timeliness**: Is changelog updated with every release (not months behind)?

## Examples

### Good Changelog Entry
"Added dark mode toggle in Settings → Appearance—reduces eye strain in low-light environments. Toggle anytime; your preference syncs across devices."

**Why this works**: User benefit (eye strain), feature location, how to use it, additional value (syncs across devices).

### Bad Changelog Entry
"Implemented dark mode feature"

**Why this fails**: No user benefit, no location, no instruction.

### Good Breaking Change Entry
"Removed: Internet Explorer 11 Support
We've discontinued IE 11 support to enable faster development of modern features. IE 11 users will see 'browser not supported' message. Action: Upgrade to Chrome, Firefox, Safari, or Edge (all free). Migration timeline: Support ends March 1st, 2024."

**Why this works**: Clear what changed, why, impact, action, timeline.

### Bad Breaking Change Entry
"IE 11 support removed in v2.0.0"

**Why this fails**: No context, no action, no timeline, no migration path.

## Common Mistakes

1. **Technical Jargon** — "Refactored Redux state management" without explaining user benefit. Solution: "Improved app responsiveness—actions now feel snappier" (translate to user benefit).

2. **Missing Breaking Changes** — Breaking change mentioned casually in "Fixed" section instead of prominently highlighted. Users miss it. Solution: Mark breaking changes in separate section with migration guide.

3. **Vague Descriptions** — "Improved performance" without specifics. Solution: Be specific. "Improved dashboard loading by 40%" tells users exactly what changed.

4. **Dates Missing** — No date on releases. Users don't know when something shipped. Solution: Include date (YYYY-MM-DD) for every release.

5. **Not Updated Regularly** — Changelog is 6 months behind actual releases. Users can't find recent changes. Solution: Update immediately after release (automate if possible with semantic commits).

6. **Everything in "Fixed"** — All changes lumped into "Fixed" category. Users can't scan for new features. Solution: Use proper categories (Added, Changed, Deprecated, Removed, Fixed, Security).

## Anti-Patterns

1. **The Excuse Changelog** — Full of apologies ("We fixed the bug we introduced") and explanations. Focuses on what went wrong, not what's better. Anti-pattern: "We had a critical bug in v1.8.0 that deleted data. We deeply apologize. Here's the fix." Better: "Fixed critical bug where saving multiple tasks simultaneously would lose data. Upgrade immediately."

2. **The Hidden Breaking Change** — Major breaking change buried in "Changed" section as if it's optional. Users miss it. Anti-pattern: "Changed API response format" (no migration guide). Better: "BREAKING: API response format changed. See [migration guide]. Old format supported until June 1st."

3. **The Feature Dump** — 50+ features listed under "Added" with no context. Users scroll past. Anti-pattern: "Added 47 features" without details. Better: Highlight top 3-5 features; link to detailed list.

4. **The Inactive Changelog** — Last update 2 years ago. Users assume project is dead. Anti-pattern: Not updating changelog for months. Better: Update with every release, even if just bug fixes.

5. **The Blame Game** — Changelog focused on what users did wrong or how they misused the product. Anti-pattern: "Fixed user error where they entered dates in wrong format." Better: "Improved date input validation—now accepts multiple date formats (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD)."
