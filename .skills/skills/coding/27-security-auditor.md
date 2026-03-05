---
name: security-auditor
description: "Audit applications for OWASP Top 10 vulnerabilities, dependency scanning, auth/authz, input validation, secrets management, CSP headers, and rate limiting with remediation guidance."
category: coding
difficulty: advanced
model_boost: "Weak models miss critical vulnerabilities or suggest incomplete security fixes"
---

# Security Auditor

## Purpose
This skill systematically audits applications for security vulnerabilities following OWASP Top 10 guidelines. It covers vulnerability identification using static analysis, dependency vulnerability scanning, authentication and authorization review, input validation and output encoding, secrets management, Content Security Policy implementation, rate limiting, and threat modeling. Output includes specific vulnerabilities with proof-of-concept exploits and practical remediation steps, enabling engineering teams to prioritize security fixes by impact.

## When to Use
- Conducting security reviews before major deployments
- Investigating security incident root causes
- Implementing compliance requirements (SOC2, HIPAA, PCI-DSS)
- Onboarding new third-party services and dependencies
- Establishing security baselines for applications
- Remediating reported security vulnerabilities
- **Do NOT use when**: Penetration testing requires legal authorization and scope definition outside this skill

## Instructions

### Step 1: Identify OWASP Top 10 Vulnerabilities
Systematically check for common vulnerability categories:

**A1: Broken Access Control**
```
Vulnerability Examples:
├── Missing authorization checks
│   ├── User A accesses User B's profile: GET /api/users/user_b_id
│   ├── User A modifies User B's settings: PATCH /api/users/user_b_id
│   └── Non-admin user accesses admin dashboard
├── Horizontal privilege escalation
│   └── User 1 changes their user_id in URL to access user_2 data
└── Vertical privilege escalation
    └── Regular user bypasses to get admin functionality

Detection:
function getUserProfile(req, res) {
  const userId = req.params.id;
  // BUG: No check that userId matches authenticated user
  const user = db.query('SELECT * FROM users WHERE id = ?', [userId]);
  res.json(user);
}

Remediation:
function getUserProfile(req, res) {
  const userId = req.params.id;
  const authenticatedUserId = req.user.id;

  // FIXED: Verify user accessing their own data
  if (userId !== authenticatedUserId && !req.user.isAdmin) {
    return res.status(403).json({ error: 'Unauthorized' });
  }

  const user = db.query('SELECT * FROM users WHERE id = ?', [userId]);
  res.json(user);
}
```

**A2: Cryptographic Failures**
```
Vulnerability Examples:
├── Data in transit unencrypted
│   └── HTTP instead of HTTPS; credentials sent over plain text
├── Weak encryption algorithm
│   └── MD5, DES for password hashing
├── Hard-coded secrets
│   └── API keys in source code, .env in git
└── No encryption at rest
    └── Sensitive database data stored unencrypted

Detection:
// BUG: MD5 hashing (cryptographically broken)
const hash = crypto.createHash('md5').update(password).digest('hex');

// BUG: Hard-coded secret
const apiKey = 'sk-1234567890abcdef';

Remediation:
// FIXED: bcrypt hashing with salt rounds
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(password, 10);

// FIXED: Secret from environment variable
const apiKey = process.env.API_KEY;
if (!apiKey) throw new Error('API_KEY not set');

// FIXED: Enable HTTPS only
app.use((req, res, next) => {
  if (req.header('x-forwarded-proto') !== 'https') {
    res.redirect(301, `https://${req.header('host')}${req.url}`);
  } else {
    next();
  }
});
```

**A3: Injection (SQL, Command, LDAP)**
```
Vulnerability Examples:
├── SQL Injection
│   ├── User input directly in SQL query
│   └── SELECT * FROM users WHERE email = '${email}'
├── Command Injection
│   ├── User input to shell commands
│   └── shell.exec('ping ' + userInput)
└── XSS (Cross-Site Scripting)
    ├── User input rendered without escaping
    └── <div>{userProvidedHtml}</div> in React

