#Requires -Version 7.0

<#
.SYNOPSIS
    Composes agents/<id>/SOUL.md from build/agent-src/ (agent templates plus shared fragments).
.DESCRIPTION
    Families are listed in build/agent-src/families.psd1 (without it: the single family in
    build/agent-src/family.psd1). For each family, with <dir> the folder of its family file, each
    SOUL.md is generated from <dir>/souls/<id>.md, with every include line ({{> soul/<NN-id>}})
    replaced by <dir>/fragments/soul/<NN-id>.md and every {{= Key}} replaced by that family's
    Values. Lines starting with "%% " are template comments and are dropped. Never hand-edit a
    SOUL.md. Families never share templates or fragments; an agent id belongs to one family.

    Output is UTF-8 without BOM, LF line endings, exactly one trailing newline, no banner.
    A SOUL.md is written only when its bytes change; no other file is touched. When any error
    is found nothing is written.

    Errors print as "ERROR <path>:<line>: <message>" and the script exits 1; otherwise it
    exits 0 (or 1 under -Check when a SOUL.md drifted).
.PARAMETER RepoRoot
    Repository root holding build/agent-src/ and agents/. Defaults to the parent of this script.
.PARAMETER Family
    Compose only these families (registry Ids; comma-separated values are accepted). Default: every
    registered family. Unknown names are errors.
.PARAMETER Agents
    Compose only these agent ids (comma-separated values are accepted). Unknown ids are errors.
    The unused-fragment check runs per family, only when that family's whole roster is composed.
.PARAMETER Check
    Write nothing. Compare each composed SOUL with the committed file and report every drift
    (a missing file is drift too), then exit 1 if any drifted.
.PARAMETER OutDir
    Write (or, with -Check, compare against) <OutDir>/<id>/SOUL.md instead of agents/<id>/SOUL.md.
.PARAMETER Omit
    Control arms for the instruction tests: compose without these ids (comma-separated values are accepted).
    A fragment id (NN-name) or a whole-fragment Method rule drops that include line; a block rule (Anchor)
    drops its lines, and one of two blank lines around it. Valid only with -OutDir and never with -Check,
    so an ablated SOUL cannot reach agents/. Every selected agent must carry every id. The script prints
    what it removed: the id, the source and line range, the lines and the bytes.
