[CmdletBinding()]
param(
  [string]$Tag = "openchronicle-core:local",
  [Parameter(Mandatory = $true)]
  [string]$PluginDir,
  [switch]$Keep,
  [switch]$SkipBuild,
  [switch]$SkipSelftest
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$RuntimeDir = Join-Path $env:TEMP "openchronicle-plugin-harness"

if (-not (Test-Path $PluginDir)) {
  Write-Error "PluginDir not found: $PluginDir"
  exit 1
}

function Cleanup {
  if (-not $Keep) {
    if (Test-Path $RuntimeDir) {
      Remove-Item -Recurse -Force $RuntimeDir
    }
  }
}

try {
  if (-not $SkipBuild) {
    Write-Host "Building image $Tag"
    docker build -t $Tag $RepoRoot
  }

  if (Test-Path $RuntimeDir) {
    Remove-Item -Recurse -Force $RuntimeDir
  }
  New-Item -ItemType Directory -Path $RuntimeDir | Out-Null

  if (-not $SkipSelftest) {
    Write-Host "Running container selftest"
    $selftestOutput = docker run --rm `
      -e OC_DB_PATH=/app/runtime/data/openchronicle.db `
      -e OC_CONFIG_DIR=/app/runtime/config `
      -e OC_PLUGIN_DIR=/app/runtime/plugins `
      -e OC_OUTPUT_DIR=/app/runtime/output `
      -v "${RuntimeDir}:/app/runtime" `
      -v "${PluginDir}:/app/runtime/plugins:ro" `
      $Tag selftest --json

    if ($LASTEXITCODE -ne 0) {
      Write-Error "Selftest failed with exit code $LASTEXITCODE"
      Write-Host $selftestOutput
      exit $LASTEXITCODE
    }

    $selftestJson = $selftestOutput | ConvertFrom-Json
    if (-not $selftestJson.ok) {
      Write-Error "Selftest returned ok=false"
      Write-Host $selftestOutput
      exit 1
    }
  }

  Write-Host "Running system.health RPC"
  $healthRequest = '{"protocol_version":"1","command":"system.health","args":{}}'
  $healthOutput = docker run --rm $Tag rpc --request $healthRequest

  if ($LASTEXITCODE -ne 0) {
    Write-Error "Health RPC failed with exit code $LASTEXITCODE"
    Write-Host $healthOutput
    exit $LASTEXITCODE
  }

  $healthJson = $healthOutput | ConvertFrom-Json
  if (-not $healthJson.ok) {
    Write-Error "Health RPC returned ok=false"
    Write-Host $healthOutput
    exit 1
  }

  Write-Host "Creating conversation"
  $convoId = docker run --rm `
    -e OC_DB_PATH=/app/runtime/data/openchronicle.db `
    -e OC_CONFIG_DIR=/app/runtime/config `
    -e OC_PLUGIN_DIR=/app/runtime/plugins `
    -e OC_OUTPUT_DIR=/app/runtime/output `
    -v "${RuntimeDir}:/app/runtime" `
    -v "${PluginDir}:/app/runtime/plugins:ro" `
    $Tag convo new

  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($convoId)) {
    Write-Error "Failed to create conversation"
    exit 1
  }

  Write-Host "Submitting hello.echo task"
  $taskOutput = docker run --rm `
    -e OC_DB_PATH=/app/runtime/data/openchronicle.db `
    -e OC_CONFIG_DIR=/app/runtime/config `
    -e OC_PLUGIN_DIR=/app/runtime/plugins `
    -e OC_OUTPUT_DIR=/app/runtime/output `
    -v "${RuntimeDir}:/app/runtime" `
    -v "${PluginDir}:/app/runtime/plugins:ro" `
    $Tag run-task $(($convoId).Trim()) hello.echo '{"prompt":"hello"}'

  if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to submit hello.echo task"
    Write-Host $taskOutput
    exit 1
  }

  Write-Host "Running task.run_many"
  $runManyRequest = '{"protocol_version":"1","command":"task.run_many","args":{"limit":1}}'
  $runManyOutput = docker run --rm $Tag rpc --request $runManyRequest

  if ($LASTEXITCODE -ne 0) {
    Write-Error "task.run_many failed with exit code $LASTEXITCODE"
    Write-Host $runManyOutput
    exit $LASTEXITCODE
  }

  $runManyJson = $runManyOutput | ConvertFrom-Json
  if (-not $runManyJson.ok) {
    Write-Error "task.run_many returned ok=false"
    Write-Host $runManyOutput
    exit 1
  }

  Write-Host "PASS: Plugin docker harness"
} finally {
  Cleanup
}
