<#
PowerShell helper to run the SQLite -> Postgres migration script.

Usage examples (PowerShell):

# Use DATABASE_URL from env (e.g., on Heroku or after `heroku config:get`):
python .\scripts\sqlite_to_postgres.py --sqlite .\db\app.db

# Or pass the Postgres URL inline:
python .\scripts\sqlite_to_postgres.py --sqlite .\db\app.db --pg "postgres://user:pass@host:5432/dbname"

# Notes:
# - Make sure dependencies are installed (`pip install -r requirements.txt`).
# - Test on a copy of your production DB first.
# - If using Heroku, you can run `heroku config:get DATABASE_URL -a your-app-name` to get the URL.
#
Write-Host "Running sqlite -> postgres migration helper"

param(
    [string] $Sqlite = "db/app.db",
    [string] $Pg = $env:DATABASE_URL
)

if (-not $Pg) {
    Write-Host "DATABASE_URL not provided in env. You may pass --pg to the Python script or set DATABASE_URL env var." -ForegroundColor Yellow
}

$argList = @()
$argList += "--sqlite"; $argList += $Sqlite
if ($Pg) { $argList += "--pg"; $argList += $Pg }

python .\scripts\sqlite_to_postgres.py $argList
