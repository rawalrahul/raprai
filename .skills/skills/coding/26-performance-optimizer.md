---
name: performance-optimizer
description: "Identify performance bottlenecks through profiling, then optimize code using algorithmic improvements, caching strategies, lazy loading, database optimization, and memory profiling."
category: coding
difficulty: advanced
model_boost: "Weak models identify wrong bottlenecks or suggest ineffective optimizations"
---

# Performance Optimizer

## Purpose
This skill systematizes performance optimization by following a data-driven approach: profile → identify → measure → optimize → verify. It covers CPU profiling to find hot paths, memory profiling for leak detection, database query analysis and optimization, caching strategies at multiple layers, algorithmic complexity improvements, and lazy loading patterns. Output includes specific optimizations with before/after benchmarks, elimination of premature optimization attempts, and measurable performance improvements documented with profiling data.

## When to Use
- Investigating slow API endpoints or user-reported lag
- Optimizing database queries and indexes
- Reducing application memory consumption
- Speeding up application startup time
- Improving web page load time (Core Web Vitals)
- Scaling system to handle more concurrent users
- **Do NOT use when**: Premature optimization before profiling, or optimizing already-fast code

## Instructions

### Step 1: Profile and Identify Bottlenecks
Use profiling tools to find actual performance issues:

**Node.js CPU Profiling:**
```bash
# Using node built-in profiler
node --prof app.js
# Generates isolate-*.log file

# Process the profile
node --prof-process isolate-*.log > profile.txt

# Or use Node.js Inspector
node --inspect app.js
# Then connect Chrome DevTools: chrome://inspect

# Use clinic.js for easier analysis
npm install -g clinic
clinic doctor -- node app.js
# Generates HTML report showing CPU, memory, event loop issues
```

**Python CPU Profiling:**
```python
import cProfile
import pstats

# Method 1: Decorator
@profile
def slow_function():
    # code here
    pass

# Method 2: Direct profiling
profiler = cProfile.Profile()
profiler.enable()

# Run code to profile
slow_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions

# Using py-spy for production profiling (low overhead)
# pip install py-spy
# py-spy record -o profile.svg -- python app.py
```

**Database Query Analysis:**
```sql
-- PostgreSQL: Enable query logging
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Find slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Analyze query plan
EXPLAIN ANALYZE
SELECT u.id, u.name, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id
ORDER BY post_count DESC;

-- Find missing indexes
SELECT
  schemaname, tablename,
  (total_heap_blks_read - heap_blks_hit) / (total_heap_blks_read + 0.1) as missing_index_ratio
FROM pg_statio_user_tables
ORDER BY missing_index_ratio DESC;
```

**Memory Profiling:**
```python
# Using memory_profiler
from memory_profiler import profile

@profile
def memory_intensive_function():
    large_list = list(range(1000000))  # tracks memory usage
    return sum(large_list)

# Run: python -m memory_profiler script.py

# For production: Use tracemalloc
import tracemalloc
tracemalloc.start()

# Run code
result = memory_intensive_function()

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 10**6:.2f}MB; Peak: {peak / 10**6:.2f}MB")

# Find top allocations
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:5]:
    print(stat)
```

### Step 2: Identify Root Causes and Measure Baseline
Understand why bottleneck exists and establish metrics:

**Common Bottlenecks and Causes:**
```
API Slow (>500ms response time)
├── Problem: N+1 Queries
│   └── Solution: Eager loading, JOINs
├── Problem: Missing database indexes
│   └── Solution: Add indexes on WHERE/JOIN columns
├── Problem: Large data transfer
│   └── Solution: Pagination, filtering, select specific columns
└── Problem: Slow business logic
    └── Solution: Algorithm optimization, caching

Application Memory Spike
├── Problem: Memory leak (objects not garbage collected)
│   └── Solution: Fix circular references, unsubscribe listeners
├── Problem: Unbounded cache
│   └── Solution: Set max size, LRU eviction
└── Problem: Large collections loaded in memory
    └── Solution: Pagination, streaming, generators

Frontend Slow Load
├── Problem: Large bundle size
│   └── Solution: Code splitting, tree shaking, compression
├── Problem: Render blocking JS
│   └── Solution: Async/defer script tags
└── Problem: Unoptimized images
    └── Solution: WebP, compression, lazy loading
```

**Baseline Measurements:**
```bash
# HTTP endpoint baseline
ab -n 1000 -c 10 http://localhost:3000/api/posts
# Results show: requests/sec, latency distribution

# Database query baseline
psql -c "SELECT NOW(); SELECT * FROM posts WHERE user_id = 1; SELECT NOW();"

# Memory baseline
node --max-old-space-size=512 app.js &
# Monitor: node-inspect or Activity Monitor
```

