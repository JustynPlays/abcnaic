import sqlite3
import json

# Connect to SQLite database
conn = sqlite3.connect('db/users.db')
c = conn.cursor()

# Get all tables
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = c.fetchall()

print('=== SQLITE DATABASE ANALYSIS ===')
print(f'Found {len(tables)} tables:')
for table in tables:
    table_name = table[0]
    print(f'\n--- {table_name.upper()} ---')

    # Get table schema
    c.execute(f'PRAGMA table_info({table_name})')
    columns = c.fetchall()
    print('Columns:')
    for col in columns:
        pk_text = "PRIMARY KEY" if col[5] else ""
        null_text = "NOT NULL" if col[3] else ""
        print(f'  {col[1]} ({col[2]}) {pk_text} {null_text}'.strip())

    # Get row count
    c.execute(f'SELECT COUNT(*) FROM {table_name}')
    count = c.fetchone()[0]
    print(f'Row count: {count}')

    # Show sample data (first 3 rows) if table has data
    if count > 0:
        c.execute(f'SELECT * FROM {table_name} LIMIT 3')
        rows = c.fetchall()
        print('Sample data:')
        for i, row in enumerate(rows):
            print(f'  Row {i+1}: {row}')

conn.close()
