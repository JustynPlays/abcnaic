import sqlite3
"""
This script has been deprecated and intentionally disabled.

The application no longer uses an 'is_verified' gating flow; users are active immediately
upon registration. To avoid accidental mass-modification of user rows, this file has
been disabled. If you need to run a one-off migration to update historical data,
create a dedicated migration script or use the project's migration tooling.

If you want the original script preserved, a copy exists in the archive folder.
"""

import sys

print("scripts/mark_verified.py has been disabled. See archive/removed-2025-10-26 for the original.")
sys.exit(0)
print(f'Updated users - was_unverified={before}, now_unverified={after}, marked={before - after}')
