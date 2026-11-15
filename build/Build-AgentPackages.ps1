#Requires -Version 7.0

<#
.SYNOPSIS
    Validates and builds agents/<name> using Sophon's canonical agent-package tooling.
.DESCRIPTION
    Requires Sophon CLI 2.2.0 or newer. Writes versioned .sophon-agent bundles and SHA256SUMS.
    Does not install, publish, or change live agents. Warnings fail closed by default because
    CLI JSON combines publish-blocking issues and advisory warnings. Review every warning
    before explicitly using -AllowWarnings; that switch does not establish publish readiness.
.PARAMETER AllowWarnings
    Print but do not block on reviewed CLI validation warnings. Errors always block.
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')),
    [string]$OutputDir = (Join-Path $RepoRoot 'dist/agents'),
    [string[]]$Agents = @(),
    [switch]$ValidateOnly,
    [switch]$AllowWarnings
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$OutputDir = [IO.Path]::GetFullPath($OutputDir)
$indexPath = Join-Path $OutputDir 'SHA256SUMS'
if (-not $ValidateOnly -and (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
    Remove-Item -LiteralPath $indexPath
}

$agentsDir = Join-Path $RepoRoot 'agents'
$discovered = @(
    if (Test-Path -LiteralPath $agentsDir -PathType Container) {
        Get-ChildItem -LiteralPath $agentsDir -Directory | Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json') -PathType Leaf
        } | Sort-Object Name
    }
)
if ($discovered.Count -eq 0) {
    throw "No agent projects found under '$agentsDir'."
}

$selected = @(
    if ($Agents.Count -eq 0) {
        $discovered
    } else {
        foreach ($name in $Agents) {
            $matches = @($discovered | Where-Object { $_.Name -ceq $name })
            if ($matches.Count -ne 1) {
                throw "Unknown agent selection: '$name'."
            }
            $matches[0]
        }
    }
)

$projects = @(
foreach ($agent in $selected) {
    $manifest = Get-Content -LiteralPath (Join-Path $agent.FullName 'manifest.json') -Raw | ConvertFrom-Json
    if ($null -eq $manifest -or $null -eq $manifest.PSObject.Properties['name'] -or
        $manifest.name -cne $agent.Name) {
        throw "Agent folder '$($agent.Name)' does not exactly match its manifest name."
    }
    $json = & sophon dev validate $agent.FullName --json
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "Validation failed for '$($agent.Name)' (exit $code): $json"
    }
    $result = $json | ConvertFrom-Json
    if (-not $result.ok -or $result.projectType -cne 'agent') {
        throw "Validation failed for '$($agent.Name)': $json"
    }
    # CLI 2.2.0 merges publish-blocking issues and ordinary warnings. Fail closed.
    if (@($result.warnings).Count -gt 0) {
        if (-not $AllowWarnings) {
            throw "Validation warnings for '$($agent.Name)' require review; use -AllowWarnings only after reviewing every warning: $json"
        }
        foreach ($warning in $result.warnings) {
            Write-Warning "$($agent.Name): $($warning.message)"
        }
    }
    [pscustomobject]@{ Directory = $agent.FullName; Name = $agent.Name; Version = $manifest.version }
}
)

if ($ValidateOnly) {
    Write-Host "Validated $($projects.Count) agent project(s)."
    return
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$stage = Join-Path $OutputDir ('.agent-build-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage | Out-Null
try {
    $artifacts = @(
        foreach ($project in $projects) {
            $buildJson = & sophon dev build $project.Directory --output $stage --json
            $code = $LASTEXITCODE
            if ($code -ne 0) {
                throw "Build failed for '$($project.Name)' (exit $code): $buildJson"
            }
            $built = $buildJson | ConvertFrom-Json
            if (-not $built.ok) { throw "Build failed for '$($project.Name)': $buildJson" }
            $filename = "$($project.Name)-$($project.Version).sophon-agent"
            $source = Join-Path $stage "$($project.Name).sophon-agent"
            $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
            [pscustomobject]@{ Source = $source; Filename = $filename; Hash = $hash }
        }
    )
    [string[]]$lines = @(
        foreach ($artifact in $artifacts) {
            Copy-Item -LiteralPath $artifact.Source -Destination (Join-Path $OutputDir $artifact.Filename) -Force
            $line = "$($artifact.Hash)  $($artifact.Filename)"
            Write-Host $line
            $line
        }
    )
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force
}

# Publish the index only after all packages are copied and staging is removed.
# A temporary file on the same filesystem makes the final rename atomic.
[Array]::Sort($lines, [StringComparer]::Ordinal)
$indexTemp = Join-Path $OutputDir ('.agent-index-' + [guid]::NewGuid().ToString('N'))
try {
    [IO.File]::WriteAllText($indexTemp, (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($indexTemp, $indexPath)
}
finally {
    if (Test-Path -LiteralPath $indexTemp -PathType Leaf) {
        Remove-Item -LiteralPath $indexTemp -Force
    }
}