### Step 3: Optimize Algorithms and Data Structures
Improve algorithmic complexity:

**Example 1: N+1 Query Problem**
```javascript
// BEFORE: O(n) queries
async function getPostsWithAuthors(postIds) {
  const posts = await db.query(
    'SELECT * FROM posts WHERE id IN ($1)',
    [postIds]
  );

  for (const post of posts) {
    // This runs N more queries!
    post.author = await db.query(
      'SELECT * FROM users WHERE id = $1',
      [post.user_id]
    );
  }
  return posts;
}

// AFTER: Single JOIN query
async function getPostsWithAuthors(postIds) {
  return db.query(`
    SELECT p.*, u.id as author_id, u.name as author_name
    FROM posts p
    JOIN users u ON p.user_id = u.id
    WHERE p.id IN ($1)
  `, [postIds]);
}

// Benchmark:
// Before: 1005ms for 100 posts (1 query + 100 queries)
// After: 45ms for 100 posts (1 JOIN query)
// Improvement: 22x faster
```

**Example 2: Inefficient Sorting**
```python
# BEFORE: Load all, sort in memory
def get_top_posts():
    posts = Post.objects.all()  # loads all rows into memory
    posts.sort(key=lambda p: p.views, reverse=True)  # O(n log n) in-memory sort
    return posts[:10]

# AFTER: Let database handle sorting
def get_top_posts():
    return Post.objects.all().order_by('-views')[:10]  # Database optimized

# Benchmark:
# Before: 5 seconds + 500MB memory for 1M posts
# After: 150ms + 1MB memory
# Improvement: 33x faster, 500x less memory
```

**Example 3: Hash Lookup vs. Linear Search**
```javascript
// BEFORE: Linear search O(n)
function isUserInGroup(userId, groupMembers) {
  // groupMembers is array of 10k items
  return groupMembers.some(m => m.id === userId);  // worst case: 10k comparisons
}

// AFTER: Hash map lookup O(1)
function isUserInGroup(userId, groupMemberSet) {
  // groupMemberSet is Set built once
  return groupMemberSet.has(userId);  // always 1 comparison
}

// Usage
const memberIds = new Set(groupMembers.map(m => m.id));
const isMember = isUserInGroup(123, memberIds);

// Benchmark: with 10k members
// Before: ~5ms average
// After: <0.1ms average
// Improvement: 50x faster
```

### Step 4: Implement Caching Strategies
Add caching at appropriate layers:

**L1: Application Memory Cache**
```javascript
// Simple cache with TTL
class Cache {
  constructor(ttl = 60000) {
    this.ttl = ttl;
    this.store = new Map();
  }

  get(key) {
    const item = this.store.get(key);
    if (!item) return null;

    if (item.expiresAt < Date.now()) {
      this.store.delete(key);
      return null;
    }

    return item.value;
  }

  set(key, value) {
    this.store.set(key, {
      value,
      expiresAt: Date.now() + this.ttl
    });
  }
}

// Or use existing library
const cache = new Map();

// Cache user by ID with 5-minute TTL
async function getUserWithCache(userId) {
  const cached = cache.get(userId);
  if (cached) return cached;

  const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);
  cache.set(userId, user);

  setTimeout(() => cache.delete(userId), 5 * 60 * 1000);
  return user;
}
```

**L2: Redis Distributed Cache**
```javascript
// Cache frequently accessed data
async function getUserWithRedis(userId) {
  const cached = await redis.get(`user:${userId}`);
  if (cached) return JSON.parse(cached);

  const user = await db.query('SELECT * FROM users WHERE id = $1', [userId]);

  // Cache for 5 minutes
  await redis.setex(`user:${userId}`, 300, JSON.stringify(user));
  return user;
}

// Batch cache pattern (avoid thundering herd)
async function getUsers(userIds) {
  const cacheKeys = userIds.map(id => `user:${id}`);
  const cached = await redis.mget(cacheKeys);

  const missing = userIds.filter((id, i) => !cached[i]);

  if (missing.length > 0) {
    const fromDb = await db.query(
      'SELECT * FROM users WHERE id = ANY($1)',
      [missing]
    );

    // Write back to cache
    const pipeline = redis.pipeline();
    fromDb.forEach(user => {
      pipeline.setex(`user:${user.id}`, 300, JSON.stringify(user));
    });
    await pipeline.exec();
  }

  return userIds.map((id, i) => cached[i] || ...);
}
```