Detection:
// BUG: SQL Injection
function getUserByEmail(email) {
  return db.query(`SELECT * FROM users WHERE email = '${email}'`);
}
// Attack: email = "' OR '1'='1"

Remediation:
// FIXED: Parameterized queries
function getUserByEmail(email) {
  return db.query('SELECT * FROM users WHERE email = ?', [email]);
}

// FIXED: XSS Prevention (HTML encode output)
function renderUserComment(comment) {
  const encoded = escapeHtml(comment);
  return <div>{encoded}</div>;
}

// FIXED: Using DOMPurify for user-provided HTML
import DOMPurify from 'dompurify';
const cleanHtml = DOMPurify.sanitize(userProvidedHtml);
```

**A4: Insecure Design (Missing Security Controls)**
```
Detection: Missing threat model, attack surface not documented

Remediation:
// Add rate limiting to prevent brute force
const rateLimit = require('express-rate-limit');
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 5,  // 5 attempts
  message: 'Too many login attempts, try again later'
});
app.post('/login', loginLimiter, handleLogin);

// Add CSRF protection
const csrf = require('csurf');
app.use(csrf({ cookie: true }));

// Implement account lockout
const maxAttempts = 5;
const lockoutTime = 15 * 60 * 1000;  // 15 minutes
```

**A5: Broken Authentication**
```
Vulnerability Examples:
├── Weak passwords (no policy)
├── Session fixation (same session ID after login)
├── No password expiration
├── Hardcoded credentials
└── No multi-factor authentication

Detection:
// BUG: No password strength requirements
if (password.length < 3) return error('Too short');

// BUG: Weak session management
session.id = Math.random();  // Not cryptographically secure

Remediation:
// FIXED: Password strength requirements
const passwordStrength = (password) => {
  const rules = [
    password.length >= 12,
    /[A-Z]/.test(password),  // Uppercase
    /[a-z]/.test(password),  // Lowercase
    /[0-9]/.test(password),  // Number
    /[!@#$%^&*]/.test(password)  // Special char
  ];
  return rules.filter(Boolean).length >= 4;
};

// FIXED: Secure session IDs
const sessionId = crypto.randomBytes(32).toString('hex');

// FIXED: JWT with expiration
const token = jwt.sign(
  { userId: user.id },
  process.env.JWT_SECRET,
  { expiresIn: '1h' }  // Token expires after 1 hour
);

// FIXED: Multi-factor authentication
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (!user) return res.status(401).json({ error: 'Invalid credentials' });

  // Send OTP to user's phone
  const otp = generateOTP();
  await sendSMS(user.phone, otp);

  res.json({ message: 'OTP sent', requiresOTP: true });
});
```

**A6: Software and Data Integrity Failures**
```
Detection:
- Insecure deserialization of untrusted data
- No integrity checks on downloaded libraries
- Unsigned container images or artifacts

Remediation:
// Verify npm package integrity
npm ci --audit
npm audit --production

// Verify container image signatures
docker trust inspect image_name

// Use lock files to ensure reproducible builds
// package-lock.json or poetry.lock
```

**A7: Identification and Authentication Failures**
```
Detection: Session management vulnerabilities

Remediation:
// Secure cookie settings
res.cookie('sessionId', sessionId, {
  httpOnly: true,     // Not accessible to JavaScript
  secure: true,       // HTTPS only
  sameSite: 'strict', // CSRF protection
  maxAge: 3600000     // 1 hour expiration
});

// Regenerate session ID after login (prevent session fixation)
req.session.regenerate((err) => {
  req.session.userId = user.id;
  res.json({ success: true });
});
```

**A8: Software and Data Integrity Failures**
```
Detection: Using insecure dependencies

Remediation:
npm audit  # Check for known vulnerabilities
npm audit fix  # Auto-fix where possible

# In CI/CD:
dependencies:
  script:
    - npm audit --production
