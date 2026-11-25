#Requires -Version 7.0
<#
.SYNOPSIS
    The craft-reference topic checks that need the PowerShell data files (design "Generator rules").
.DESCRIPTION
    generate.py checks the corpus itself (CRAFT-REGISTRY to CRAFT-RULES). This script holds every topic to the
    SOUL text rules of the development family, so a topic can move into an agent package unchanged:

      LINT-*          Invoke-ToolNameLint (kind soul) over each topic, with no skill tool allowed
      SCAN-*          Invoke-AgentPreflight (kind soul) with the development family's AllowedHosts
      CRAFT-NOTOOLS   a topic outside the agent family names a Sophon tool
      CRAFT-DIGEST    a colour value of fragment 21-sophon-default is missing from topic design-sophon-default
                      (skipped until that fragment exists)

    Front matter is checked by generate.py and is not part of the text checked here. No Sophon CLI needed.
.EXAMPLE
    pwsh -NoProfile -File build/craft-reference/Test-CraftSources.ps1
#>
[CmdletBinding()]
param([string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $RepoRoot 'build/AgentLint.psm1') -Force

$errors = [System.Collections.Generic.List[string]]::new()
$catalog = Get-AgentCatalog -RepoRoot $RepoRoot
$rules = Get-ScanRules -RepoRoot $RepoRoot
$family = Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'build/agent-src/family.psd1')
$hosts = [string[]]@($family['AllowedHosts'])
$registry = Get-Content -LiteralPath (Join-Path $RepoRoot 'build/craft-reference/topics.index.json') -Raw -Encoding utf8 | ConvertFrom-Json
$toolRx = [regex]::new('(?<![\w./\\@:-])([a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+)(?![\w/\\(@-]|\.[A-Za-z0-9_])')
$checked = 0

foreach ($entry in $registry) {
    $rel = "build/craft-reference/topics/$($entry.family)/$($entry.id).md"
    $full = Join-Path $RepoRoot $rel
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { $errors.Add("CRAFT-REGISTRY ${rel}: missing (generate.py reports it too)"); continue }
    $lines = [IO.File]::ReadAllText($full) -split "`n"
    # The body starts after the second --- line; line numbers stay those of the file.
    $close = [Array]::IndexOf($lines, '---', 1)
    if ($lines[0] -ne '---' -or $close -lt 0) { $errors.Add("CRAFT-FRONT ${rel}:1: front matter is missing (generate.py reports it too)"); continue }
    $offset = $close + 1
    $body = ($lines[$offset..($lines.Length - 1)]) -join "`n"
    $checked++

    foreach ($issue in @(Invoke-ToolNameLint -Text $body -Path $rel -Kind 'soul' -Catalog $catalog)) {
        $errors.Add("$($issue.Rule) ${rel}:$($issue.Line + $offset): $($issue.Message)")
    }
    foreach ($issue in @(Invoke-AgentPreflight -Text $body -Path $rel -Rules $rules -AllowedHosts $hosts -Kind 'soul')) {
        $errors.Add("$($issue.Rule) ${rel}:$($issue.Line + $offset): $($issue.Message)")
    }
    if ($entry.family -ne 'agent') {
        $bodyLines = $body -split "`n"
        for ($i = 0; $i -lt $bodyLines.Length; $i++) {
            foreach ($m in $toolRx.Matches($bodyLines[$i])) {
                $name = $m.Groups[1].Value
                if ($catalog.Allowed.Contains($name) -or $catalog.Denied.ContainsKey($name) -or $catalog.SkillTools.Contains($name) -or
                    $catalog.RestrictedExact.Contains($name)) {
                    $errors.Add("CRAFT-NOTOOLS ${rel}:$($i + 1 + $offset): names the Sophon tool $name; only agent-family topics name tools")
                }
            }
        }
    }
}

# CRAFT-DIGEST: the inline Sophon digest never disagrees with the full tables.
$digestRel = 'build/agent-src/fragments/soul/21-sophon-default.md'
$digestPath = Join-Path $RepoRoot $digestRel
if (Test-Path -LiteralPath $digestPath -PathType Leaf) {
    $topicPath = Join-Path $RepoRoot 'build/craft-reference/topics/design/design-sophon-default.md'
    $topicText = if (Test-Path -LiteralPath $topicPath -PathType Leaf) { [IO.File]::ReadAllText($topicPath).ToLowerInvariant() } else { '' }
    foreach ($m in [regex]::Matches([IO.File]::ReadAllText($digestPath), '#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b')) {
        if (-not $topicText.Contains($m.Value.ToLowerInvariant())) {
            $errors.Add("CRAFT-DIGEST ${digestRel}: colour $($m.Value) is not in topic design-sophon-default")
        }
    }
} else {
    Write-Host "note: CRAFT-DIGEST skipped: $digestRel does not exist yet"
}

foreach ($e in $errors) { Write-Host "ERROR $e" }
if ($errors.Count -gt 0) {
    Write-Host "Test-CraftSources: $($errors.Count) error(s) in $checked topic(s)."
    exit 1
}
Write-Host "Test-CraftSources: OK ($checked topic(s))."
exit 0
