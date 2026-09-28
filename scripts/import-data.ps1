<#
Restores a data backup produced by export-data.ps1 into the running `db` service.

Run this AFTER `docker compose up -d --build` has completed on the destination machine
(so the schema/migrations already exist) - this is a data-only restore, not a schema
restore.

Must be run from the repo root (where docker-compose.yml lives) with the stack up.
#>
param(
    [string]$BackupFile = (Join-Path (Split-Path $PSScriptRoot -Parent) "EngineOps-data-backup.sql")
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupFile)) {
    throw "Backup file not found: $BackupFile"
}

Write-Host "Restoring data from $BackupFile..."
Get-Content $BackupFile -Raw | docker compose exec -T db psql -U ops_platform -d ops_platform -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { throw "Restore failed (exit $LASTEXITCODE)" }

Write-Host "Data restored."
