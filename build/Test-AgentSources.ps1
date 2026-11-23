#Requires -Version 7.0

<#
.SYNOPSIS
    Source checks for the agent packages in agents/: layout, SOUL composition, tool-name lint, scanner
    preflight, budgets, manifests, TOOLS.md, attribution and credits. Needs no Sophon CLI.
.DESCRIPTION
    Sections (docs/plans/2026-11-15-agents-v2-design.md section 7.5):
      A  roster and layout       agents/ folders == roster; exactly 5 files each; strict UTF-8, no BOM, CR,
                                 NUL, tabs or hidden characters; one trailing LF; size limits; LICENSE copy
      B  composer                build/Compose-AgentSouls.ps1 -Check in a child pwsh
      C  tool-name lint          SOUL.md, TOOLS.md, README.md, manifest displayName/description/whenToUse
      D  preflight               the same texts through the scanner replay; every fragment <= 4,096 B and
                                 starts with its only "## " heading
      E  budgets                 SOUL <= SoulCap, TOOLS.md <= 2,048 B, README <= 12 KiB (lead 24 KiB);
                                 prints the headroom table
      F  manifest                the family contract (keys, lengths, marker, subAgents, requires.tools)
      G  TOOLS.md                strict grammar, runtime-parser agreement, pin rules
      H  attribution             exact trailer and footer bytes; present in every 12a agent, absent otherwise
      I  credits                 family Credits strings and the canonical credits sentence in each README

    Every issue prints as "ERROR <rule> <path>:<line>: <message>". Exit code 1 on any error, else 0.
    Pure cross-platform PowerShell 7; runs on Linux CI.
.PARAMETER RepoRoot
    Repository root. Defaults to the parent of this script.
.PARAMETER Agents
    Check only these agent ids (comma-separated values are accepted). The folders-equal-roster check runs only
    without -Agents.
.EXAMPLE
    pwsh -NoProfile -File build/Test-AgentSources.ps1
.EXAMPLE
    pwsh -NoProfile -File build/Test-AgentSources.ps1 -Agents lead-developer
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..'),
    [string[]]$Agents = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
Import-Module (Join-Path $PSScriptRoot 'AgentLint.psm1') -Force

$script:Errors = [System.Collections.Generic.List[object]]::new()
$script:SectionCounts = [ordered]@{}
$script:Section = ''

function Enter-Section {
    param([string]$Id, [string]$Title)
    $script:Section = $Id
    $script:SectionCounts[$Id] = 0
    Write-Host ''
    Write-Host "== $Id. $Title"
}

function Add-SourceError {
    param([string]$Rule, [string]$Path, [int]$Line, [string]$Message)
    $script:Errors.Add([pscustomobject]@{ Section = $script:Section; Rule = $Rule; Path = $Path; Line = $Line; Message = $Message })
    $script:SectionCounts[$script:Section]++
    Write-Host "ERROR $Rule ${Path}:${Line}: $Message"
}

function Add-Issues {
    param($Issues, [hashtable]$LineMap = $null, [string]$PathOverride = $null)
    foreach ($issue in @($Issues)) {
        if ($null -eq $issue) { continue }
        $line = [int]$issue.Line
        if ($null -ne $LineMap -and $LineMap.ContainsKey($line)) { $line = $LineMap[$line] }
        $path = if ($PathOverride) { $PathOverride } else { $issue.Path }
        Add-SourceError $issue.Rule $path $line $issue.Message
    }
}

