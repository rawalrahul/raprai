---
name: api-designer
description: "Design RESTful and GraphQL APIs with correct endpoint naming conventions, versioning strategy, pagination, error response standards, rate limiting, and generate OpenAPI/GraphQL schemas with documentation."
category: coding
difficulty: advanced
model_boost: "Weak models design inconsistent endpoints, miss error handling, don't version APIs, and generate incomplete specifications"
---

# API Designer

## Purpose
Well-designed APIs are self-documenting, predictable, and sustainable. They handle growth, backward compatibility, and error cases deliberately. This skill produces API designs with concrete endpoints, error contracts, pagination strategy, and machine-readable specifications that development can implement immediately.

## When to Use
- Starting a new service or public API
- Designing integration points between systems
- Planning mobile app backends
- Versioning existing APIs for breaking changes
- Documenting REST/GraphQL contract before implementation
- **Do NOT use when**: Designing internal micro-service callsites (use simpler contracts), or when the API scope isn't yet defined

## Instructions

### Step 1: Define Resource Model and Use Cases
List all nouns the API works with (users, products, orders) and their relationships. For each resource, identify primary use cases:
- CRUD operations (Create, Read, Update, Delete)
- Filtering/searching needs
- Relationships (user has many orders)
- Computed fields or aggregations

Example: E-commerce API needs users, products, orders, reviews, payments. A common use case is "list all products in a category with reviews."

### Step 2: Design RESTful Endpoints
Follow REST conventions strictly:
- Use HTTP verbs correctly: GET (read), POST (create), PUT/PATCH (update), DELETE (remove)
- Use nouns for resources, not verbs: `/products` not `/getProducts`
- Use resource hierarchy only 2 levels deep: `/products/{id}/reviews` is OK; `/products/{id}/reviews/{id}/comments/{id}` violates nesting depth
- Use query parameters for filtering: `/products?category=electronics&minPrice=100`
- Use path parameters for identity: `/products/{productId}/reviews/{reviewId}`

Example endpoints:
```
GET    /api/v1/products              # List all products
POST   /api/v1/products              # Create product
GET    /api/v1/products/{id}         # Get product by ID
PUT    /api/v1/products/{id}         # Update product
DELETE /api/v1/products/{id}         # Delete product
GET    /api/v1/products/{id}/reviews # List reviews for product
```

### Step 3: Design Error Response Contract
Define a consistent error format that every endpoint uses:
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "User-friendly error message",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    },
    "traceId": "req-12345"
  }
}
```

Map HTTP status codes to scenarios:
- 400 Bad Request: Client error (invalid input)
- 401 Unauthorized: Missing/invalid authentication
- 403 Forbidden: Authenticated but lacks permission
- 404 Not Found: Resource doesn't exist
- 409 Conflict: Request conflicts with current state (duplicate creation)
- 422 Unprocessable Entity: Validation failed
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server failure (rare, log it)

### Step 4: Design Pagination and Filtering
For list endpoints, define pagination:
```json
{
  "data": [{...}, {...}],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalCount": 1500,
    "hasMore": true
  }
}
```

Or cursor-based pagination for large datasets:
```json
{
  "data": [{...}, {...}],
  "pagination": {
    "nextCursor": "eyJpZCI6IDEwMDB9",
    "hasMore": true
  }
}
```

Define filter syntax:
```
GET /products?category=electronics&minPrice=50&maxPrice=500&sortBy=price&sortDirection=asc&pageSize=25
```

### Step 5: Design Versioning Strategy
Choose one approach:
- **URL versioning** (simple, explicit): `/api/v1/products`, `/api/v2/products`
- **Header versioning** (clean URLs): `Accept: application/vnd.company.v1+json`
- **Query param** (rarely used): `/api/products?version=1`

Recommendation: URL versioning for public APIs (clearest for API consumers), header versioning for internal.

Plan deprecation: support N-1 versions, announce deprecation 6 months before removal.

### Step 6: Design Rate Limiting and Quotas
Include rate limit headers in every response:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640001234
```

Strategy: Per-user (authenticated) or per-IP (anonymous). Example:
- Unauthenticated: 100 requests/hour
- Authenticated: 10,000 requests/hour
- Premium tier: 100,000 requests/hour

Return 429 with `Retry-After` header when limit exceeded.

