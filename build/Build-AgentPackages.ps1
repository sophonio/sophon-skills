#Requires -Version 7.0

<#
.SYNOPSIS
    Validates and builds the Buildersoft agent families (agents/<id>) with Sophon's agent-package CLI.
.DESCRIPTION
    Order (docs/plans/2026-11-15-agents-v2-design.md section 7.4):
      1. Load every family in build/agent-src/families.psd1 (or the single build/agent-src/family.psd1 when
         there is no registry). The roster is the union of the family rosters; an id in two families fails.
         The agents/ folders must equal the roster ids exactly, and every -Agents entry must be a roster id.
      2. 'sophon' must be on PATH and 'sophon --version' must match the SophonCli pattern of every family
         being built. The CLI version and 'git rev-parse --short HEAD' are printed.
      3. build/Compose-AgentSouls.ps1 -Check (every SOUL.md must equal its composed text).
      4. build/Test-AgentSources.ps1 (-Agents <selection> on a subset build).
      5. 'sophon dev validate <dir> --json' per selected agent. Any error and ANY warning fails the build.
      6. -ValidateOnly stops here.
      7. 'sophon dev build' into a staging folder, then stale *.sophon-agent files are removed (all of them on a
         full build, only the selected ids on a subset build), <id>-<version>.sophon-agent is written for each
         selected agent and SHA256SUMS is written atomically, one line per package in ordinal file-name order.

    A build that is not -ValidateOnly first deletes SHA256SUMS, so a failed build never leaves a success index
    behind; older packages can remain on disk until the next successful build. Upload only after a successful
    full build. This script never installs or publishes anything.
.PARAMETER RepoRoot
    Repository root. Defaults to the parent of this script.
.PARAMETER OutputDir
    Output folder for the packages and SHA256SUMS. Defaults to <RepoRoot>/dist/agents.
.PARAMETER Agents
    Build only these agent ids (comma-separated values are accepted). Unknown ids fail the build.
.PARAMETER ValidateOnly
    Run every check, write nothing.
.PARAMETER Family
    Build only this family (a registry Id). Its agents must have folders; folders of other families are
    checked by a build without -Family. A build of fewer families than the registry lists is a subset build.
.PARAMETER Release
    Release build (alias -StrictHeadroom): passes -Release to Test-AgentSources.ps1, so its release-gated findings
    (BUDGET-HEADROOM under 5% free, a missing RoleCap) fail the build instead of warning.
.EXAMPLE
    pwsh -NoProfile -File build/Build-AgentPackages.ps1 -ValidateOnly
.EXAMPLE
    pwsh -NoProfile -File build/Build-AgentPackages.ps1
.EXAMPLE
    pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Agents lead-developer,code-reviewer
.EXAMPLE
    pwsh -NoProfile -File build/Build-AgentPackages.ps1 -Family development
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..'),
    [string]$OutputDir = '',
    [string[]]$Agents = @(),
    [switch]$ValidateOnly,
    [string]$Family = '',
    [Alias('StrictHeadroom')][switch]$Release
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'AgentFamily.psm1') -Force

function Resolve-FullPath([string]$Path) {
    return [IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path))
}

function Invoke-Native {
    # Runs a native command with stderr merged into the output; never throws on stderr or a non-zero exit.
    param([string]$FilePath, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $lines = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } catch {
        $lines = @("could not start ${FilePath}: $($_.Exception.Message)")
        $code = -1
    } finally {
        $ErrorActionPreference = $previous
    }
    return [pscustomobject]@{ Code = $code; Lines = $lines }
}

function Invoke-NativeJson {
    # Runs a CLI command that prints JSON on stdout; stderr is kept apart so it cannot corrupt the JSON.
    param([string]$FilePath, [string[]]$Arguments)
    $errFile = [IO.Path]::GetTempFileName()
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $stdout = @(& $FilePath @Arguments 2>$errFile | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
        $stderr = [IO.File]::ReadAllText($errFile).Trim()
    } finally {
        $ErrorActionPreference = $previous
        Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
    }
    $text = ($stdout -join "`n").Trim()
    $json = $null
    try { $json = $text | ConvertFrom-Json -ErrorAction Stop } catch { $json = $null }
    return [pscustomobject]@{ Code = $code; Text = $text; Json = $json; Stderr = $stderr }
}