```

**A9: Logging and Monitoring Failures**
```
Detection: No logging of security events

Remediation:
// Log authentication events
logger.warn('Failed login attempt', {
  email: req.body.email,
  ip: req.ip,
  timestamp: new Date()
});

// Log unauthorized access attempts
logger.error('Unauthorized access attempt', {
  userId: req.user.id,
  attemptedResource: req.path,
  ip: req.ip
});

// Monitor for suspicious patterns
const failedLogins = await db.query(`
  SELECT ip, COUNT(*) as attempts
  FROM login_attempts
  WHERE status = 'failed'
  AND created_at > NOW() - INTERVAL '15 minutes'
  GROUP BY ip
  HAVING COUNT(*) > 5
`);
```

**A10: Server-Side Request Forgery (SSRF)**
```
Detection:
// BUG: User-provided URL used in server request
app.get('/proxy', async (req, res) => {
  const url = req.query.url;  // User controls this
  const response = await fetch(url);
  res.json(response);
});

Remediation:
// FIXED: Whitelist allowed domains
const ALLOWED_DOMAINS = ['api.example.com', 'data.example.com'];
const url = new URL(req.query.url);

if (!ALLOWED_DOMAINS.includes(url.hostname)) {
  return res.status(403).json({ error: 'Domain not allowed' });
}

const response = await fetch(url);
res.json(response);
```

### Step 2: Scan Dependencies for Vulnerabilities
Automated detection of known vulnerabilities:

```bash
# npm projects
npm audit  # Built-in vulnerability scanner
npm audit fix  # Auto-fix where possible

# For specific severity threshold
npm audit --production --audit-level=moderate

# Python projects
pip install safety
safety check  # Scans requirements.txt for known vulnerabilities

# Or use pip-audit
pip install pip-audit
pip-audit

# Ruby projects
bundle exec bundler-audit check

# General vulnerability database
# OWASP Dependency-Check (multi-language)
dependency-check --project MyApp --scan .

# Snyk (comprehensive SCA tool)
snyk test  # Scan for vulnerabilities
snyk monitor  # Continuous monitoring
```

### Step 3: Implement Input Validation and Output Encoding
Prevent injection attacks:

```javascript
// Input Validation (allowlist approach)
function validateEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) {
    throw new Error('Invalid email format');
  }
  return email;
}

function validatePostalCode(code) {
  if (!/^\d{5}(-\d{4})?$/.test(code)) {
    throw new Error('Invalid postal code');
  }
  return code;
}

// Output Encoding (prevent XSS)
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, char => map[char]);
}

// Sanitize for database (parameterized queries)
function getUserByUsername(username) {
  return db.query('SELECT * FROM users WHERE username = ?', [username]);
}

// Content Security Policy (prevent XSS)
app.use((req, res, next) => {
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.example.com; style-src 'self' 'unsafe-inline'"
  );
  next();
});
```

### Step 4: Audit Authentication and Authorization
Verify access control implementation:

```typescript
// Authentication: Verify user identity
async function authenticateUser(email: string, password: string) {
  const user = await db.query('SELECT * FROM users WHERE email = ?', [email]);
  if (!user) return null;

  const isValid = await bcrypt.compare(password, user.passwordHash);
  return isValid ? user : null;
}

// Authorization: Verify user has permission
async function authorizeAction(
  userId: string,
  action: string,
  resource: string
): Promise<boolean> {
  const user = await db.query('SELECT roles FROM users WHERE id = ?', [userId]);
  const permissions = await db.query(
    'SELECT permissions FROM roles WHERE name IN (?)',
    [user.roles]
  );

  const hasPermission = permissions.some(
    p => p.action === action && p.resource === resource
  );

  if (!hasPermission) {
    logger.warn('Unauthorized action', { userId, action, resource });
  }

  return hasPermission;
}

