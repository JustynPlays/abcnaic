import sqlite3
import os

db_path = 'c:/xampp2/htdocs/ABC-PWA Ichatbot/db/drcare.db'

if not os.path.exists(db_path):
    print(f"❌ Database file not found: {db_path}")
else:
    print(f"✅ Database file exists: {db_path}")
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get all tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = c.fetchall()
    
    print(f"\nTotal tables: {len(tables)}")
    print("\nTables in database:")
    for table in tables:
        table_name = table[0]
        c.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = c.fetchone()[0]
        print(f"  • {table_name} ({count} rows)")
    
    conn.close()