.PARAMETER Explain
    Also print each agent's fragment list, the source of every output line, and which agents
    include each fragment.
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Check
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Family development -Check
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Agents developer -OutDir $env:TEMP/souls -Explain
.EXAMPLE
    pwsh -NoProfile -File build/Compose-AgentSouls.ps1 -Agents developer -Omit test-first -OutDir $env:TEMP/ctl
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..'),
    [string[]]$Agents = @(),
    [switch]$Check,
    [string]$OutDir = '',
    [switch]$Explain,
    [string[]]$Family = @(),
    [string[]]$Omit = @()
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
    $omitIds = [string[]]@(foreach ($entry in $Omit) { foreach ($part in ([string]$entry).Split(',')) { if ($part.Trim()) { $part.Trim() } } })
    if ($omitIds.Length -gt 0 -and (-not $OutDir -or $Check)) {
        Write-Output "ERROR build/Compose-AgentSouls.ps1:0: -Omit is valid only with -OutDir and never with -Check (an ablated SOUL must not reach agents/)"
        exit 1
    }

    # Families: every registered family, or the -Family selection (the legacy single family without a registry).
    $registry = Get-AgentFamilyRegistry -RepoRoot $root
    $registryErrors = @($registry['Errors'])
    foreach ($item in $registryErrors) { Format-AgentComposeError -Item $item }
    if ($registryErrors.Count -gt 0) { exit 1 }
    $knownFamilies = [string[]]@(foreach ($f in @($registry['Families'])) { [string]$f['Id'] })
    $wantedFamilies = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $Family) {
        foreach ($part in ([string]$entry).Split(',')) {
            $name = $part.Trim()
            if (-not $name -or $wantedFamilies.Contains($name)) { continue }
            if ([Array]::IndexOf($knownFamilies, $name) -lt 0) {
                Write-Output "ERROR $($registry['Path']):1: unknown family '$name' (families: $($knownFamilies -join ', '))"
                exit 1
            }
            $wantedFamilies.Add($name)
        }
    }
    $entries = @(@($registry['Families']) | Where-Object { $wantedFamilies.Count -eq 0 -or $wantedFamilies.Contains([string]$_['Id']) })
    $multi = $entries.Count -gt 1

    # Several families: ids are unique across them, and each -Agents id goes to the family that owns it.
    $agentsByFamily = @{}
    if ($multi) {
        $union = Get-AgentRosterUnion -RepoRoot $root -Family ([string[]]@($entries | ForEach-Object { $_['Id'] }))
        $unionErrors = @($union['Errors'])
        foreach ($item in $unionErrors) { Format-AgentComposeError -Item $item }
        if ($unionErrors.Count -gt 0) { exit 1 }
        $requested = [System.Collections.Generic.List[string]]::new()
        foreach ($entry in $Agents) {
            foreach ($part in ([string]$entry).Split(',')) {
                $name = $part.Trim()
                if ($name -and -not $requested.Contains($name)) { $requested.Add($name) }
            }
        }
        $unknownAgents = 0
        foreach ($name in $requested) {
            $owner = $null
            if (-not $union['Owner'].TryGetValue($name, [ref]$owner)) {
                Write-Output "ERROR $($registry['Path']):1: unknown agent '$name' (not in any family roster)"
                $unknownAgents++
                continue
            }
            if (-not $agentsByFamily.ContainsKey($owner)) { $agentsByFamily[$owner] = [System.Collections.Generic.List[string]]::new() }
            $agentsByFamily[$owner].Add($name)
        }
        if ($unknownAgents -gt 0) { exit 1 }
        if ($requested.Count -gt 0) {
            $entries = @($entries | Where-Object { $agentsByFamily.ContainsKey([string]$_['Id']) })
        }
    }

    # Phase 1: compose every selected family. Nothing is written unless every family composed cleanly.
    $runs = [System.Collections.Generic.List[object]]::new()
    $allErrors = [System.Collections.Generic.List[object]]::new()
    foreach ($entry in $entries) {
        $null = Set-AgentFamilyContext -Entry $entry
        $familyRel = [string](Get-AgentFamilyContext)['FamilyRelPath']
        if ($multi) { Write-Output "family $($entry['Id']) ($familyRel)" }
        $familyData = $null
        try {
            $familyData = Get-AgentFamily -RepoRoot $root
        }
        catch {
            $message = ($_.Exception.Message -replace '\s+', ' ').Trim()
            $line = 1
            if ($_.Exception.Data.Contains('Line')) { $line = $_.Exception.Data['Line'] }
            Write-Output "ERROR ${familyRel}:${line}: cannot load family data: $message"
            exit 1
        }
        $familyAgents = $Agents
        if ($multi) {
            $familyAgents = if ($agentsByFamily.ContainsKey([string]$entry['Id'])) { [string[]]$agentsByFamily[[string]$entry['Id']].ToArray() } else { [string[]]@() }
        }
        $run = Invoke-AgentFamilyCompose -RepoRoot $root -Agents $familyAgents -Family $familyData -Omit $omitIds
        foreach ($item in @($run['AllErrors'])) {
            Format-AgentComposeError -Item $item
            $allErrors.Add($item)
        }
        $runs.Add(@{ Id = [string]$entry['Id']; Run = $run; FragmentIds = [string[]]@(Get-AgentFragmentIds -RepoRoot $root) })
    }

    $outRoot = ''
    if ($OutDir) { $outRoot = Resolve-AgentFullPath -Path $OutDir }
    if ($omitIds.Length -gt 0) {
        $agentsRoot = [IO.Path]::Combine($root, 'agents')
        $relOut = [IO.Path]::GetRelativePath($agentsRoot, $outRoot)
        if ($relOut -eq '.' -or -not ($relOut.StartsWith('..') -or [IO.Path]::IsPathRooted($relOut))) {
            Write-Output "ERROR build/Compose-AgentSouls.ps1:0: -Omit writes to -OutDir, which must be outside agents/ (got $outRoot)"
            exit 1
        }
    }
    $results = @(foreach ($r in $runs) { @($r['Run']['Results']) })
    $clean = @($results | Where-Object { @($_['Errors']).Count -eq 0 })

    foreach ($result in $clean) {
        foreach ($record in @($result['Omitted'])) {
            $what = if ($record['Rule']) { "rule $($record['Rule'])" } else { "fragment $($record['Id'])" }
            $where = if ($record['Include']) { "include line $($record['Include']):$($record['From'])" } else { "$($record['Source']):$($record['From'])-$($record['To'])" }
            Write-Output "omit $($result['Id']): $what from $($record['Source']) ($where), $($record['Lines']) line(s), $($record['Bytes']) byte(s)"
        }
    }

    # Phase 2: compare or write.
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
        foreach ($result in $results) {
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
        foreach ($r in $runs) {
            Write-Output $(if ($multi) { "FRAGMENT USAGE ($($r['Id']))" } else { 'FRAGMENT USAGE' })
            foreach ($usage in @(Get-AgentFragmentUsage -Results @($r['Run']['Results']) -FragmentIds $r['FragmentIds'])) {
                $users = @($usage['Agents'])
                Write-Output ('  {0}: {1}' -f $usage['Id'], $(if ($users.Count) { $users -join ', ' } else { '(none)' }))
            }
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