// Middleware to enforce authorization
app.delete('/api/posts/:id', async (req, res) => {
  const post = await db.query('SELECT * FROM posts WHERE id = ?', [req.params.id]);

  // Check: is user the post owner or admin?
  const isAuthorized =
    post.userId === req.user.id ||
    req.user.roles.includes('admin');

  if (!isAuthorized) {
    return res.status(403).json({ error: 'Forbidden' });
  }

  await db.query('DELETE FROM posts WHERE id = ?', [req.params.id]);
  res.json({ success: true });
});
```

### Step 5: Implement Secrets Management
Protect API keys and credentials:

```bash
# .env file (LOCAL DEVELOPMENT ONLY)
# Never commit to git; add to .gitignore
DATABASE_URL=postgresql://user:pass@localhost/db
API_KEY=sk_test_1234567890
JWT_SECRET=super-secret-key-never-share

# Production: Use environment variables from secret management service
# AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id prod/db-password

# Azure Key Vault
az keyvault secret show --name db-password --vault-name prod-vault

# Hashicorp Vault
vault kv get secret/prod/database
```

**Secure Secrets in Code:**
```javascript
// WRONG: Secret in code
const apiKey = 'sk_live_1234567890';

// CORRECT: Load from environment
const apiKey = process.env.API_KEY;
if (!apiKey) {
  throw new Error('API_KEY environment variable not set');
}

// Rotate secrets regularly
// Implement automated secret rotation
const rotateSecrets = async () => {
  const newApiKey = await generateNewApiKey();
  await updateSecretsManager(newApiKey);
  logger.info('API key rotated successfully');
};
```

### Step 6: Configure Security Headers
Implement defense-in-depth HTTP headers:

```javascript
// Helmet.js helps set many security headers
const helmet = require('helmet');
app.use(helmet());

// Or manually configure
app.use((req, res, next) => {
  // Prevent MIME type sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');

  // Enable XSS protection
  res.setHeader('X-XSS-Protection', '1; mode=block');

  // Prevent clickjacking
  res.setHeader('X-Frame-Options', 'DENY');

  // Content Security Policy (prevent XSS)
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self' cdn.example.com; style-src 'self' 'unsafe-inline'"
  );

  // HSTS (force HTTPS)
  res.setHeader(
    'Strict-Transport-Security',
    'max-age=31536000; includeSubDomains'
  );

  next();
});
```

### Step 7: Implement Rate Limiting and DDoS Protection
Protect against abuse:

```javascript
// Rate limiting per IP
const rateLimit = require('express-rate-limit');

const limiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100,  // 100 requests per windowMs
  message: 'Too many requests from this IP'
});

app.use(limiter);

// Stricter limit for login endpoint
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,  // 5 attempts
  skipSuccessfulRequests: true  // Don't count successful logins
});

app.post('/login', loginLimiter, handleLogin);

// Redis-backed rate limiting for distributed systems
const RedisStore = require('rate-limit-redis');
const redis = require('redis').createClient();

const limiter = rateLimit({
  store: new RedisStore({
    client: redis,
    prefix: 'rate-limit:'
  }),
  windowMs: 15 * 60 * 1000,
  max: 100
});
```

## Output Template

```markdown
# Security Audit Report: {{application_name}}

## Executive Summary
- Critical Vulnerabilities: {{count}}
- High Severity: {{count}}
- Medium Severity: {{count}}

## Findings

### 1. {{Vulnerability Title}} (CRITICAL)
- OWASP Category: {{category}}
- Description: {{description}}
- Proof of Concept: {{poc}}
- Impact: {{impact}}
- Remediation:
  ```
  {{fix_code}}
  ```

## Dependency Analysis
- Direct Dependencies: {{count}}
- Vulnerable Dependencies: {{count}}
- Outdated Dependencies: {{count}}

## Recommendations
1. {{priority_1}}
2. {{priority_2}}
3. {{priority_3}}