**L3: Database Query Result Caching**
```sql
-- Materialized View for expensive aggregations
CREATE MATERIALIZED VIEW user_stats AS
SELECT
  u.id,
  u.name,
  COUNT(DISTINCT p.id) as post_count,
  COUNT(DISTINCT c.id) as comment_count,
  COUNT(DISTINCT f.follower_id) as follower_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id AND p.deleted_at IS NULL
LEFT JOIN comments c ON u.id = c.user_id AND c.deleted_at IS NULL
LEFT JOIN follows f ON u.id = f.following_id
GROUP BY u.id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY user_stats;

-- Index for faster queries
CREATE INDEX ON user_stats(id);
```

### Step 5: Optimize Database Queries
Improve query performance:

**Add Indexes Strategically**
```sql
-- Index on frequently filtered columns
CREATE INDEX posts_user_id_idx ON posts(user_id);
CREATE INDEX posts_created_at_idx ON posts(created_at DESC);

-- Composite index for common WHERE clause
CREATE INDEX posts_user_status_idx ON posts(user_id, status);

-- Index expressions for computed columns
CREATE INDEX posts_published_idx ON posts(published_at DESC)
WHERE published_at IS NOT NULL;

-- Partial index for large sparse columns
CREATE INDEX posts_featured_idx ON posts(id)
WHERE featured = true;

-- Monitor index usage
SELECT
  schemaname, tablename, indexname,
  idx_scan as number_of_scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

**Query Optimization Patterns**
```sql
-- BEFORE: Multiple queries
SELECT u.* FROM users u;
-- Then loop: SELECT COUNT(*) FROM posts WHERE user_id = ?

-- AFTER: Single query with aggregation
SELECT
  u.*,
  COALESCE(COUNT(p.id), 0) as post_count
FROM users u
LEFT JOIN posts p ON u.id = p.user_id
GROUP BY u.id;

-- BEFORE: Full table scan
SELECT * FROM posts WHERE title LIKE '%keyword%';

-- AFTER: Use full-text search
SELECT * FROM posts WHERE to_tsvector(title) @@ to_tsquery('keyword');

-- Or use external search engine
SELECT * FROM posts WHERE id = ANY(
  elasticsearch_query('keyword')
);
```

### Step 6: Implement Lazy Loading and Pagination
Reduce data transfer and memory:

```javascript
// BEFORE: Load everything at once
async function getPostsFeed(userId) {
  const posts = await db.query(`
    SELECT p.* FROM posts p
    WHERE p.user_id IN (
      SELECT following_id FROM follows WHERE follower_id = $1
    )
    ORDER BY p.created_at DESC
  `, [userId]);

  return posts;  // Could be 10,000+ rows!
}

// AFTER: Pagination with limit/offset
async function getPostsFeed(userId, page = 1, pageSize = 20) {
  const offset = (page - 1) * pageSize;

  const posts = await db.query(`
    SELECT p.*, COUNT(*) OVER() as total_count
    FROM posts p
    WHERE p.user_id IN (
      SELECT following_id FROM follows WHERE follower_id = $1
    )
    ORDER BY p.created_at DESC
    LIMIT $2 OFFSET $3
  `, [userId, pageSize, offset]);

  return {
    posts: posts,
    total: posts[0]?.total_count || 0,
    page,
    pageSize
  };
}

// AFTER: Cursor-based pagination (better for large datasets)
async function getPostsFeed(userId, cursor = null, limit = 20) {
  const posts = await db.query(`
    SELECT * FROM posts p
    WHERE p.user_id IN (
      SELECT following_id FROM follows WHERE follower_id = $1
    )
    AND (p.created_at, p.id) < (
      SELECT created_at, id FROM posts WHERE id = $2
    )
    ORDER BY p.created_at DESC, p.id DESC
    LIMIT $3
  `, [userId, cursor, limit]);

  const nextCursor = posts.length > 0 ? posts[posts.length - 1].id : null;
  return { posts, nextCursor };
}
```

### Step 7: Measure and Verify Improvements
Benchmark after optimization:

```bash
# Before and after comparison
# Run baseline
time node app.js < test_input.txt > /dev/null
# Real: 2.345s

# Apply optimization
# Run again
time node app.js < test_input.txt > /dev/null
# Real: 0.842s

# Calculate improvement
# 2.345 / 0.842 = 2.78x faster

# Load test with ab (ApacheBench)
ab -n 10000 -c 100 -p post_data.json http://localhost:3000/api/posts

