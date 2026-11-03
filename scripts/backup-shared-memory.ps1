# Consistent, stopped-volume backup; only the dedicated Agent Brain container is touched.
[CmdletBinding()]
param(
    [string]$Vault = 'F:\Backups'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$container = 'agent_brain_surrealdb'
$volume = 'agent_brain_memory_data'
$secretDir = $env:AGENT_BRAIN_SECRETS_PATH
if (-not $secretDir) { $secretDir = Join-Path $env:USERPROFILE 'Documents\.secrets\.agent-brain' }
$secret = Join-Path $secretDir 'SURREALDB_ENV'
if (-not (Test-Path $secret)) { throw 'Missing protected Agent Brain secrets' }
if (-not (Test-Path $Vault)) { throw 'Backup vault missing; attach external F: first' }

$inspected = docker inspect $container --format '{{json .Config.Labels}}' 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Agent Brain container not found' }
$labels = $inspected | ConvertFrom-Json
if ($labels.'com.docker.compose.project' -ne 'agent_brain') {
    throw 'Refusing backup of a container not owned by agent_brain'
}
$mount = @(docker inspect $container --format '{{range .Mounts}}{{.Name}}{{println}}{{end}}' | Where-Object { $_ -eq $volume })
if ($mount.Count -ne 1) { throw 'Expected Agent Brain volume is not mounted' }

$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'
$staging = Join-Path $Vault ('_incoming\agent_brain_' + $stamp)
$dest = Join-Path $Vault ('Services\AgentBrain\2026\' + $stamp)
if ((Test-Path $staging) -or (Test-Path $dest)) { throw 'Backup destination collision' }
New-Item -ItemType Directory -Force -Path (Join-Path $staging 'data'),(Join-Path $staging 'config'),(Join-Path $staging 'secrets') | Out-Null
$stopped = $false
try {
    docker stop $container | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Container stop failed; snapshot aborted' }
    $stopped = $true

    $dataDir = Join-Path $staging 'data'
    docker run --rm --mount ('type=volume,source=' + $volume + ',target=/from,readonly') -v ($dataDir + ':/to') alpine:latest sh -c 'tar -czf /to/agent_brain_memory_data.tgz -C /from .'
    if ($LASTEXITCODE -ne 0) { throw 'Volume backup failed' }
    $archive = Join-Path $dataDir 'agent_brain_memory_data.tgz'
    if ((-not (Test-Path $archive)) -or (Get-Item $archive).Length -le 0) { throw 'Archive missing or empty' }
    tar -tzf $archive | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Archive is unreadable' }

    Copy-Item (Join-Path $repo 'infrastructure\compose\shared-memory.yml') (Join-Path $staging 'config\shared-memory.yml')
    Copy-Item (Join-Path $repo 'docs\operations\SHARED_MEMORY.md') (Join-Path $staging 'config\RESTORE_README.md')
    Copy-Item $secret (Join-Path $staging 'secrets\SURREALDB_ENV')
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $sec = Join-Path $staging 'secrets'
    & icacls.exe $sec /inheritance:r | Out-Null
    & icacls.exe $sec /grant:r ($identity + ':(OI)(CI)F') 'SYSTEM:(OI)(CI)F' | Out-Null
    $manifest = [ordered]@{
        schema_version = 1
        backup_id = 'BKP-AGENT-BRAIN-SURREAL-' + $stamp
        created_at = (Get-Date).ToUniversalTime().ToString('o')
        scope = 'agent_brain_surrealdb_only'
        compose_project = 'agent_brain'
        volume = $volume
        source_container = $container
        source_image = 'surrealdb/surrealdb@sha256:65000ff205b08363b035b457f292dc0a0b1cd4212935dd5ea94073cf67adf306'
        namespace = 'agent_brain'
        database = 'shared_memory'
        includes_secrets = $true
        full_restore_test = 'PENDING'
        restore_requirement = 'restore to empty independent volume; never attach CDB volume'
    }
    [IO.File]::WriteAllText((Join-Path $staging 'manifest.json'), ($manifest | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding($false)))
    $hashLines = @()
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        foreach($item in (Get-ChildItem $staging -File -Recurse | Sort-Object FullName)) {
            $stream = [IO.File]::OpenRead($item.FullName)
            try { $hash = $sha.ComputeHash($stream) } finally { $stream.Dispose() }
            $hex = ([BitConverter]::ToString($hash)).Replace('-','').ToLowerInvariant()
            $relative = $item.FullName.Substring($staging.Length + 1).Replace('\','/')
            $hashLines += ($hex + '  ' + $relative)
        }
    } finally { $sha.Dispose() }
    [IO.File]::WriteAllLines((Join-Path $staging 'SHA256SUMS.txt'), [string[]]$hashLines, (New-Object Text.UTF8Encoding($false)))
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    Move-Item -LiteralPath $staging -Destination $dest
    Write-Host ('BACKUP_FINAL=' + $dest)
    Write-Host ('SHA256_FILE_COUNT=' + $hashLines.Count)
} finally {
    if ($stopped) {
        docker start $container | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Error 'Agent Brain failed to restart after snapshot' }
    }
}