function Get-RelPath {
    param([string]$FullPath)
    return [IO.Path]::GetRelativePath($RepoRoot, $FullPath).Replace('\', '/')
}

function Get-LineAt {
    param([string]$Text, [int]$Index)
    $line = 1
    for ($i = 0; $i -lt $Index -and $i -lt $Text.Length; $i++) { if ($Text[$i] -eq "`n") { $line++ } }
    return $line
}

$utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
$ord = [System.StringComparison]::Ordinal
$ordIgnore = [System.StringComparison]::OrdinalIgnoreCase
$packageFiles = @('LICENSE', 'README.md', 'SOUL.md', 'TOOLS.md', 'manifest.json')

# =============================================================================================================
Enter-Section 'A' 'Roster and layout'
# =============================================================================================================

$familyPath = Join-Path $RepoRoot 'build/agent-src/family.psd1'
try {
    $familyData = Import-PowerShellDataFile -LiteralPath $familyPath
} catch {
    Add-SourceError 'FAMILY-LOAD' 'build/agent-src/family.psd1' 1 "does not load with Import-PowerShellDataFile: $($_.Exception.Message)"
    Write-Host ''
    Write-Host 'Test-AgentSources: cannot continue without family.psd1.'
    exit 1
}

# Prefer the composer's loader when it is present (it sorts Agents ordinally); fall back to the data file.
$family = $familyData
$familyModule = Join-Path $PSScriptRoot 'AgentFamily.psm1'
if (Test-Path -LiteralPath $familyModule -PathType Leaf) {
    try {
        Import-Module $familyModule -Force
        $loaded = AgentFamily\Get-AgentFamily -RepoRoot $RepoRoot
        if ($null -ne (Get-AgentField $loaded 'Agents')) { $family = $loaded }
    } catch {
        Write-Host "note: build/AgentFamily.psm1 did not load the family ($($_.Exception.Message)); using family.psd1 directly"
    }
}

$familyAgents = @(Get-AgentField $family 'Agents' @())
$roster = [System.Collections.Generic.List[string]]::new()
foreach ($agent in $familyAgents) { $roster.Add([string](Get-AgentField $agent 'Id')) }
$roster.Sort([System.StringComparer]::Ordinal)
$agentById = @{}
foreach ($agent in $familyAgents) { $agentById[[string](Get-AgentField $agent 'Id')] = $agent }

$requested = @($Agents | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$selected = [System.Collections.Generic.List[string]]::new()
if ($requested.Count -eq 0) {
    foreach ($id in $roster) { $selected.Add($id) }
} else {
    foreach ($id in $requested) {
        if ($roster.Contains($id)) { if (-not $selected.Contains($id)) { $selected.Add($id) } }
        else { Add-SourceError 'LAYOUT-AGENT' 'build/agent-src/family.psd1' 1 "unknown agent '$id' (roster: $($roster -join ', '))" }
    }
}

$agentsDir = Join-Path $RepoRoot 'agents'
if ($requested.Count -eq 0) {
    $entries = @(if (Test-Path -LiteralPath $agentsDir -PathType Container) { Get-ChildItem -LiteralPath $agentsDir -Force })
    $folders = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $entries) {
        if ($entry.PSIsContainer) { $folders.Add($entry.Name) }
        else { Add-SourceError 'LAYOUT-ROSTER' (Get-RelPath $entry.FullName) 0 'only agent folders may live directly under agents/' }
    }
    foreach ($name in $folders) {
        if (-not $roster.Contains($name)) { Add-SourceError 'LAYOUT-ROSTER' "agents/$name" 0 'folder is not in the family roster (build/agent-src/family.psd1)' }
    }
    foreach ($id in $roster) {
        if (-not $folders.Contains($id)) { Add-SourceError 'LAYOUT-ROSTER' "agents/$id" 0 'roster agent has no folder' }
    }
}

$rootLicensePath = Join-Path $RepoRoot 'LICENSE'
$rootLicense = $null
if (Test-Path -LiteralPath $rootLicensePath -PathType Leaf) { $rootLicense = [IO.File]::ReadAllBytes($rootLicensePath) }
if ($null -eq $rootLicense) { Add-SourceError 'LAYOUT-LICENSE' 'LICENSE' 0 'the repository root LICENSE is missing' }

# texts[id][file] = decoded text (only files that decoded as strict UTF-8); bytes[id][file] = raw bytes.
$texts = @{}
$bytes = @{}
foreach ($id in $selected) {
    $texts[$id] = @{}
    $bytes[$id] = @{}
    $dir = Join-Path $agentsDir $id
    if (-not (Test-Path -LiteralPath $dir -PathType Container)) { continue }

    $total = 0
    foreach ($entry in @(Get-ChildItem -LiteralPath $dir -Force)) {
        $rel = Get-RelPath $entry.FullName
        if ($entry.PSIsContainer) { Add-SourceError 'LAYOUT-FILES' $rel 0 'subfolders are not allowed in a package'; continue }
        if ($entry.Name.StartsWith('.', $ord)) { Add-SourceError 'LAYOUT-FILES' $rel 0 'dotfiles are not allowed in a package'; continue }
        if ($entry.Name -cnotin $packageFiles) { Add-SourceError 'LAYOUT-FILES' $rel 0 "not a package file (allowed: $($packageFiles -join ', '))"; continue }
    }
    foreach ($name in $packageFiles) {
        $path = Join-Path $dir $name
        $rel = "agents/$id/$name"
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { Add-SourceError 'LAYOUT-FILES' $rel 0 'missing'; continue }
        $data = [IO.File]::ReadAllBytes($path)
        $bytes[$id][$name] = $data
        $total += $data.Length
        if ($data.Length -gt 65536) { Add-SourceError 'LAYOUT-SIZE' $rel 0 "$($data.Length) bytes; a package file is at most 65,536" }
        if ($data.Length -ge 3 -and $data[0] -eq 0xEF -and $data[1] -eq 0xBB -and $data[2] -eq 0xBF) {
            Add-SourceError 'LAYOUT-ENCODING' $rel 1 'starts with a UTF-8 BOM'
        }
        $text = $null
        try { $text = $utf8Strict.GetString($data) } catch { Add-SourceError 'LAYOUT-ENCODING' $rel 0 'is not valid UTF-8'; continue }
        if ($text.Length -gt 0 -and $text[0] -eq [char]0xFEFF) { $text = $text.Substring(1) }
        $texts[$id][$name] = $text

        $cr = $text.IndexOf("`r")
        if ($cr -ge 0) { Add-SourceError 'LAYOUT-EOL' $rel (Get-LineAt $text $cr) 'contains CR; use LF line endings' }
        $nul = $text.IndexOf([char]0)
        if ($nul -ge 0) { Add-SourceError 'LAYOUT-ENCODING' $rel (Get-LineAt $text $nul) 'contains NUL' }
        $hidden = [regex]::Match($text, '\p{Cf}|\uDB40[\uDC00-\uDC7F]')
        if ($hidden.Success) { Add-SourceError 'LAYOUT-HIDDEN' $rel (Get-LineAt $text $hidden.Index) ('contains an invisible formatting character (U+{0:X4})' -f [int]$text[$hidden.Index]) }
        if ($text.Length -eq 0 -or -not $text.EndsWith("`n", $ord) -or $text.EndsWith("`n`n", $ord)) {
            Add-SourceError 'LAYOUT-EOL' $rel 0 'must end with exactly one LF'
        }
        if ($name -ne 'LICENSE') {
            $tab = $text.IndexOf("`t")
            if ($tab -ge 0) { Add-SourceError 'LAYOUT-TAB' $rel (Get-LineAt $text $tab) 'contains a tab character' }
            $trailing = [regex]::Match($text, '[ \t]+(?=\r?\n)')
            if ($trailing.Success) { Add-SourceError 'LAYOUT-WHITESPACE' $rel (Get-LineAt $text $trailing.Index) 'trailing whitespace' }
        }
    }
    if ($total -gt 524288) { Add-SourceError 'LAYOUT-SIZE' "agents/$id" 0 "package is $total bytes; at most 524,288" }

    # An agent with its own LicenseFile (family.psd1) copies that file; every other agent copies the root LICENSE.
    $licenseRel = [string](Get-AgentField $agentById[$id] 'LicenseFile' '')
    $expectedLicense = $rootLicense
    $licenseSource = 'the repository root LICENSE'
    if ($licenseRel) {
        $licenseSource = $licenseRel
        $licensePath = Join-Path $RepoRoot $licenseRel
        $expectedLicense = $null
        if (Test-Path -LiteralPath $licensePath -PathType Leaf) { $expectedLicense = [IO.File]::ReadAllBytes($licensePath) }
        else { Add-SourceError 'LAYOUT-LICENSE' $licenseRel 0 "LicenseFile of agent '$id' is missing" }
    }
    if ($null -ne $expectedLicense -and $bytes[$id].ContainsKey('LICENSE')) {
        $mine = $bytes[$id]['LICENSE']
        if ($mine.Length -ne $expectedLicense.Length -or -not [System.Linq.Enumerable]::SequenceEqual([byte[]]$mine, [byte[]]$expectedLicense)) {
            Add-SourceError 'LAYOUT-LICENSE' "agents/$id/LICENSE" 0 "must be a byte-identical copy of $licenseSource"
        }
    }
}

# =============================================================================================================
Enter-Section 'B' 'Composer (Compose-AgentSouls.ps1 -Check)'
# =============================================================================================================

$composer = Join-Path $RepoRoot 'build/Compose-AgentSouls.ps1'
if (-not (Test-Path -LiteralPath $composer -PathType Leaf)) { $composer = Join-Path $PSScriptRoot 'Compose-AgentSouls.ps1' }
if ($requested.Count -gt 0 -and $selected.Count -eq 0) {
    Write-Host '  skipped: no known agent selected'
} elseif (-not (Test-Path -LiteralPath $composer -PathType Leaf)) {
    Add-SourceError 'COMPOSE-MISSING' 'build/Compose-AgentSouls.ps1' 0 'the composer is missing'
} else {
    $pwsh = [Environment]::ProcessPath
    if (-not $pwsh -or [IO.Path]::GetFileNameWithoutExtension($pwsh) -ne 'pwsh') { $pwsh = 'pwsh' }
    $composeArgs = @('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $RepoRoot, '-Check')
    if ($requested.Count -gt 0 -and $selected.Count -gt 0) { $composeArgs += @('-Agents', ($selected -join ',')) }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & $pwsh @composeArgs 2>&1
        $code = $LASTEXITCODE
    } catch {
        $output = @("could not start ${pwsh}: $($_.Exception.Message)")
        $code = -1
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    foreach ($line in @($output)) { Write-Host "  | $line" }
    if ($code -ne 0) {
        Add-SourceError 'COMPOSE-CHECK' 'build/Compose-AgentSouls.ps1' 0 "-Check exited $code (SOUL drift or a source error; run pwsh -File build/Compose-AgentSouls.ps1)"
    }
}

# Shared inputs for C-G.
$catalog = Get-AgentCatalog -RepoRoot $RepoRoot
foreach ($warning in $catalog.Warnings) { Write-Host "note: $warning" }
$rules = Get-ScanRules -RepoRoot $RepoRoot
$allowedHosts = [string[]]@(Get-AgentField $family 'AllowedHosts' @())

# Manifest texts per agent: parsed object, raw text, and the scanned fields with their manifest.json lines.
$manifests = @{}
foreach ($id in $selected) {
    $raw = $texts[$id]['manifest.json']
    if ($null -eq $raw) { continue }
    $parsed = $null
    try { $parsed = $raw | ConvertFrom-Json -ErrorAction Stop } catch { $parsed = $null }
    $fields = [System.Collections.Generic.List[object]]::new()
    if ($null -ne $parsed) {
        $agentObj = Get-AgentField $parsed 'agent'
        foreach ($pair in @(
                @('displayName', (Get-AgentField $parsed 'displayName')),
                @('description', (Get-AgentField $parsed 'description')),
                @('whenToUse', (Get-AgentField $agentObj 'whenToUse')))) {
            if ($pair[1] -is [string] -and $pair[1].Length -gt 0) {
                $lines = $raw.Split("`n")
                $at = 1
                for ($k = 0; $k -lt $lines.Length; $k++) { if ($lines[$k].Contains('"' + $pair[0] + '"')) { $at = $k + 1; break } }
                $fields.Add([pscustomobject]@{ Name = $pair[0]; Text = $pair[1]; Line = $at })
            }
        }
    }
    $manifests[$id] = [pscustomobject]@{ Raw = $raw; Parsed = $parsed; Fields = $fields.ToArray() }
}

# =============================================================================================================
Enter-Section 'C' 'Tool-name lint'
# =============================================================================================================

foreach ($id in $selected) {
    foreach ($pair in @(@('SOUL.md', 'soul'), @('TOOLS.md', 'tools'), @('README.md', 'readme'))) {
        $text = $texts[$id][$pair[0]]
        if ($null -eq $text) { continue }
        Add-Issues (Invoke-ToolNameLint -Text $text -Path "agents/$id/$($pair[0])" -Kind $pair[1] -Catalog $catalog)
    }
    if ($manifests.ContainsKey($id)) {
        foreach ($field in $manifests[$id].Fields) {
            Add-Issues (Invoke-ToolNameLint -Text $field.Text -Path "agents/$id/manifest.json" -Kind 'manifest' -Catalog $catalog) @{ 1 = $field.Line }
        }
    }
}

# =============================================================================================================
Enter-Section 'D' 'Preflight (scanner replay)'
# =============================================================================================================

foreach ($id in $selected) {
    foreach ($pair in @(@('SOUL.md', 'soul'), @('TOOLS.md', 'tools'), @('README.md', 'readme'))) {
        $text = $texts[$id][$pair[0]]
        if ($null -eq $text) { continue }
        Add-Issues (Invoke-AgentPreflight -Text $text -Path "agents/$id/$($pair[0])" -Rules $rules -AllowedHosts $allowedHosts -Kind $pair[1])
    }
    if ($manifests.ContainsKey($id) -and $manifests[$id].Fields.Length -gt 0) {
        # Scanned as one text (displayName, description, whenToUse), as the runtime's AgentPackageScanner does.
        $fields = $manifests[$id].Fields
        $map = @{}
        for ($k = 0; $k -lt $fields.Length; $k++) { $map[$k + 1] = $fields[$k].Line }
        $joined = [string]::Join("`n", [string[]]@($fields | ForEach-Object { $_.Text }))
        Add-Issues (Invoke-AgentPreflight -Text $joined -Path "agents/$id/manifest.json" -Rules $rules -AllowedHosts $allowedHosts -Kind 'manifest') $map
    }
}

$fragmentDir = Join-Path $RepoRoot 'build/agent-src/fragments/soul'
if (Test-Path -LiteralPath $fragmentDir -PathType Container) {
    foreach ($fragment in @(Get-ChildItem -LiteralPath $fragmentDir -File -Filter '*.md' | Sort-Object Name)) {
        $fragRel = Get-RelPath $fragment.FullName
        if ($fragment.Length -gt 4096) {
            Add-SourceError 'BUDGET-FRAGMENT' $fragRel 0 "$($fragment.Length) bytes; a fragment is at most 4,096"
        }
        # Family contract: a fragment starts with exactly one "## <Heading>" line and holds no other heading
        # outside code fences, so each fragment is one section of the composed SOUL.
        $fragLines = [IO.File]::ReadAllText($fragment.FullName) -split "`n"
        if ($fragLines.Length -eq 0 -or $fragLines[0] -cnotmatch '^## \S') {
            Add-SourceError 'FRAGMENT-HEADING' $fragRel 1 'a fragment must start with one "## <Heading>" line'
        }
        $inFence = $false
        for ($k = 1; $k -lt $fragLines.Length; $k++) {
            if ($fragLines[$k].StartsWith('```', [StringComparison]::Ordinal)) { $inFence = -not $inFence; continue }
            if (-not $inFence -and $fragLines[$k] -cmatch '^#{1,6} ') {
                Add-SourceError 'FRAGMENT-HEADING' $fragRel ($k + 1) "a fragment holds one heading, on line 1; found '$($fragLines[$k].Trim())'"
            }
        }
    }
} else {
    Add-SourceError 'BUDGET-FRAGMENT' 'build/agent-src/fragments/soul' 0 'fragment folder is missing'
}

# =============================================================================================================
Enter-Section 'E' 'Budgets'
# =============================================================================================================

$lead = [string](Get-AgentField $family 'Lead' 'lead-developer')
$budgetRows = [System.Collections.Generic.List[object]]::new()
foreach ($id in $selected) {
    $entry = $agentById[$id]
    $cap = [int](Get-AgentField $entry 'SoulCap' 0)
    if ($bytes[$id].ContainsKey('SOUL.md')) {
        $size = $bytes[$id]['SOUL.md'].Length
        if ($cap -le 0) { Add-SourceError 'BUDGET-SOUL' 'build/agent-src/family.psd1' 1 "agent '$id' has no SoulCap" }
        elseif ($size -gt $cap) { Add-SourceError 'BUDGET-SOUL' "agents/$id/SOUL.md" 0 "$size bytes; cap $cap (over by $($size - $cap))" }
        $budgetRows.Add([pscustomobject]@{ Id = $id; Bytes = $size; Cap = $cap })
    }
    if ($bytes[$id].ContainsKey('TOOLS.md') -and $bytes[$id]['TOOLS.md'].Length -gt 2048) {
        Add-SourceError 'BUDGET-TOOLS' "agents/$id/TOOLS.md" 0 "$($bytes[$id]['TOOLS.md'].Length) bytes; at most 2,048"
    }
    $readmeCap = if ($id -ceq $lead) { 24576 } else { 12288 }
    if ($bytes[$id].ContainsKey('README.md') -and $bytes[$id]['README.md'].Length -gt $readmeCap) {
        Add-SourceError 'BUDGET-README' "agents/$id/README.md" 0 "$($bytes[$id]['README.md'].Length) bytes; at most $readmeCap"
    }
}
if ($budgetRows.Count -gt 0) {
    Write-Host ('  {0,-20} {1,8} {2,8} {3,7} {4,10}' -f 'agent', 'bytes', 'cap', 'used', '~tokens')
    foreach ($row in $budgetRows) {
        $pct = if ($row.Cap -gt 0) { '{0:0.0}%' -f (100.0 * $row.Bytes / $row.Cap) } else { 'n/a' }
        Write-Host ('  {0,-20} {1,8:N0} {2,8:N0} {3,7} {4,10:N0}' -f $row.Id, $row.Bytes, $row.Cap, $pct, [Math]::Round($row.Bytes / 3.8))
    }
    Write-Host '  ~tokens = bytes/3.8, an estimate. Body of TOOLS.md (at most 5 lines) is checked in G.'
}

# =============================================================================================================
Enter-Section 'F' 'Manifest'
# =============================================================================================================

$toolsParsed = @{}
foreach ($id in $selected) {
    $toolsText = $texts[$id]['TOOLS.md']
    if ($null -ne $toolsText) { $toolsParsed[$id] = Read-ToolsMd -Text $toolsText -Path "agents/$id/TOOLS.md" }
}
foreach ($id in $selected) {
    if (-not $manifests.ContainsKey($id)) { continue }
    $m = $manifests[$id]
    $tools = if ($toolsParsed.ContainsKey($id)) { $toolsParsed[$id] } else { $null }
    Add-Issues (Test-AgentManifest -Manifest $m.Parsed -Raw $m.Raw -Id $id -Family $family -ToolsMd $tools -Path "agents/$id/manifest.json")
}

# =============================================================================================================
Enter-Section 'G' 'TOOLS.md'
# =============================================================================================================

foreach ($id in $selected) {
    if (-not $toolsParsed.ContainsKey($id)) { continue }
    $parsed = $toolsParsed[$id]
    Add-Issues $parsed.Issues
    Add-Issues (Test-ToolsMdPins -ToolsMd $parsed -Path "agents/$id/TOOLS.md" -Catalog $catalog)
}

# =============================================================================================================
Enter-Section 'H' 'Attribution'
# =============================================================================================================

$values = Get-AgentField $family 'Values' @{}
$trailer = [string](Get-AgentField $values 'CommitTrailer' '')
$footer = [string](Get-AgentField $values 'PrFooter' '')
if (-not $trailer -or -not $footer) {
    Add-SourceError 'ATTR-VALUES' 'build/agent-src/family.psd1' 1 'Values.CommitTrailer and Values.PrFooter are required'
} else {
    $footerAnchor = 'Generated with [Sophon]'
    $anchorOffset = $footer.IndexOf($footerAnchor, $ord)
    $scanDirs = if ($requested.Count -eq 0) { @($agentsDir) } else { @($selected | ForEach-Object { Join-Path $agentsDir $_ }) }
    foreach ($scanDir in $scanDirs) {
        if (-not (Test-Path -LiteralPath $scanDir -PathType Container)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $scanDir -File -Recurse -Force)) {
            $rel = Get-RelPath $file.FullName
            $text = $null
            try { $text = $utf8Strict.GetString([IO.File]::ReadAllBytes($file.FullName)) } catch { continue }

            $at = $text.IndexOf('Co-Authored-By:', $ordIgnore)
            while ($at -ge 0) {
                if ($text.Length - $at -lt $trailer.Length -or -not [string]::Equals($text.Substring($at, $trailer.Length), $trailer, $ord)) {
                    $found = [regex]::Match($text.Substring($at), '^Co-Authored-By:[^"''`\r\n]*', 'IgnoreCase').Value
                    Add-SourceError 'ATTR-TRAILER' $rel (Get-LineAt $text $at) "commit trailer '$found' differs from the canonical '$trailer'"
                }
                $at = $text.IndexOf('Co-Authored-By:', $at + 1, $ordIgnore)
            }

            $at = $text.IndexOf($footerAnchor, $ordIgnore)
            while ($at -ge 0) {
                $start = $at - $anchorOffset
                if ($start -lt 0 -or $text.Length - $start -lt $footer.Length -or -not [string]::Equals($text.Substring($start, $footer.Length), $footer, $ord)) {
                    $found = [regex]::Match($text.Substring([Math]::Max(0, $start)), '^.{0,3}Generated with \[Sophon\]\([^)]*\)?', 'IgnoreCase').Value
                    Add-SourceError 'ATTR-FOOTER' $rel (Get-LineAt $text $at) "PR footer '$found' differs from the canonical footer (U+1F916 without U+FE0F, then ' Generated with [Sophon](https://sophon.buildersoft.io)')"
                }
                $at = $text.IndexOf($footerAnchor, $at + 1, $ordIgnore)
            }

            foreach ($forbidden in 'noreply@anthropic.com', 'claude.com/claude-code') {
                $hit = $text.IndexOf($forbidden, $ordIgnore)
                if ($hit -ge 0) { Add-SourceError 'ATTR-FORBIDDEN' $rel (Get-LineAt $text $hit) "contains '$forbidden'; agents use the Sophon trailer and footer only" }
            }
        }
    }

    foreach ($id in $selected) {
        $soul = $texts[$id]['SOUL.md']
        if ($null -eq $soul) { continue }
        $fragments = @(Get-AgentField $agentById[$id] 'Fragments' @())
        if ($fragments -contains '12a-git-commit') {
            if (-not $soul.Contains($trailer, $ord)) { Add-SourceError 'ATTR-MISSING' "agents/$id/SOUL.md" 0 "includes 12a-git-commit but does not contain the commit trailer '$trailer'" }
            if (-not $soul.Contains($footer, $ord)) { Add-SourceError 'ATTR-MISSING' "agents/$id/SOUL.md" 0 'includes 12a-git-commit but does not contain the PR footer' }
        } else {
            if ($soul.IndexOf('Co-Authored-By:', $ordIgnore) -ge 0) { Add-SourceError 'ATTR-UNEXPECTED' "agents/$id/SOUL.md" (Get-LineAt $soul $soul.IndexOf('Co-Authored-By:', $ordIgnore)) 'a read-only agent (no 12a-git-commit) must not carry the commit trailer' }
            if ($soul.IndexOf($footerAnchor, $ordIgnore) -ge 0) { Add-SourceError 'ATTR-UNEXPECTED' "agents/$id/SOUL.md" (Get-LineAt $soul $soul.IndexOf($footerAnchor, $ordIgnore)) 'a read-only agent (no 12a-git-commit) must not carry the PR footer' }
        }
    }
}

# =============================================================================================================
Enter-Section 'I' 'Credits'
# =============================================================================================================

$creditSentence = 'Workflow patterns adapted, not copied, from obra/superpowers (MIT, ' + [char]0xA9 + ' 2025 Jesse Vincent) and ' +
    'Anthropic''s Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).'
$licenseSentences = @{
    'MIT'        = 'Licensed under the MIT License; see LICENSE.'
    'Apache-2.0' = 'Licensed under the Apache License, Version 2.0; see LICENSE.'
}
$familyLicense = [string](Get-AgentField $family 'License' 'MIT')
$credits = Get-AgentField $family 'Credits' @{}
foreach ($id in $selected) {
    $readme = $texts[$id]['README.md']
    if ($null -eq $readme) { continue }
    $agentLicense = [string](Get-AgentField $agentById[$id] 'License' $familyLicense)
    $licenseSentence = $licenseSentences[$agentLicense]
    if ($null -eq $licenseSentence) {
        Add-SourceError 'CREDITS-LICENSE' 'build/agent-src/family.psd1' 1 "agent '$id' has license '$agentLicense', which has no README sentence (known: $(@($licenseSentences.Keys | Sort-Object) -join ', '))"
        continue
    }
    $rel = "agents/$id/README.md"
    foreach ($key in @(Get-AgentField $agentById[$id] 'Credits' @())) {
        $credit = Get-AgentField $credits ([string]$key)
        if ($null -eq $credit) { Add-SourceError 'CREDITS-KEY' 'build/agent-src/family.psd1' 1 "agent '$id' lists credit '$key', which Credits does not define"; continue }
        if (-not $readme.Contains([string]$credit, $ord)) { Add-SourceError 'CREDITS-MISSING' $rel 0 "missing the credit '$credit'" }
    }
    $sentenceAt = $readme.IndexOf($creditSentence, $ord)
    if ($sentenceAt -lt 0) { Add-SourceError 'CREDITS-SENTENCE' $rel 0 "missing the verbatim credits sentence '$creditSentence'" }
    else {
        $licenseAt = $readme.IndexOf($licenseSentence, $sentenceAt, $ord)
        if ($licenseAt -lt 0) { Add-SourceError 'CREDITS-SENTENCE' $rel (Get-LineAt $readme $sentenceAt) "the credits sentence must be followed by '$licenseSentence'" }
    }
}

# =============================================================================================================
# Summary
# =============================================================================================================

Write-Host ''
Write-Host '== Summary'
foreach ($key in $script:SectionCounts.Keys) {
    Write-Host ('  {0}  {1} error(s)' -f $key, $script:SectionCounts[$key])
}
if ($script:Errors.Count -gt 0) {
    Write-Host "Test-AgentSources: $($script:Errors.Count) error(s) across $($selected.Count) agent(s)."
    exit 1
}
Write-Host "Test-AgentSources: OK ($($selected.Count) agent(s): $($selected -join ', '))."
exit 0