# Before: 85 requests/second
# After: 240 requests/second
# Improvement: 2.8x throughput

# Memory comparison
node --max-old-space-size=512 app.js
# Monitor heap size before/after optimization
```

## Output Template

```markdown
# Performance Analysis: {{component_name}}

## 1. Profiling Results
- Bottleneck: {{bottleneck_identification}}
- Root Cause: {{root_cause}}

## 2. Baseline Metrics
- Current Latency: {{p50}}/{{p95}}/{{p99}}
- Throughput: {{requests_per_second}}
- Memory Usage: {{memory_mb}}

## 3. Optimization Strategy
- Algorithm: {{change}}
- Caching: {{cache_layer}}
- Database: {{query_optimization}}

## 4. Before/After Code
```Before: {{slow_code}}```
```After: {{optimized_code}}```

## 5. Benchmark Results
- Latency Improvement: {{improvement_percent}}
- Throughput Improvement: {{throughput_improvement}}
- Memory Reduction: {{memory_reduction}}

## 6. Verification
- Correctness: {{test_results}}
- Production Monitoring: {{alerting_configured}}
```

## Quality Gates
- [ ] Profiling data collected and analyzed (not guessed)
- [ ] Baseline metrics documented before optimization
- [ ] Root cause identified (not surface-level symptom)
- [ ] Optimization targets algorithmic complexity (not micro-optimizations)
- [ ] After-optimization metrics demonstrate measurable improvement
- [ ] Code changes don't reduce readability or maintainability significantly
- [ ] All automated tests pass after optimization
- [ ] Monitoring/alerting configured to catch regressions

## Examples

### Good Output (excerpt)
```markdown
# Performance Analysis: User Feed API

## Bottleneck
Profile showed 800ms response time; 95% spent in database queries.

## Root Cause
N+1 query problem: loading 50 posts, then loading author for each post (50 additional queries).

## Optimization
Changed from loop with individual author queries to single JOIN query.

## Results
- Before: 45 queries, 850ms response time, 15 users/second
- After: 1 query, 80ms response time, 150 users/second
- Improvement: 10.6x faster
```

### Bad Output (what to avoid)
```markdown
# Performance Analysis: User Feed API

The API is slow. Let's cache it and use Redis.
Add more servers to handle load.
Increase database connection pool.

# Problems:
- No profiling data
- No measurement
- Vague recommendations
- No before/after metrics
```

## Common Mistakes

1. **Optimizing Without Profiling**: Guessing the bottleneck and optimizing the wrong part. Spend 2 days making code 10% faster, but actual bottleneck is I/O wait. Solution: Always profile first with real data and realistic load.

2. **Optimizing for Micro-operations While Ignoring Macroscopic Issues**: Shaving 1ms off a function that's called once per request while ignoring 500ms database queries. Solution: Optimize algorithm and system architecture first, micro-optimizations last.

3. **Over-Caching and Cache Invalidation Problems**: Caching everything with indefinite TTL. Stale data served for days. Users confused by inconsistency. Solution: Understand data freshness requirements; use appropriate TTL.

4. **Adding Indexes Without Understanding Impact**: Index on every column. Write performance degrades (indexes must be updated). Storage bloats. Solution: Index only columns used in WHERE/JOIN/ORDER BY and measure impact.

5. **Single-Thread Load Testing Against Multi-threaded System**: Load test with 1 concurrent request. System appears fast. Deploy to production with 1000 concurrent users; falls apart (contention, lock conflicts). Solution: Test with realistic concurrency levels.

6. **Assuming Optimization Will Work at Scale**: Optimization works with 1k records. Breaks with 1M records due to algorithmic complexity. Solution: Test optimizations with production-scale data.

## Anti-Patterns

1. **Premature Optimization**: Optimizing code before it's written, before measuring, before it's slow. Adds complexity that makes code harder to maintain. Do simple code first; optimize what's actually slow.

2. **Trading Correctness for Speed**: Optimization introduces subtle bugs (race conditions, data loss). System faster but unreliable. Solution: Performance without correctness is worthless.

3. **Horizontal Scaling as First Solution**: Slow system, so add more servers. Underlying bottleneck (database) becomes worse. Solution: Optimize the slow component first, then scale horizontally if needed.

4. **Ignoring Tail Latency**: Optimizing average latency (p50) while p99 remains terrible. Users with slow requests experience poor performance. Solution: Measure p95, p99, p99.9; optimize worst cases.

5. **Optimization Without Monitoring**: Deploy optimization; no way to know if it actually helped in production. Can't detect regressions. Solution: Set up metrics and alerts before deployment.
