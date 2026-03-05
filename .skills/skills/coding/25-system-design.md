---
name: system-design
description: "Generate comprehensive system design documents covering requirements analysis, architecture diagrams (C4 model), data flow, scaling strategies, trade-offs, and monitoring plans."
category: coding
difficulty: advanced
model_boost: "Weak models produce incomplete system designs missing scalability or monitoring considerations"
---

# System Design

## Purpose
This skill generates production-ready system design documents that translate business requirements into scalable architecture. It covers requirements gathering and analysis, visual architecture using the C4 model (Context, Container, Component, Code levels), data flow and communication patterns, database design and schema, scaling strategies for traffic growth, architectural trade-offs (CAP theorem, synchronous vs. asynchronous), deployment topology, and comprehensive monitoring and observability planning. Output documents are suitable for engineering teams, stakeholders, and serve as blueprints for implementation.

## When to Use
- Designing new systems or major features at scale
- Planning architectural refactoring or technology migration
- Documenting existing systems for knowledge transfer
- Evaluating trade-offs between technologies or approaches
- Planning for growth and scalability before building
- Creating design review documents for stakeholder approval
- **Do NOT use when**: Designing simple CRUD applications, or making tactical code-level decisions

## Instructions

### Step 1: Gather and Analyze Requirements
Understand business and technical requirements:

```markdown
## Functional Requirements
1. User Registration & Authentication
   - Email/password signup
   - JWT token-based authentication
   - Multi-factor authentication optional
   - OAuth 2.0 integration (Google, GitHub)

2. Content Management
   - Create, read, update, delete posts
   - Support markdown, images, and embeds
   - Version history tracking
   - Collaborative editing (live cursors)

## Non-Functional Requirements
- Availability: 99.9% uptime (SLA)
- Latency: <100ms p99 for API endpoints
- Throughput: 10,000 requests/second peak
- Data Consistency: Strong consistency for financial data, eventual consistency acceptable for caches
- Compliance: GDPR, PCI-DSS if handling payments
- Scalability: Support 1M+ concurrent users
- Disaster Recovery: RPO <1 hour, RTO <4 hours
```

### Step 2: Create C4 Model Architecture Diagrams
Visualize system at multiple abstraction levels:

**Level 1: System Context**
```
User → [YourSystem] → External Services
           ↓
     Database
```

**Level 2: Container Diagram**
```
    ┌─────────────┐
    │  Browser    │
    └──────┬──────┘
           │
    ┌──────▼──────────┐         ┌──────────────┐
    │  Web Server     │────────→│  PostgreSQL  │
    │  (Node.js)      │         └──────────────┘
    └──────┬──────────┘
           │
    ┌──────▼──────────┐         ┌──────────────┐
    │  API Gateway    │────────→│  Redis Cache │
    │  (Kong/Nginx)   │         └──────────────┘
    └──────┬──────────┘
           │
    ┌──────▼──────────┐         ┌──────────────┐
    │ Job Queue       │────────→│  Workers     │
    │ (RabbitMQ)      │         │ (Async Jobs) │
    └─────────────────┘         └──────────────┘
```

**Level 3: Component Diagram (within Web Server)**
```
API Layer
├── UserController
├── PostController
└── AuthController

Service Layer
├── UserService
├── PostService
├── AuthService
└── NotificationService

Data Access Layer
├── UserRepository
├── PostRepository
└── CommentRepository

External Integrations
├── EmailProvider
├── S3 Storage
└── OAuth Handler
```

### Step 3: Define Data Model and Database Schema
Design data persistence layer:

```sql
-- Users Table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(50) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX (email),
  INDEX (username)
);

-- Posts Table
CREATE TABLE posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at TIMESTAMP,
  view_count INT DEFAULT 0,
  INDEX (user_id),
  INDEX (published_at DESC),
  INDEX (created_at DESC)
);

-- Comments Table
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX (post_id),
  INDEX (user_id),
  INDEX (created_at DESC)
);

-- Follows Table (for social features)
CREATE TABLE follows (
  follower_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  following_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, following_id),
  INDEX (following_id)
);
```

### Step 4: Define API Contracts and Communication Patterns
Specify service communication:

```typescript
// API Request/Response Examples
POST /api/v1/posts
Content-Type: application/json
Authorization: Bearer {jwt_token}

{
  "title": "My First Post",
  "content": "This is markdown content",
  "published": true
}

Response 201 Created:
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "title": "My First Post",
  "slug": "my-first-post",
  "published_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-15T10:30:00Z"
}

// Error Response
Response 400 Bad Request:
{
  "error": "VALIDATION_ERROR",
  "message": "Title is required",
  "details": {
    "title": "Title must be at least 3 characters"
  }
}
```

**Service-to-Service Communication:**
```
Synchronous (HTTP/gRPC):
├── API Gateway → User Service (user lookup)
├── API Gateway → Post Service (create post)
└── Post Service → Notification Service (notify followers)

Asynchronous (Message Queue):
├── Post Service → RabbitMQ (post created event)
├── Worker Service → RabbitMQ (consume post event)
├── Worker → Elasticsearch (index post)
└── Worker → Cache (update user's post count)
```

