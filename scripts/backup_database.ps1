param(
    [string]$BackupDir = "./backups"
)

$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) { throw "DATABASE_URL is required" }
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $BackupDir "skuphase-$stamp.dump"

# pg_dump receives the connection string through the process argument. Use a
# protected CI secret/environment in production and keep this directory out of
# the web/static tree.
pg_dump --format=custom --file=$target $env:DATABASE_URL
Write-Output "Backup written to $target"
