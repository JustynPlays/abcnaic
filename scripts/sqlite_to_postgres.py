"""sqlite_to_postgres.py

Copy schema and data from a local SQLite database file into a Postgres database.

Usage:
  python scripts/sqlite_to_postgres.py --sqlite ./db/app.db --pg "$DATABASE_URL"

By default the script will try to read the target Postgres URL from the
environment variable DATABASE_URL. It uses SQLAlchemy to reflect the SQLite
schema, create corresponding tables in Postgres, and bulk-copy rows.

Important:
- Run this against a non-production database first to verify results.
- The script attempts to set SERIAL sequences for integer `id` primary keys
  when present.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError, NoSuchModuleError


def copy_sqlite_to_postgres(sqlite_path: str, postgres_url: str, batch: int = 500, dry_run: bool = False,
                            only_tables: Optional[set] = None, skip_tables: Optional[set] = None) -> int:
    """Copy data from sqlite_path into postgres_url.

    Returns number of rows copied (approx) or -1 on error.
    """
    # dry_run parameter controls whether writes are performed
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite file not found: {sqlite_path}")
        return -1

    print(f"Connecting to SQLite: {sqlite_path}")
    sqlite_engine = create_engine(f"sqlite:///{os.path.abspath(sqlite_path)}")

    # Normalize common Heroku-style URL 'postgres://' -> SQLAlchemy 'postgresql://'
    normalized_pg = postgres_url
    if normalized_pg.startswith("postgres://"):
        normalized_pg = "postgresql://" + normalized_pg[len("postgres://"):]

    print(f"Connecting to Postgres: {normalized_pg}")
    try:
        pg_engine = create_engine(normalized_pg)
    except NoSuchModuleError as e:
        print("Error: SQLAlchemy couldn't load the DB dialect for the URL you provided.")
        print("If your URL begins with 'postgres://', try using 'postgresql://' or 'postgresql+psycopg2://'.")
        print("Also ensure the 'psycopg2-binary' package is installed.")
        print("Original error:", e)
        return -1

    meta_sqlite = MetaData()
    print("Reflecting SQLite schema...")
    meta_sqlite.reflect(bind=sqlite_engine)

    if not meta_sqlite.tables:
        print("No tables found in SQLite database. Nothing to do.")
        return 0

    meta_pg = MetaData()

    # Copy table objects into postgresql metadata
    print("Preparing tables for creation in Postgres...")
    for tbl in meta_sqlite.sorted_tables:
        # Table.to_metadata requires SQLAlchemy >=1.4
        tbl.to_metadata(meta_pg)

    print("Creating tables on Postgres (if not exists)...")

    # Dry-run: only report tables and row counts without creating or writing
    if dry_run:
        print("Dry-run mode: listing tables and row counts (no writes)")
        with sqlite_engine.connect() as s_conn:
            for tbl in meta_sqlite.sorted_tables:
                if only_tables and tbl.name not in only_tables:
                    continue
                if skip_tables and tbl.name in skip_tables:
                    continue
                try:
                    res = s_conn.execute(text(f"SELECT count(1) FROM \"{tbl.name}\""))
                    n = res.scalar()
                except Exception:
                    n = None
                print(f"Table: {tbl.name}  Rows: {n}")
        return 0

    meta_pg.create_all(bind=pg_engine)

    total_rows = 0
    try:
        with sqlite_engine.connect() as s_conn, pg_engine.connect() as p_conn:
            for tbl in meta_sqlite.sorted_tables:
                if only_tables and tbl.name not in only_tables:
                    print(f"Skipping table {tbl.name} (not in --only-tables)")
                    continue
                if skip_tables and tbl.name in skip_tables:
                    print(f"Skipping table {tbl.name} (in --skip-tables)")
                    continue
                print(f"Copying table: {tbl.name}")
                rows = s_conn.execute(select(tbl)).fetchall()
                if not rows:
                    print("  (no rows)")
                    continue

                # Convert SQLAlchemy Row/RowMapping to plain dict safely.
                rows_dicts = []
                for r in rows:
                    if hasattr(r, "_mapping"):
                        rows_dicts.append(dict(r._mapping))
                    else:
                        try:
                            rows_dicts.append(dict(r))
                        except Exception:
                            # Fallback: map by column order
                            rows_dicts.append({col.name: r[idx] for idx, col in enumerate(tbl.columns)})
                p_table = meta_pg.tables.get(tbl.name)
                if p_table is None:
                    print(f"  Warning: target table {tbl.name} not found in Postgres metadata; skipping")
                    continue

                # Avoid duplicate primary-key inserts by skipping rows whose PK already exists in target
                existing_ids = set()
                if 'id' in p_table.c:
                    try:
                        existing = p_conn.execute(select(p_table.c.id)).fetchall()
                        existing_ids = {r[0] for r in existing}
                    except Exception:
                        existing_ids = set()

                if existing_ids:
                    filtered = [r for r in rows_dicts if r.get('id') not in existing_ids]
                    if not filtered:
                        print(f"  (all {len(rows_dicts)} rows already exist in target; skipping)")
                        continue
                    rows_dicts = filtered

                # Insert in batches (use implicit transactions via execute to avoid nested begin())
                for i in range(0, len(rows_dicts), batch):
                    chunk = rows_dicts[i : i + batch]
                    p_conn.execute(p_table.insert(), chunk)
                total_rows += len(rows_dicts)

                # If table has an integer PK called `id`, attempt to set its sequence
                id_cols = [c for c in tbl.columns if c.primary_key and c.name == 'id']
                if id_cols:
                    max_id = max((r.get('id') or 0) for r in rows_dicts)
                    try:
                        # setval(..., is_called=true) so next serial uses max_id+1
                        p_conn.execute(
                            text("SELECT setval(pg_get_serial_sequence(:tbl, 'id'), :val, true)"),
                            {"tbl": tbl.name, "val": max_id},
                        )
                    except SQLAlchemyError:
                        # Not fatal; sequence may not exist or column not serial
                        pass

    except SQLAlchemyError as e:
        print("Database error while copying:", e)
        return -1

    print(f"Done. Approx rows copied: {total_rows}")
    return total_rows


def _parse_args(argv: Optional[list[str]] = None):
    p = argparse.ArgumentParser(description="Copy SQLite DB into Postgres (simple tool)")
    p.add_argument("--sqlite", default="db/app.db", help="Path to the SQLite file (default: db/app.db)")
    p.add_argument("--pg", help="Postgres DATABASE_URL. If omitted, read from env DATABASE_URL")
    p.add_argument("--batch", type=int, default=500, help="Batch size for inserts")
    p.add_argument("--dry-run", action="store_true", help="Print table names and row counts without inserting")
    p.add_argument("--only-tables", help="Comma-separated list of tables to copy (default: all)")
    p.add_argument("--skip-tables", help="Comma-separated list of tables to skip")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    pg = args.pg or os.environ.get("DATABASE_URL")
    if not pg:
        print("Error: Postgres URL not provided via --pg and DATABASE_URL not set in env.")
        return 2

    only = set(args.only_tables.split(',')) if args.only_tables else None
    skip = set(args.skip_tables.split(',')) if args.skip_tables else None

    rc = copy_sqlite_to_postgres(args.sqlite, pg, batch=args.batch, dry_run=args.dry_run,
                                only_tables=only, skip_tables=skip)
    return 0 if rc >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