function Get-Field($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) { if ($Object.Contains($Name)) { return $Object[$Name] }; return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Format-CliIssue($Issue) {
    $message = [string](Get-Field $Issue 'message')
    $where = @(@((Get-Field $Issue 'file'), (Get-Field $Issue 'field')) | Where-Object { $_ }) -join ' '
    if ($where) { return "$message ($where)" }
    return $message
}

function Get-RepoScript([string]$Name) {
    $inRepo = Join-Path $RepoRoot "build/$Name"
    if (Test-Path -LiteralPath $inRepo -PathType Leaf) { return $inRepo }
    $beside = Join-Path $PSScriptRoot $Name
    if (Test-Path -LiteralPath $beside -PathType Leaf) { return $beside }
    throw "Missing build/$Name."
}

$ordinal = [StringComparer]::Ordinal
$pwsh = [Environment]::ProcessPath
if (-not $pwsh -or [IO.Path]::GetFileNameWithoutExtension($pwsh) -ne 'pwsh') { $pwsh = 'pwsh' }

try {
    $RepoRoot = Resolve-FullPath $RepoRoot
    if (-not $OutputDir) { $OutputDir = Join-Path $RepoRoot 'dist/agents' }
    $OutputDir = Resolve-FullPath $OutputDir
    $agentsDir = Join-Path $RepoRoot 'agents'
    $indexPath = Join-Path $OutputDir 'SHA256SUMS'

    # Stale index: a build that does not finish must not leave a success index behind.
    if (-not $ValidateOnly -and (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        Remove-Item -LiteralPath $indexPath -Force
    }

    # 1. Family rosters, folders and selection. -----------------------------------------------------------
    $registry = Get-AgentFamilyRegistry -RepoRoot $RepoRoot
    $registryErrors = @($registry['Errors'])
    if ($registryErrors.Count -gt 0) { throw "family registry error: $(Format-AgentComposeError -Item $registryErrors[0])" }
    $familyFilter = @(if ($Family) { $Family })
    $union = Get-AgentRosterUnion -RepoRoot $RepoRoot -Family $familyFilter
    $unionErrors = @($union['Errors'])
    if ($unionErrors.Count -gt 0) {
        throw "agent families do not load: $(@($unionErrors | ForEach-Object { Format-AgentComposeError -Item $_ }) -join '; ')"
    }
    $families = @($union['Families'])
    $rosterSource = if ($registry['Legacy']) { 'build/agent-src/family.psd1' } else { $registry['Path'] }
    $roster = [string[]]@($union['Ids'])
    if ($roster.Count -eq 0) { throw "$rosterSource lists no agents." }
    $partialFamilies = -not $registry['Legacy'] -and $families.Count -lt @($registry['Families']).Count

    $relativeOut = [IO.Path]::GetRelativePath($agentsDir, $OutputDir)
    if ($relativeOut -eq '.' -or -not ($relativeOut.StartsWith('..') -or [IO.Path]::IsPathRooted($relativeOut))) {
        throw "OutputDir '$OutputDir' is inside agents/; choose a folder outside the package sources."
    }

    $rosterSet = [System.Collections.Generic.HashSet[string]]::new([string[]]$roster, $ordinal)
    $folders = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $agentsDir -PathType Container) {
        foreach ($folder in @(Get-ChildItem -LiteralPath $agentsDir -Directory -Force)) { $folders.Add($folder.Name) }
    }
    $folders.Sort($ordinal)
    $folderSet = [System.Collections.Generic.HashSet[string]]::new([string[]]$folders.ToArray(), $ordinal)
    $missing = @($roster | Where-Object { -not $folderSet.Contains($_) })
    # A -Family build sees only its own roster, so other families' folders are not extra.
    $extra = @(if (-not $partialFamilies) { $folders | Where-Object { -not $rosterSet.Contains($_) } })
    if ($missing.Count -gt 0 -or $extra.Count -gt 0) {
        $parts = @()
        if ($missing.Count -gt 0) { $parts += "roster ids without a folder: $($missing -join ', ')" }
        if ($extra.Count -gt 0) { $parts += "folders not in the roster: $($extra -join ', ')" }
        throw "agents/ folders must equal the roster in $rosterSource ($($parts -join '; '))."
    }

    $requested = @($Agents | ForEach-Object { "$_" -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    foreach ($name in $requested) {
        if (-not $rosterSet.Contains($name)) { throw "Unknown agent selection: '$name' (roster: $($roster -join ', '))." }
    }
    $requestedSet = [System.Collections.Generic.HashSet[string]]::new([string[]]$requested, $ordinal)
    $selected = @(if ($requested.Count -eq 0) { $roster } else { $roster | Where-Object { $requestedSet.Contains($_) } })
    $selectionSubset = $selected.Count -lt $roster.Count
    $subset = $selectionSubset -or $partialFamilies
    $selectedSet = [System.Collections.Generic.HashSet[string]]::new([string[]]$selected, $ordinal)
    $builtFamilies = @($families | Where-Object { @($_['Roster'] | Where-Object { $selectedSet.Contains($_) }).Count -gt 0 })

    $projects = @(foreach ($id in $selected) {
            $dir = Join-Path $agentsDir $id
            $manifestPath = Join-Path $dir 'manifest.json'
            if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "agents/$id has no manifest.json." }
            $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json
            $manifestName = [string](Get-Field $manifest 'name')
            $version = [string](Get-Field $manifest 'version')
            if (-not [string]::Equals($manifestName, $id, [StringComparison]::Ordinal)) {
                throw "Agent folder '$id' does not exactly match its manifest name '$manifestName'."
            }
            if ($version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') { throw "agents/$id/manifest.json has no SemVer version ('$version')." }
            [pscustomobject]@{ Id = $id; Directory = $dir; Version = $version }
        })
    Write-Host "Agents: $($selected -join ', ')$(if ($subset) { " ($($selected.Count) of $($roster.Count))" })"

    # 2. Sophon CLI and commit. ----------------------------------------------------------------------------
    $sophon = Get-Command 'sophon' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $sophon) {
        throw "The Sophon CLI ('sophon') is not on PATH; install Sophon $($builtFamilies[0]['Data']['MinSophonVersion']) or later."
    }
    $sophonPath = $sophon.Source
    $versionRun = Invoke-Native $sophonPath @('--version')
    $versionLine = [string](@($versionRun.Lines | Where-Object { "$_".Trim() }) | Select-Object -First 1)
    $versionLine = $versionLine.Trim()
    if ($versionRun.Code -ne 0) { throw "'sophon --version' exited $($versionRun.Code): $($versionRun.Lines -join ' ')" }
    foreach ($built in $builtFamilies) {
        $pattern = [string]$built['Data']['SophonCli']
        if ($versionLine -notmatch $pattern) {
            throw "Sophon CLI '$versionLine' does not match $pattern ($($built['Path']) SophonCli)."
        }
    }
    Write-Host "Sophon CLI: $versionLine"
    $commit = 'n/a (git not found)'
    if (Get-Command 'git' -CommandType Application -ErrorAction SilentlyContinue) {
        $gitRun = Invoke-Native 'git' @('-C', $RepoRoot, 'rev-parse', '--short', 'HEAD')
        $commit = if ($gitRun.Code -eq 0 -and $gitRun.Lines.Count -gt 0) { $gitRun.Lines[0].Trim() } else { 'n/a (not a git checkout)' }
    }
    Write-Host "Commit: $commit"

    # 3. Composer drift check. -----------------------------------------------------------------------------
    $composer = Get-RepoScript 'Compose-AgentSouls.ps1'
    $composeArgs = @('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $RepoRoot, '-Check')
    if ($Family) { $composeArgs += @('-Family', $Family) }
    $compose = Invoke-Native $pwsh $composeArgs
    if ($compose.Code -ne 0) {
        foreach ($line in $compose.Lines) { Write-Host "  | $line" }
        throw "SOUL drift — run the composer (pwsh -File build/Compose-AgentSouls.ps1); Compose-AgentSouls.ps1 -Check exited $($compose.Code)."
    }
    Write-Host "Compose-AgentSouls -Check: ok ($(@($compose.Lines | Where-Object { $_ -clike 'ok *' }).Count) SOUL file(s) match)"

    # 4. Source checks. ------------------------------------------------------------------------------------
    $sources = Get-RepoScript 'Test-AgentSources.ps1'
    $sourceArgs = @('-NoProfile', '-NonInteractive', '-File', $sources, '-RepoRoot', $RepoRoot)
    if ($Family) { $sourceArgs += @('-Family', $Family) }
    if ($selectionSubset) { $sourceArgs += @('-Agents', ($selected -join ',')) }
    if ($Release) { $sourceArgs += '-Release' }
    $sourceRun = Invoke-Native $pwsh $sourceArgs
    if ($sourceRun.Code -ne 0) {
        foreach ($line in $sourceRun.Lines) { Write-Host "  | $line" }
        throw "Test-AgentSources.ps1 failed (exit $($sourceRun.Code)); fix the errors listed above."
    }
    Write-Host "Test-AgentSources: ok"

    # 5. CLI validation: zero errors and zero warnings. ---------------------------------------------------
    $failed = [System.Collections.Generic.List[string]]::new()
    foreach ($project in $projects) {
        $run = Invoke-NativeJson $sophonPath @('dev', 'validate', $project.Directory, '--json')
        $json = $run.Json
        $errors = @(Get-Field $json 'errors' | Where-Object { $null -ne $_ })
        $warnings = @(Get-Field $json 'warnings' | Where-Object { $null -ne $_ })
        $problems = [System.Collections.Generic.List[string]]::new()
        if ($run.Code -ne 0) { $problems.Add("exit code $($run.Code)") }
        if ($null -eq $json) { $problems.Add("output is not JSON: $($run.Text) $($run.Stderr)".Trim()) }
        else {
            if ((Get-Field $json 'ok') -ne $true) { $problems.Add('ok is not true') }
            if (-not [string]::Equals([string](Get-Field $json 'projectType'), 'agent', [StringComparison]::Ordinal)) {
                $problems.Add("projectType is '$(Get-Field $json 'projectType')', not 'agent'")
            }
        }
        foreach ($issue in $errors) { $problems.Add("error: $(Format-CliIssue $issue)") }
        foreach ($issue in $warnings) { $problems.Add("warning: $(Format-CliIssue $issue)") }
        if ($problems.Count -eq 0) {
            Write-Host "sophon dev validate $($project.Id): ok (0 errors, 0 warnings)"
        } else {
            Write-Host "sophon dev validate $($project.Id): FAILED"
            foreach ($problem in $problems) { Write-Host "  $($project.Id): $problem" }
            $failed.Add($project.Id)
        }
    }
    if ($failed.Count -gt 0) {
        throw "sophon dev validate reported errors or warnings for: $($failed -join ', '). Warnings fail the build; fix the source, never acknowledge them away."
    }

    if ($ValidateOnly) {
        Write-Host "Validated $($projects.Count) agent package(s); nothing written (-ValidateOnly)."
        exit 0
    }

    # 7. Build, replace stale packages, write SHA256SUMS. ----------------------------------------------
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $stage = Join-Path $OutputDir ('.agent-build-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $stage | Out-Null
    $lines = [System.Collections.Generic.List[string]]::new()
    try {
        $artifacts = @(foreach ($project in $projects) {
                $run = Invoke-NativeJson $sophonPath @('dev', 'build', $project.Directory, '--output', $stage, '--json')
                $json = $run.Json
                if ($run.Code -ne 0 -or $null -eq $json -or (Get-Field $json 'ok') -ne $true) {
                    throw "sophon dev build failed for '$($project.Id)' (exit $($run.Code)): $($run.Text) $($run.Stderr)"
                }
                $buildIssues = @(@(Get-Field $json 'errors') + @(Get-Field $json 'warnings') | Where-Object { $null -ne $_ })
                if ($buildIssues.Count -gt 0) {
                    throw "sophon dev build reported issues for '$($project.Id)': $(@($buildIssues | ForEach-Object { Format-CliIssue $_ }) -join '; ')"
                }
                $source = [string](Get-Field $json 'outputPath')
                if (-not $source) { $source = Join-Path $stage "$($project.Id).sophon-agent" }
                if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "sophon dev build wrote no package for '$($project.Id)' ($source)." }
                $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
                [pscustomobject]@{ Id = $project.Id; Source = $source; Filename = "$($project.Id)-$($project.Version).sophon-agent"; Hash = $hash }
            })

        # Stale packages: every *.sophon-agent on a full build; only the selected ids' packages on a subset build.
        foreach ($file in @(Get-ChildItem -LiteralPath $OutputDir -File -Filter '*.sophon-agent' -Force)) {
            $stale = -not $subset
            if ($subset) {
                foreach ($id in $selected) {
                    if ($file.Name -cmatch ('^' + [regex]::Escape($id) + '-\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?\.sophon-agent$')) { $stale = $true }
                }
            }
            if ($stale) {
                Remove-Item -LiteralPath $file.FullName -Force
                Write-Host "removed stale $($file.Name)"
            }
        }

        foreach ($artifact in $artifacts) {
            Copy-Item -LiteralPath $artifact.Source -Destination (Join-Path $OutputDir $artifact.Filename) -Force
        }
        $names = [string[]]@($artifacts | ForEach-Object { $_.Filename })
        [Array]::Sort($names, $ordinal)
        foreach ($name in $names) {
            $artifact = @($artifacts | Where-Object { [string]::Equals($_.Filename, $name, [StringComparison]::Ordinal) })[0]
            $lines.Add("$($artifact.Hash)  $($artifact.Filename)")
        }
    } finally {
        Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Publish the index only after every package is copied and staging is removed. A temporary file on the
    # same filesystem makes the final rename atomic.
    $indexTemp = Join-Path $OutputDir ('.agent-index-' + [guid]::NewGuid().ToString('N'))
    try {
        [IO.File]::WriteAllText($indexTemp, (($lines -join "`n") + "`n"), [Text.UTF8Encoding]::new($false))
        [IO.File]::Move($indexTemp, $indexPath, $true)
    } finally {
        if (Test-Path -LiteralPath $indexTemp -PathType Leaf) { Remove-Item -LiteralPath $indexTemp -Force }
    }

    foreach ($line in $lines) { Write-Host $line }
    if ($subset) { Write-Host "SHA256SUMS covers only: $($selected -join ', ')" }
    Write-Host "Built $($lines.Count) agent package(s) into $OutputDir"
    exit 0
} catch {
    Write-Host "Build-AgentPackages: FAILED: $($_.Exception.Message)"
    exit 1
}
