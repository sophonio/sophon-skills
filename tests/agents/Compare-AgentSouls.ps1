#Requires -Version 7.0

<#
.SYNOPSIS
    Lost-lines report: every line of a base SOUL that no longer occurs in the current SOUL of the same agent.
.DESCRIPTION
    Read-only. Extracts the base tree (build/ and agents/ at -Base) with git archive into a temporary folder,
    composes the base SOULs there with the current composer module (so each base line keeps its source file
    and line), and compares them with the current composed SOULs in agents/<id>/SOUL.md. A base line counts
    as lost when no line of the current SOUL equals it (ordinal, blank lines ignored). The report is grouped
    by agent and, inside an agent, by the base source file, with a count per agent and a total.

    At M4 of docs/plans/2026-11-23-agents-v3-design.md the report must equal the de-duplication cut list;
    after M5 it is reading material and the anchors are the gate. Nothing in the repository is written; the
    temporary folder is removed on exit.

    Exit code 0 when the report ran (lost lines are not a failure), 1 when it could not run.
.PARAMETER Base
    A git ref (tag, branch or commit). Default: agents-v2.1.0.
.PARAMETER Family
    The family to compare (a registry Id). Default: development.
.PARAMETER Agents
    Only these agent ids (comma-separated values are accepted).
.PARAMETER RepoRoot
    Repository root. Defaults to the grandparent of this script.
.PARAMETER Summary
    Print the per-agent counts only.
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Compare-AgentSouls.ps1 -Base agents-v2.1.0
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Compare-AgentSouls.ps1 -Base 3f052f3 -Agents developer -Summary
#>
[CmdletBinding()]
param(
    [string]$Base = 'agents-v2.1.0',
    [string]$Family = 'development',
    [string[]]$Agents = @(),
    [string]$RepoRoot = (Join-Path $PSScriptRoot '../..'),
    [switch]$Summary
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$ord = [StringComparer]::Ordinal

function Invoke-Git {
    param([string[]]$Arguments)
    $output = & git -C $RepoRoot @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed: $(@($output) -join ' ')" }
    $output
}

$temp = Join-Path ([IO.Path]::GetTempPath()) ('sophon-compare-souls-' + [guid]::NewGuid().ToString('N'))
try {
    $commit = [string](@(Invoke-Git @('rev-parse', '--verify', '--quiet', "$Base^{commit}")) | Select-Object -First 1)
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    $archive = Join-Path $temp 'base.tar'
    Invoke-Git @('archive', '--format=tar', "--output=$archive", $commit, 'build', 'agents') | Out-Null
    $baseRoot = Join-Path $temp 'base'
    New-Item -ItemType Directory -Path $baseRoot -Force | Out-Null
    & tar -xf $archive -C $baseRoot
    if ($LASTEXITCODE -ne 0) { throw "tar could not extract the base tree of $Base" }

    Import-Module (Join-Path $RepoRoot 'build/AgentFamily.psm1') -Force
    $requested = [string[]]@(foreach ($entry in $Agents) { foreach ($part in ([string]$entry).Split(',')) { if ($part.Trim()) { $part.Trim() } } })

    # The base side: composed from the base sources, with each line's source.
    $registry = Get-AgentFamilyRegistry -RepoRoot $baseRoot
    $entry = $null
    foreach ($candidate in @($registry['Families'])) { if ([string]::Equals([string]$candidate['Id'], $Family, [StringComparison]::Ordinal)) { $entry = $candidate } }
    if ($null -eq $entry) { throw "the base tree at $Base has no family '$Family'" }
    $null = Set-AgentFamilyContext -Entry $entry
    $baseFamily = Get-AgentFamily -RepoRoot $baseRoot
    $baseRun = Invoke-AgentFamilyCompose -RepoRoot $baseRoot -Family $baseFamily -Agents $requested
    $baseErrors = @($baseRun['AllErrors'])
    if ($baseErrors.Count -gt 0) { throw "the base sources at $Base do not compose: $(Format-AgentComposeError -Item $baseErrors[0])" }

    $totalLost = 0
    $rows = [System.Collections.Generic.List[object]]::new()
    Write-Host "Lost lines: $Family at $Base ($($commit.Substring(0, 12))) against the working tree's agents/<id>/SOUL.md"
    foreach ($result in @($baseRun['Results'])) {
        $id = [string]$result['Id']
        $currentPath = Join-Path $RepoRoot "agents/$id/SOUL.md"
        if (-not (Test-Path -LiteralPath $currentPath -PathType Leaf)) {
            Write-Host ''
            Write-Host "== ${id}: no current SOUL (agent removed); every base line is lost"
        }
        $current = [System.Collections.Generic.HashSet[string]]::new($ord)
        if (Test-Path -LiteralPath $currentPath -PathType Leaf) {
            foreach ($line in [IO.File]::ReadAllText($currentPath).Replace("`r", '').Split("`n")) { [void]$current.Add($line) }
        }
        $baseLines = $result['Text'].TrimEnd("`n").Split("`n")
        $map = @($result['LineMap'])
        $lost = [ordered]@{}
        $count = 0
        for ($i = 0; $i -lt $baseLines.Length; $i++) {
            $line = $baseLines[$i]
            if ([string]::IsNullOrWhiteSpace($line) -or $current.Contains($line)) { continue }
            $source = if ($i -lt $map.Count) { "$($map[$i]['Source']):$($map[$i]['Line'])" } else { '?' }
            $file = if ($i -lt $map.Count) { [string]$map[$i]['Source'] } else { '?' }
            if (-not $lost.Contains($file)) { $lost[$file] = [System.Collections.Generic.List[string]]::new() }
            $lost[$file].Add("  $source  $line")
            $count++
        }
        $totalLost += $count
        $rows.Add([pscustomobject]@{ Id = $id; Lost = $count; Lines = $baseLines.Length })
        if (-not $Summary -and $count -gt 0) {
            Write-Host ''
            Write-Host "== ${id}: $count lost line(s)"
            foreach ($file in $lost.Keys) {
                Write-Host "-- $file ($($lost[$file].Count))"
                foreach ($item in $lost[$file]) { Write-Host $item }
            }
        }
    }
    Write-Host ''
    Write-Host '== Per agent'
    foreach ($row in $rows) { Write-Host ('  {0,-26} {1,5} lost of {2,5} base line(s)' -f $row.Id, $row.Lost, $row.Lines) }
    Write-Host "  total: $totalLost lost line(s) in $($rows.Count) agent(s)"
    exit 0
} catch {
    Write-Host "Compare-AgentSouls: $($_.Exception.Message)"
    exit 1
} finally {
    if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue }
}