### Step 5: Plan Scaling Strategies
Design system for growth:

**Vertical Scaling (Single Server):**
```
- Increasing CPU, RAM, storage
- Limited to hardware capacity
- Single point of failure
- Used for: development, small startup (<10k users)
```

**Horizontal Scaling (Multiple Servers):**
```
Load Balancer (Nginx/HAProxy)
    │
    ├─→ Server 1 (Port 3000)
    ├─→ Server 2 (Port 3000)
    ├─→ Server 3 (Port 3000)
    └─→ Server 4 (Port 3000)

Shared Resources:
    ├─ PostgreSQL (Primary + Replicas for reads)
    ├─ Redis Cluster (distributed cache)
    └─ Elasticsearch (distributed search)
```

**Database Scaling:**
```
Read Replicas Strategy:
- Primary (write-only): handles all writes, backups
- Read Replicas (1-N): handle all read queries
- Replication lag: typically 10-100ms

Sharding Strategy (for 100M+ records):
├── By User ID (user-based sharding)
│   └── Shard 1: Users 1-999,999
│   └── Shard 2: Users 1,000,000-1,999,999
│   └── Shard 3: Users 2,000,000-2,999,999
└── By Time (date-based sharding)
    └── posts_2024_01
    └── posts_2024_02
    └── posts_2024_03
```

**Caching Strategy:**
```
L1: Browser Cache (static assets)
    ├── Expiry: 1 year for versioned files
    └── Expiry: 1 hour for index.html

L2: CDN Cache (CloudFront/Cloudflare)
    ├── Images, CSS, JS: 1 year
    ├── API responses: 5 minutes
    └── HTML: 1 minute

L3: In-Memory Cache (Redis)
    ├── User profiles: 1 hour
    ├── Post metadata: 30 minutes
    ├── Hot posts (top 10k): 5 minutes
    └── Rate limit counters: 1 minute

Invalidation:
    └── Cache-aside: application checks cache, loads from DB if missing
    └── Write-through: application writes to cache and DB simultaneously
    └── Write-behind: application writes to cache, async flush to DB
```

### Step 6: Document Trade-offs and Decisions
Explain architectural choices:

**Consistency Models:**
```
Strong Consistency:
- All users see same data immediately
- Required for: financial transactions, inventory
- Cost: reduced availability, increased latency
- Example: Credit card transactions

Eventual Consistency:
- Users may see stale data temporarily
- Required for: social media feeds, metrics
- Cost: eventual consistency window (seconds to minutes)
- Example: user follower counts, post likes

Quorum Reads/Writes:
- Write to N/2+1 replicas, read from N/2+1
- Guarantees consistency if quorum overlaps
- Cost: increased latency, complex logic
- Example: Apache Cassandra, Riak
```

**Synchronous vs. Asynchronous:**
```
Synchronous (API Call):
✓ Immediate response
✓ Strong consistency
✗ Slower (network round-trip)
✗ Less resilient (timeout = failure)
Use for: payments, user authentication

Asynchronous (Message Queue):
✓ Faster (returns immediately)
✓ Resilient (queue buffers spikes)
✓ Decoupled (service can be offline)
✗ Eventually consistent
✗ More complex (retry logic, dead letters)
Use for: email, notifications, analytics
```

**Monolith vs. Microservices:**
```
Monolith:
✓ Simple deployment
✓ Easy debugging
✓ Good performance (in-process calls)
✗ Hard to scale parts independently
✗ Technology lock-in
✗ One bug can crash everything

Microservices:
✓ Independent scaling
✓ Technology flexibility
✓ Easier to maintain large systems
✗ Network latency
✗ Distributed debugging complexity
✗ Data consistency challenges
```

### Step 7: Design Monitoring and Observability
Plan system observability:

```yaml
# Monitoring Strategy
Metrics:
  Application Level:
    - API response time (histogram)
    - Request rate (counter)
    - Error rate by endpoint (gauge)
    - Queue depth (gauge)
    - Cache hit ratio (gauge)
    - Database query latency (histogram)

  Infrastructure Level:
    - CPU, Memory, Disk usage
    - Network I/O
    - Database connections
    - File descriptors

Logging:
  Structured Logging (JSON):
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "ERROR",
      "service": "post-service",
      "trace_id": "abc123def456",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "message": "Failed to publish post",
      "error": "Database timeout",
      "context": {
        "post_id": "xyz",
        "attempt": 2
      }
    }

  Log Aggregation:
    - ELK Stack (Elasticsearch, Logstash, Kibana)
    - or CloudWatch, Datadog, New Relic

Tracing:
  Distributed Tracing (Jaeger, Zipkin):
    - Trace ID: uniquely identifies request across services
    - Span ID: identifies single operation
    - Shows latency at each service
    - Helps identify bottlenecks in request path

Alerting:
  Critical:
    - Error rate > 1%
    - API p99 latency > 500ms
    - Database connection pool exhausted
    - Disk usage > 90%

  Warning:
    - Error rate > 0.1%
    - API p95 latency > 200ms
    - Cache hit ratio < 70%
    - Queue depth > 10,000
```