## Checklist
- [ ] All OWASP Top 10 reviewed
- [ ] Dependencies scanned for vulnerabilities
- [ ] Auth/authz implementation verified
- [ ] Input validation and output encoding checked
- [ ] Security headers configured
- [ ] Rate limiting implemented
- [ ] Secrets properly managed
```

## Quality Gates
- [ ] All 10 OWASP Top 10 categories examined
- [ ] Dependency vulnerability scan completed with results
- [ ] Authentication and authorization flows documented and verified
- [ ] Input validation patterns tested with malicious payloads
- [ ] Output encoding verified to prevent XSS
- [ ] Security headers configured and tested (use security.txt header checker)
- [ ] Secrets management approach documented
- [ ] Rate limiting configured for at least login endpoints
- [ ] Logging captures security events (auth attempts, access denials)
- [ ] Recommendations prioritized by severity and effort

## Examples

### Good Output (excerpt)
```markdown
# Security Audit: Payment Service

## A1: Broken Access Control (CRITICAL)
User can access another user's payment history by changing user_id in URL.

### Proof of Concept
GET /api/users/123/payments
# Returns payments for user_id=123, regardless of authenticated user

### Remediation
Add authorization check in middleware:
```javascript
app.get('/api/users/:id/payments', (req, res) => {
  if (req.params.id !== req.user.id && !req.user.isAdmin) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  // Continue...
});
```

### Impact
- Critical: Exposure of payment history for all users
- Affects: Confidentiality, regulatory compliance (PCI-DSS)
```

### Bad Output (what to avoid)
```
# Security Audit

"The code has some security issues. Use HTTPS and authentication. Update dependencies."

# Problems:
- Vague findings
- No specific vulnerabilities
- No proof of concept
- No remediation steps
- No prioritization
```

## Common Mistakes

1. **Only Scanning Dependencies, Ignoring Application Code**: 3rd-party libraries are updated regularly, but application vulnerabilities stay for years. SQL injection in custom code is worse than outdated library. Solution: Scan both code and dependencies.

2. **Treating All Vulnerabilities as Equal**: Severity varies from low (update advisory) to critical (data breach). Spending time on low-severity issues while ignoring critical ones wastes resources. Solution: Prioritize by severity and impact.

3. **Fixing Without Understanding Root Cause**: Applying quick patch without understanding how vulnerability existed. New developer introduces same vulnerability 6 months later. Solution: Document root cause and add preventive controls (code review, testing).

4. **No Verification After Fix**: Applying fix, assuming problem solved, no testing to confirm. Vulnerability still exists. Solution: Write security test case proving vulnerability exists before fix, verify test passes after.

5. **Secrets in Environment Without Rotation**: API key set in environment, forgotten. Key exposed in data breach months later; attacker uses key for days before discovery. Solution: Implement automatic secret rotation.

6. **Rate Limiting Without Monitoring**: Rate limiting configured, but no alerts when limit is reached. Brute force attack happens over 2 weeks; discovered only when account locked. Solution: Alert on repeated rate limit hits.

## Anti-Patterns

1. **Security as Afterthought**: Building features first, adding security later. Retrofitting security is 10x more expensive. Security must be part of design from start.

2. **Blacklist Instead of Whitelist**: Blocking known bad inputs ("avoid characters: <, >, &"). Attacker finds new encoding ("<" encoded as "&#60;"). Solution: Whitelist allowed characters/patterns.

3. **Single Security Layer**: Only using HTTPS, only using firewalls, only using rate limiting. One bypass defeats entire defense. Solution: Defense in depth (multiple layers).

4. **Security Theater Without Testing**: Implementing security controls but never testing if they work. "We have WAF" but WAF misconfigured. Solution: Penetration testing and continuous security validation.

5. **No Audit Trail**: No logging of security events. Breach happens; no way to know what was accessed. Solution: Comprehensive audit logging with retention.

6. **Ignoring Error Messages**: Exception details exposed to users (database errors, stack traces). Reveals system architecture to attackers. Solution: Generic error messages to users, detailed logging internally.
