param(
    [string]$HostAlias = "synology",
    [string]$RemoteDir = "/volume1/docker/shorts-pipeline"
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$remote = "${HostAlias}:$RemoteDir"
$trackedFiles = @(
    "Dockerfile", "docker-compose.yml", "requirements.txt", "pyproject.toml",
    ".env.example", "README.md"
)
$trackedDirectories = @("assets", "docs", "shorts_pipeline")

Write-Host "Preparing ${HostAlias}:$RemoteDir"
ssh -o BatchMode=yes $HostAlias "mkdir -p '$RemoteDir/secrets' '$RemoteDir/output' '$RemoteDir/data'"
if ($LASTEXITCODE -ne 0) { throw "Unable to prepare the NAS target" }

Push-Location $repo
try {
    scp -O -q @trackedFiles $remote
    if ($LASTEXITCODE -ne 0) { throw "Unable to copy deployment files" }
    scp -O -q -r @trackedDirectories $remote
    if ($LASTEXITCODE -ne 0) { throw "Unable to copy deployment directories" }
}
finally {
    Pop-Location
}

$remoteCommand = "cd '$RemoteDir' && cp -n .env.example .env && /usr/local/bin/docker compose build && /usr/local/bin/docker compose run --rm shorts-pipeline python -m shorts_pipeline backgrounds && /usr/local/bin/docker compose up -d && /usr/local/bin/docker compose ps"
ssh -o BatchMode=yes $HostAlias $remoteCommand
if ($LASTEXITCODE -ne 0) { throw "NAS deployment failed" }
Write-Host "Deployment complete; existing .env was preserved."
