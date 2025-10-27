"""
Simple migration utility to copy data from SQLite to Postgres.

Usage:
  - Install requirements: pip install psycopg2-binary
  - Set target DATABASE_URL in environment, or pass as first arg.
  - Run: python scripts/migrate_sqlite_to_postgres.py /path/to/sqlite.db

The script will:
  - Read all non-system SQLite tables
  - Create equivalent tables in Postgres with simple type mapping
  - Copy rows from SQLite to Postgres
  - For integer primary keys, create a sequence and set it to max(id) so future inserts don't conflict

This is a one-shot tool; test the result on a staging DB before downtimes.
"""
import sqlite3
import os
import sys
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
except Exception as e:
    print('psycopg2 is required. Install with: pip install psycopg2-binary')
    raise


def map_type(sqlite_type):
    if not sqlite_type:
        return 'TEXT'
    t = sqlite_type.upper()
    if 'INT' in t:
        return 'BIGINT'
    if 'CHAR' in t or 'CLOB' in t or 'TEXT' in t:
        return 'TEXT'
    if 'BLOB' in t:
        return 'BYTEA'
    if 'REAL' in t or 'FLOA' in t or 'DOUB' in t:
        return 'DOUBLE PRECISION'
    if 'NUMERIC' in t or 'DEC' in t:
        return 'NUMERIC'
    return 'TEXT'


def get_sqlite_tables(sq_conn):
    c = sq_conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return [r[0] for r in c.fetchall()]


def get_table_info(sq_conn, table):
    c = sq_conn.cursor()
    c.execute(f"PRAGMA table_info('{table}')")
    # cid, name, type, notnull, dflt_value, pk
    return c.fetchall()


def create_table_pg(pg_cur, table, columns):
    parts = []
    pk_cols = []
    for col in columns:
        name = col[1]
        ctype = map_type(col[2])
        notnull = 'NOT NULL' if col[3] else ''
        part = f'"{name}" {ctype} {notnull}'
        parts.append(part)
        if col[5]:
            pk_cols.append(name)

    pk = ''
    if pk_cols:
        pk = f', PRIMARY KEY ({",".join(["\"%s\""%c for c in pk_cols])})'

    sql = f'CREATE TABLE IF NOT EXISTS "{table}" ({", ".join(parts)}{pk});'
    pg_cur.execute(sql)


def copy_table(sq_conn, pg_conn, table):
    columns = get_table_info(sq_conn, table)
    col_names = [col[1] for col in columns]

    pg_cur = pg_conn.cursor()
    create_table_pg(pg_cur, table, columns)

    # Copy rows
    sq_cur = sq_conn.cursor()
    sq_cur.execute(f'SELECT {",".join(["\"%s\""%n for n in col_names])} FROM "{table}"')
    rows = sq_cur.fetchall()
    if not rows:
        pg_conn.commit()
        return

    placeholders = ','.join(['%s'] * len(col_names))
    insert_sql = f'INSERT INTO "{table}" ({",".join(["\"%s\""%n for n in col_names])}) VALUES ({placeholders})'

    for r in rows:
        # sqlite3 returns tuples; convert to list for psycopg2
        pg_cur.execute(insert_sql, list(r))

    # If table has integer PK, set sequence
    pk_cols = [c for c in columns if c[5]]
    if len(pk_cols) == 1 and 'INT' in (pk_cols[0][2] or '').upper():
        pk = pk_cols[0][1]
        pg_conn.commit()
        pg_cur.execute(f"SELECT MAX(\"{pk}\") as maxid FROM \"{table}\"")
        maxid = pg_cur.fetchone()[0] or 0
        seq_name = f'{table}_{pk}_seq'
        # create sequence if not exists and set it
        pg_cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START WITH {max(1, maxid+1)}")
        pg_cur.execute(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{pk}\" SET DEFAULT nextval('{seq_name}')")

    pg_conn.commit()


def migrate(sqlite_path, pg_dsn):
    print('Opening sqlite:', sqlite_path)
    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row

    print('Connecting to Postgres...')
    pg = psycopg2.connect(pg_dsn)

    tables = get_sqlite_tables(sq)
    print('Found tables:', tables)

    for t in tables:
        print('Copying table', t)
        copy_table(sq, pg, t)

    sq.close()
    pg.close()
    print('Migration complete')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python migrate_sqlite_to_postgres.py /path/to/sqlite.db [POSTGRES_DSN]')
        print('You can alternatively set DATABASE_URL environment variable for target Postgres.')
        sys.exit(1)

    sqlite_db = sys.argv[1]
    pg_dsn = os.environ.get('DATABASE_URL') if len(sys.argv) < 3 else sys.argv[2]
    if not pg_dsn:
        print('No Postgres DSN provided (via arg or DATABASE_URL). Aborting.')
        sys.exit(1)

    migrate(sqlite_db, pg_dsn)