### Step 7: Generate OpenAPI/GraphQL Schema
Create machine-readable specification. For REST, use OpenAPI 3.0:
```yaml
openapi: 3.0.0
info:
  title: Product API
  version: v1
paths:
  /products:
    get:
      parameters:
        - name: category
          in: query
          schema:
            type: string
      responses:
        '200':
          description: Product list
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProductList'
components:
  schemas:
    Product:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        price:
          type: number
      required: [id, name, price]
```

For GraphQL, define schema with clear types and relationships:
```graphql
type Product {
  id: ID!
  name: String!
  price: Float!
  reviews: [Review!]!
}

type Query {
  products(category: String, limit: Int = 20): [Product!]!
  product(id: ID!): Product
}
```

## Output Template

```
# API Design: [System Name]

## Overview
[2-3 sentences on API purpose and primary users]

## Resource Model
[List resources and relationships]

## Endpoints

### Products
\`\`\`
GET    /api/v1/products
POST   /api/v1/products
GET    /api/v1/products/{id}
PUT    /api/v1/products/{id}
DELETE /api/v1/products/{id}
\`\`\`

[Repeat for other resources]

## Error Responses
\`\`\`json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": {...}
  }
}
\`\`\`

## Pagination and Filtering
[Define strategy with examples]

## Rate Limiting
[Tiers and headers]

## OpenAPI Specification
[Full schema]

## Breaking Changes & Versioning
[Version strategy and deprecation plan]
```

## Quality Gates
- [ ] Every POST/PUT endpoint includes validation rules in spec
- [ ] Error codes are specific and documented (not generic "error")
- [ ] Pagination strategy handles 1M+ records efficiently
- [ ] Rate limiting strategy defined with concrete numbers
- [ ] Versioning plan handles backward compatibility
- [ ] OpenAPI/GraphQL schema is valid and complete

## Examples

### Good Output (excerpt)
```
### Products
GET /api/v1/products
Query parameters:
  - category (string, optional): Filter by category name
  - minPrice (number, optional): Minimum price in cents
  - maxPrice (number, optional): Maximum price in cents
  - pageSize (integer, optional, default: 20, max: 100)
  - pageNumber (integer, optional, default: 1)
  - sortBy (string, optional, enum: [name, price, rating])

Response 200:
{
  "data": [
    { "id": 1, "name": "Laptop", "price": 99999, "category": "electronics" }
  ],
  "pagination": {
    "pageNumber": 1,
    "pageSize": 20,
    "totalCount": 5000,
    "hasMore": true
  }
}

Response 400:
{ "error": { "code": "INVALID_PAGE_SIZE", "message": "pageSize must be <= 100" } }
```

### Bad Output (what to avoid)
```
GET /products - Get products
POST /products - Add product
```
This lacks details on filtering, pagination, error handling, and versioning.

## Common Mistakes

1. **Mistake**: Designing endpoints without versioning, then breaking clients later
   → **Fix**: Plan versioning from endpoint 1. Use `/api/v1/` prefix even for first version.

2. **Mistake**: Inconsistent error responses (sometimes error object, sometimes string)
   → **Fix**: Define error schema once, use it everywhere. Every 4xx/5xx returns same structure.

3. **Mistake**: N+1 problem in API design (client must call endpoint multiple times to get related data)
   → **Fix**: Use query parameters to include related resources (e.g., `?include=reviews,ratings`) or embed in response.

4. **Mistake**: Forgetting pagination, returning all 100k records
   → **Fix**: Every list endpoint must have pageSize parameter with reasonable default (20) and max (100).

5. **Mistake**: Rate limiting without communicating limits to clients
   → **Fix**: Always return `X-RateLimit-*` headers and document tiers clearly.

## Anti-Patterns

- Never use verbs in endpoint paths (`/getUser`, `/createProduct`); REST uses HTTP verbs, paths are nouns
- Never design filtering with complex boolean logic in query string; keep filters simple and orthogonal (AND together, not OR)
- Never forget to specify `Content-Type` and `Accept` headers in examples; make it clear what format is expected
- Never design deeply nested endpoints (more than 2 levels) without GraphQL; `/users/{id}/posts/{id}/comments/{id}` is unmaintainable
- Never design endpoints that require multiple calls to compose a common use case (e.g., must call 5 endpoints to display a user profile); design for actual workflows