## Output Template

```markdown
# System Design: {{system_name}}

## 1. Requirements
### Functional Requirements
{{functional_requirements}}

### Non-Functional Requirements
{{non_functional_requirements}}

## 2. High-Level Architecture
{{c4_level_1_diagram}}

## 3. Container Architecture
{{c4_level_2_diagram}}

## 4. Component Design
{{c4_level_3_diagram}}

## 5. Data Model
{{database_schema_with_indexes}}

## 6. API Contracts
{{api_examples}}

## 7. Scaling Strategy
{{scaling_approach}}

## 8. Trade-offs
{{architectural_decisions}}

## 9. Monitoring & Observability
{{metrics_logging_tracing}}

## 10. Deployment & Infrastructure
{{deployment_topology}}
```

## Quality Gates
- [ ] All functional and non-functional requirements clearly documented
- [ ] C4 model diagrams provided at all four levels (Context, Container, Component, Code)
- [ ] Database schema includes primary keys, foreign keys, and appropriate indexes
- [ ] API contracts documented with request/response examples and error codes
- [ ] Scaling strategy addresses both vertical and horizontal scaling
- [ ] Consistency model explicitly chosen (strong, eventual, or quorum)
- [ ] Synchronous vs. asynchronous patterns defined for each interaction
- [ ] Monitoring plan includes metrics, logs, traces, and alerting thresholds
- [ ] Disaster recovery plan with RPO and RTO specified
- [ ] Technology choices justified with trade-offs explained

## Examples

### Good Output (excerpt)
```markdown
# System Design: Social Media Platform

## Non-Functional Requirements
- Availability: 99.99% SLA (52.6 minutes downtime/year)
- Latency: p99 < 100ms for feed requests
- Throughput: 100k requests/second peak
- Users: 100 million concurrent users

## Scaling Strategy
- Horizontal: Load balancer routes to 50+ servers
- Database: PostgreSQL primary + 10 read replicas
- Cache: Redis Cluster with 5 nodes for hot data
- CDN: CloudFront for static assets (images, videos)

## Trade-offs: Eventual Consistency for Feed
- Decision: Accept 1-5 minute delay in follower feed updates
- Rationale: Strong consistency would require distributed transactions
- Impact: Users see posts they authored immediately, others see with delay
- Monitoring: Track consistency lag metric, alert if > 10 minutes
```

### Bad Output (what to avoid)
```markdown
# System Design: Social Media Platform

We'll use PostgreSQL for everything. The server handles all requests.
Add Redis for caching.
Monitoring: use CloudWatch.

# Problems:
- No scalability plan
- No database schema
- No API contracts
- No trade-off analysis
- Vague monitoring plan
```

## Common Mistakes

1. **Designing for Current Scale Instead of Future Scale**: Building system that works for 1k users but needs complete rewrite at 100k users. Solution: Design for 10x current scale from start; avoid rearchitecting every 6 months.

2. **Ignoring Network Partitions in Distributed Systems**: Assuming network calls always succeed. In reality, 1-2 networks partitions happen yearly per data center. Entire system becomes unavailable. Solution: Design for partition tolerance; implement circuit breakers and timeouts.

3. **Over-Engineering for Scale Too Early**: Adding database sharding, message queues, and microservices when single server handles current load. Increases complexity without proportional benefit. Solution: Start simple (monolith + PostgreSQL), refactor as traffic grows.

4. **Single Point of Failure**: Database server is single point of failure. If it crashes, entire system offline. Solution: Always design with redundancy (read replicas, failover, backup).

5. **No Plan for Data Consistency**: Distributed system reads stale data without understanding implications. Some features require strong consistency, others work with eventual consistency. Solution: Explicitly choose consistency model per feature.

6. **Monitoring Only After Production Issues**: Discovering system limits when users complain about slowness or errors. Solution: Design monitoring first; create dashboards and alerts before deployment.

## Anti-Patterns

1. **Database-Centric Design**: Putting all logic in stored procedures and triggers. Database becomes bottleneck; hard to version control; impossible to debug. Use application layer for business logic.

2. **Synchronous All the Way**: Every interaction is HTTP request; one slow service cascades timeouts. Entire system appears unresponsive. Use asynchronous messaging for non-critical operations.

3. **Ignoring the "I" in "ACID"**: Building system assuming perfect isolation, then discovering race conditions when multiple users modify same data. Solution: Understand isolation levels (Read Uncommitted → Serializable); test concurrent scenarios.

4. **Over-Normalizing Database**: Breaking data into too many tables requiring 10-table joins. Query performance degrades to seconds. Solution: Some denormalization is acceptable (user_follower_count in users table) if consistency is maintained.

5. **No Backwards Compatibility**: Changing API response format breaks clients. Old mobile app versions fail. Solution: API versioning (v1, v2); deprecation window; support multiple versions.

6. **Treating Security as Afterthought**: Building system, then trying to add authentication/authorization. SQL injection vulnerabilities, credential leaks, unencrypted data in transit. Security must be first-class concern from design phase.
