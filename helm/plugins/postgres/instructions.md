# PostgreSQL Plugin — RAPR AI

You have access to a PostgreSQL database via the `POSTGRES_CONNECTION_STRING` environment variable.

## Authentication
```python
import os
import psycopg2

CONN_STRING = os.environ["POSTGRES_CONNECTION_STRING"]
# Format: postgresql://user:password@host:5432/dbname

conn = psycopg2.connect(CONN_STRING)
cur = conn.cursor()
```

> If psycopg2 is not installed:
> `pip install --break-system-packages psycopg2-binary`

## Common Operations

### List tables
```python
cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public' ORDER BY table_name
""")
tables = cur.fetchall()
for t in tables:
    print(t[0])
```

### Describe a table
```python
cur.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'users' ORDER BY ordinal_position
""")
for col in cur.fetchall():
    print(f"  {col[0]:20s} {col[1]:15s} null={col[2]} default={col[3]}")
```

### Query data
```python
cur.execute("SELECT id, name, email FROM users WHERE active = %s LIMIT 20", (True,))
rows = cur.fetchall()
columns = [desc[0] for desc in cur.description]
for row in rows:
    print(dict(zip(columns, row)))
```

### Insert data
```python
cur.execute(
    "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
    ("Alice", "alice@example.com")
)
new_id = cur.fetchone()[0]
conn.commit()
```

### Update data
```python
cur.execute("UPDATE users SET active = %s WHERE id = %s", (False, 42))
conn.commit()
print(f"Rows updated: {cur.rowcount}")
```

### Run aggregate queries
```python
cur.execute("""
    SELECT department, COUNT(*) as cnt, AVG(salary)::numeric(10,2) as avg_sal
    FROM employees
    GROUP BY department
    ORDER BY cnt DESC
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]} employees, avg salary ${row[2]}")
```

### Export to CSV
```python
import csv

cur.execute("SELECT * FROM orders WHERE created_at > '2025-01-01'")
columns = [desc[0] for desc in cur.description]
with open("orders_export.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(columns)
    writer.writerows(cur.fetchall())
```

### Create a table
```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL,
        level VARCHAR(10) DEFAULT 'info',
        created_at TIMESTAMP DEFAULT NOW()
    )
""")
conn.commit()
```

## Tips
- Always use parameterized queries (`%s`) — never f-strings — to prevent SQL injection.
- Call `conn.commit()` after INSERT/UPDATE/DELETE. Reads don't need commit.
- Use `conn.rollback()` if an error occurs mid-transaction.
- Close connections: `cur.close(); conn.close()` when done.
- For large result sets, use `cur.fetchmany(100)` in a loop instead of `fetchall()`.
- Connection string format: `postgresql://user:pass@host:5432/dbname?sslmode=require`
