#Requires -Version 7.0

<#
.SYNOPSIS
    Composes agents/<id>/SOUL.md from build/agent-src/ (agent templates plus shared fragments).
.DESCRIPTION
    Each SOUL.md is generated from build/agent-src/souls/<id>.md, with every include line
    ({{> soul/<NN-id>}}) replaced by build/agent-src/fragments/soul/<NN-id>.md and every
    {{= Key}} replaced by the family Values in build/agent-src/family.psd1. Lines starting
    with "%% " are template comments and are dropped. Never hand-edit a SOUL.md.

    Output is UTF-8 without BOM, LF line endings, exactly one trailing newline, no banner.
    A SOUL.md is written only when its bytes change; no other file is touched. When any error
    is found nothing is written.

    Errors print as "ERROR <path>:<line>: <message>" and the script exits 1; otherwise it
    exits 0 (or 1 under -Check when a SOUL.md drifted).
.PARAMETER RepoRoot
    Repository root holding build/agent-src/ and agents/. Defaults to the parent of this script.
.PARAMETER Agents
    Compose only these agent ids (comma-separated values are accepted). Unknown ids are errors.
    The unused-fragment check runs only when the whole roster is composed.
.PARAMETER Check
    Write nothing. Compare each composed SOUL with the committed file and report every drift
    (a missing file is drift too), then exit 1 if any drifted.
.PARAMETER OutDir
    Write (or, with -Check, compare against) <OutDir>/<id>/SOUL.md instead of agents/<id>/SOUL.md.
.PARAMETER Explain
    Also print each agent's fragment list, the source of every output line, and which agents
    include each fragment.
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Agents developer -OutDir $env:TEMP/souls -Explain
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..'),
    [string[]]$Agents = @(),
    [switch]$Check,
    [string]$OutDir = '',
    [switch]$Explain
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'AgentFamily.psm1') -Force

$exitCode = 0
try {
    if (-not (Test-Path -LiteralPath $RepoRoot -PathType Container)) {
        Write-Output "ERROR ${RepoRoot}:0: repo root not found"
        exit 1
    }
    $root = Resolve-AgentFullPath -Path $RepoRoot

    $family = $null
    try {
        $family = Get-AgentFamily -RepoRoot $root
    }
    catch {
        $message = ($_.Exception.Message -replace '\s+', ' ').Trim()
        $line = 1
        if ($_.Exception.Data.Contains('Line')) { $line = $_.Exception.Data['Line'] }
        Write-Output "ERROR build/agent-src/family.psd1:${line}: cannot load family data: $message"
        exit 1
    }

    $run = Invoke-AgentFamilyCompose -RepoRoot $root -Agents $Agents -Family $family
    $allErrors = @($run['AllErrors'])
    foreach ($item in $allErrors) { Format-AgentComposeError -Item $item }

    $outRoot = ''
    if ($OutDir) { $outRoot = Resolve-AgentFullPath -Path $OutDir }
    $clean = @($run['Results'] | Where-Object { @($_['Errors']).Count -eq 0 })

    $drift = 0
    if ($Check) {
        foreach ($result in $clean) {
            $target = Get-AgentSoulPath -RepoRoot $root -Id $result['Id'] -OutDir $outRoot
            $display = ConvertTo-AgentRepoPath -RepoRoot $root -Path $target
            $committed = $null
            if ([System.IO.File]::Exists($target)) { $committed = [System.IO.File]::ReadAllBytes($target) }
            $diff = Compare-AgentSoulText -CommittedBytes $committed -Result $result
            if ($null -eq $diff) {
                Write-Output "ok $display"
                continue
            }
            $drift++
            Write-Output "DRIFT ${display}: first difference at line $($diff['Line'])"
            Write-Output "  committed: $($diff['Committed'])"
            Write-Output "  composed:  $($diff['Composed'])"
            Write-Output "  from:      $($diff['From'])"
        }
    }
    elseif ($allErrors.Count -gt 0) {
        Write-Output "nothing written: $($allErrors.Count) error(s)"
    }
    else {
        foreach ($result in $clean) {
            $target = Get-AgentSoulPath -RepoRoot $root -Id $result['Id'] -OutDir $outRoot
            $display = ConvertTo-AgentRepoPath -RepoRoot $root -Path $target
            if (Write-AgentSoulFile -Path $target -Text $result['Text']) {
                Write-Output "wrote $display"
            }
            else {
                Write-Output "unchanged $display"
            }
        }
    }

    if ($Explain) {
        foreach ($result in @($run['Results'])) {
            $map = @($result['LineMap'])
            $top = @($result['Fragments'])
            $nested = @(@($result['Included']) | Where-Object { [Array]::IndexOf([string[]]$top, [string]$_) -lt 0 })
            Write-Output "EXPLAIN $($result['Id']): $($map.Count) lines, $($result['Bytes']) bytes"
            Write-Output ('  fragments: ' + $(if ($top.Count) { $top -join ', ' } else { '(none)' }))
            if ($nested.Count) { Write-Output ('  nested:    ' + ($nested -join ', ')) }
            for ($i = 0; $i -lt $map.Count; $i++) {
                Write-Output ("{0}`t{1}:{2}" -f ($i + 1), $map[$i]['Source'], $map[$i]['Line'])
            }
        }
        Write-Output 'FRAGMENT USAGE'
        $fragmentIds = [string[]]@(Get-AgentFragmentIds -RepoRoot $root)
        foreach ($usage in @(Get-AgentFragmentUsage -Results @($run['Results']) -FragmentIds $fragmentIds)) {
            $users = @($usage['Agents'])
            Write-Output ('  {0}: {1}' -f $usage['Id'], $(if ($users.Count) { $users -join ', ' } else { '(none)' }))
        }
    }

    if ($clean.Count -gt 0) { Format-AgentBudgetTable -Results $clean }

    if ($drift -gt 0) {
        Write-Output "$drift SOUL file(s) drifted; run: pwsh -File build/Compose-AgentSouls.ps1"
    }
    if ($allErrors.Count -gt 0 -or $drift -gt 0) { $exitCode = 1 }
}
catch {
    $where = 'build/Compose-AgentSouls.ps1'
    $line = 0
    if ($_.InvocationInfo) {
        if ($_.InvocationInfo.ScriptName) { $where = ([string]$_.InvocationInfo.ScriptName).Replace('\', '/') }
        $line = $_.InvocationInfo.ScriptLineNumber
    }
    $message = ($_.Exception.Message -replace '\s+', ' ').Trim()
    Write-Output "ERROR ${where}:${line}: internal error: $message"
    $exitCode = 1
}
exit $exitCode
