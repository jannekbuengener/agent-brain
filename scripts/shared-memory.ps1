# Agent Brain SurrealDB local operator entry point. Never manages Claire.
[CmdletBinding()]
param(
    [ValidateSet('start','stop','status')]
    [string]$Action = 'status'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$compose = Join-Path $repo 'infrastructure\compose\shared-memory.yml'
$dir = $env:AGENT_BRAIN_SECRETS_PATH
if (-not $dir) { $dir = Join-Path $env:USERPROFILE 'Documents\.secrets\.agent-brain' }
$env:AGENT_BRAIN_SECRETS_PATH = $dir

if ($Action -eq 'status') {
    docker compose -p agent_brain -f $compose ps
    if ($LASTEXITCODE -ne 0) { throw 'Agent Brain status failed' }
    return
}
if ($Action -eq 'stop') {
    docker compose -p agent_brain -f $compose stop surrealdb
    if ($LASTEXITCODE -ne 0) { throw 'Agent Brain stop failed' }
    return
}
if (-not (Test-Path (Join-Path $dir 'SURREALDB_ENV'))) {
    throw 'Missing private AGENT_BRAIN_SECRETS_PATH/SURREALDB_ENV'
}
$existing = @(docker volume ls --format '{{.Name}}' | Where-Object { $_ -eq 'agent_brain_memory_data' })
if ($existing.Count -eq 0) {
    docker volume create agent_brain_memory_data | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not create agent brain volume' }
    docker run --rm -u 0 -v agent_brain_memory_data:/data alpine:latest chown -R 65532:65532 /data
    if ($LASTEXITCODE -ne 0) { throw 'Could not initialize volume permissions' }
}
docker compose -p agent_brain -f $compose up -d
if ($LASTEXITCODE -ne 0) { throw 'Could not start agent brain surrealdb' }
docker compose -p agent_brain -f $compose ps
