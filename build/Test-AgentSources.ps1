#Requires -Version 7.0

<#
.SYNOPSIS
    Source checks for the agent packages in agents/: layout, SOUL composition, tool-name lint, scanner
    preflight, budgets, manifests, TOOLS.md, attribution and credits. Needs no Sophon CLI.
.DESCRIPTION
    Sections (docs/plans/2026-11-15-agents-v2-design.md section 7.5), run per agent family:
      A  roster and layout       roster agents have folders; exactly 5 files each; strict UTF-8, no BOM, CR,
                                 NUL, tabs or hidden characters; one trailing LF; size limits; LICENSE copy
      B  composer                build/Compose-AgentSouls.ps1 -Check in a child pwsh
      C  tool-name lint          SOUL.md, TOOLS.md, README.md, manifest displayName/description/whenToUse
      D  preflight               the same texts through the scanner replay; every fragment <= 4,096 B and
                                 starts with its only "## " heading
      E  budgets                 SOUL <= SoulCap, TOOLS.md <= 2,048 B, README <= ReadmeCaps (default 12 KiB,
                                 lead 24 KiB); prints the headroom table
      F  manifest                the family contract (keys, lengths, marker, subAgents, requires) and
                                 MAN-SKILL-VERSION (every SkillPolicy skill exists at its MinVersion or later)
      G  TOOLS.md                strict grammar, runtime-parser agreement, pin rules
      H  attribution             exact trailer and footer bytes; present in every agent that includes a
                                 fragment using {{= CommitTrailer}} or {{= PrFooter}}, absent otherwise
      I  credits                 family Credits strings and the family CreditsSentence in each README

    Families come from build/agent-src/families.psd1. Without -Family this script checks that the agents/
    folders equal the union of every family roster (an id belongs to one family), then runs itself once per
    family (-Family <id>) and fails when any family fails. Without a registry it checks the single family in
    build/agent-src/family.psd1, folders == roster included.

    Every issue prints as "ERROR <rule> <path>:<line>: <message>". Exit code 1 on any error, else 0.
    Pure cross-platform PowerShell 7; runs on Linux CI.
.PARAMETER RepoRoot
    Repository root. Defaults to the parent of this script.
.PARAMETER Agents
    Check only these agent ids (comma-separated values are accepted). The folders-equal-roster check runs only
    without -Agents.
.PARAMETER Family
    Check one family (a registry Id). The agents/-equals-union check runs only without -Family.
.EXAMPLE
    pwsh -NoProfile -File build/Test-AgentSources.ps1
.EXAMPLE
    pwsh -NoProfile -File build/Test-AgentSources.ps1 -Family development
.EXAMPLE
    pwsh -NoProfile -File build/Test-AgentSources.ps1 -Agents lead-developer
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '..'),
    [string[]]$Agents = @(),
    [string]$Family = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
Import-Module (Join-Path $PSScriptRoot 'AgentLint.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'AgentFamily.psm1') -Force

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
# Families: the registry, and the parent pass that runs one child pass per family
# =============================================================================================================

$registry = Get-AgentFamilyRegistry -RepoRoot $RepoRoot
if (@($registry['Errors']).Count -gt 0) {
    Enter-Section 'A' 'Roster and layout'
    foreach ($e in @($registry['Errors'])) { Add-SourceError 'FAMILY-REGISTRY' $e['Path'] $e['Line'] $e['Message'] }
    Write-Host ''
    Write-Host 'Test-AgentSources: cannot continue without a valid family registry.'
    exit 1
}

$requested = @($Agents | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })

if (-not $Family -and -not $registry['Legacy']) {
    # Parent pass: agents/ must hold exactly the union of the family rosters; then each family is checked by a
    # child pass of this script (-Family <id>), and the exit codes are combined.
    $familyIds = [string[]]@($registry['Families'] | ForEach-Object { [string]$_['Id'] })
    Enter-Section 'A' "Roster union ($($familyIds -join ', '))"
    $union = Get-AgentRosterUnion -RepoRoot $RepoRoot
    foreach ($e in @($union['Errors'])) { Add-SourceError 'FAMILY-LOAD' $e['Path'] $e['Line'] $e['Message'] }
    $byFamily = @{}
    if ($requested.Count -eq 0) {
        $agentsRoot = Join-Path $RepoRoot 'agents'
        if (Test-Path -LiteralPath $agentsRoot -PathType Container) {
            foreach ($entry in @(Get-ChildItem -LiteralPath $agentsRoot -Force | Sort-Object Name)) {
                if (-not $entry.PSIsContainer) { Add-SourceError 'LAYOUT-ROSTER' (Get-RelPath $entry.FullName) 0 'only agent folders may live directly under agents/' }
                elseif (-not $union['Owner'].ContainsKey($entry.Name)) { Add-SourceError 'LAYOUT-ROSTER' "agents/$($entry.Name)" 0 "folder is not in any family roster ($($registry['Path']))" }
            }
        }
    } else {
        foreach ($id in $requested) {
            $owner = $null
            if ($union['Owner'].TryGetValue($id, [ref]$owner)) {
                if (-not $byFamily.ContainsKey($owner)) { $byFamily[$owner] = [System.Collections.Generic.List[string]]::new() }
                if (-not $byFamily[$owner].Contains($id)) { $byFamily[$owner].Add($id) }
            } else {
                Add-SourceError 'LAYOUT-AGENT' $registry['Path'] 1 "unknown agent '$id' (roster union: $($union['Ids'] -join ', '))"
            }
        }
    }

    $pwsh = [Environment]::ProcessPath
    if (-not $pwsh -or [IO.Path]::GetFileNameWithoutExtension($pwsh) -ne 'pwsh') { $pwsh = 'pwsh' }
    $results = [System.Collections.Generic.List[object]]::new()
    $childErrors = 0
    $checked = 0
    foreach ($loaded in @($union['Families'])) {
        $id = [string]$loaded['Id']
        $childArgs = @('-NoProfile', '-NonInteractive', '-File', $PSCommandPath, '-RepoRoot', $RepoRoot, '-Family', $id)
        if ($requested.Count -gt 0) {
            if (-not $byFamily.ContainsKey($id)) { continue }
            $childArgs += @('-Agents', ($byFamily[$id] -join ','))
            $checked += $byFamily[$id].Count
        } else {
            $checked += @($loaded['Roster']).Count
        }
        Write-Host ''
        Write-Host "-- family $id ($($loaded['Path']))"
        $previousPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $output = @(& $pwsh @childArgs 2>&1 | ForEach-Object { "$_" })
            $code = $LASTEXITCODE
        } catch {
            $output = @("ERROR FAMILY-PASS build/Test-AgentSources.ps1:0: could not start ${pwsh}: $($_.Exception.Message)")
            $code = -1
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        foreach ($line in $output) { Write-Host $line }
        $childErrors += @($output | Where-Object { $_ -clike 'ERROR *' }).Count
        $results.Add([pscustomobject]@{ Id = $id; Code = $code })
    }

    Write-Host ''
    Write-Host '== Summary'
    Write-Host ('  roster union  {0} error(s)' -f $script:Errors.Count)
    foreach ($result in $results) {
        Write-Host ('  family {0}  {1}' -f $result.Id, $(if ($result.Code -eq 0) { 'OK' } else { "FAILED (exit $($result.Code))" }))
    }
    $failed = @($results | Where-Object { $_.Code -ne 0 } | ForEach-Object { $_.Id })
    if ($script:Errors.Count -gt 0 -or $failed.Count -gt 0) {
        $total = $script:Errors.Count + $childErrors
        Write-Host "Test-AgentSources: $total error(s) across $($results.Count) family pass(es)$(if ($failed.Count) { " (failed: $($failed -join ', '))" })."
        exit 1
    }
    Write-Host "Test-AgentSources: OK ($checked agent(s) in $($results.Count) famil$(if ($results.Count -eq 1) { 'y' } else { 'ies' }): $(@($results | ForEach-Object { $_.Id }) -join ', '))."
    exit 0
}

# =============================================================================================================
Enter-Section 'A' 'Roster and layout'
# =============================================================================================================

try {
    $familyEntry = Set-AgentFamilyContext -RepoRoot $RepoRoot -Family $Family
} catch {
    Add-SourceError 'FAMILY-LOAD' $registry['Path'] 1 $_.Exception.Message
    Write-Host ''
    Write-Host 'Test-AgentSources: cannot continue without a family.'
    exit 1
}
$familyId = [string]$familyEntry['Id']
$familyContext = Get-AgentFamilyContext
$familyRel = [string]$familyContext['FamilyRelPath']
if (-not $registry['Legacy']) { Write-Host "  family $familyId ($familyRel)" }

$familyPath = Join-Path $RepoRoot $familyRel
try {
    $familyData = Import-PowerShellDataFile -LiteralPath $familyPath
} catch {
    Add-SourceError 'FAMILY-LOAD' $familyRel 1 "does not load with Import-PowerShellDataFile: $($_.Exception.Message)"
    Write-Host ''
    Write-Host "Test-AgentSources: cannot continue without $familyRel."
    exit 1
}

# Prefer the composer's loader (it sorts Agents ordinally); fall back to the data file.
$fam = $familyData
try {
    $loaded = Get-AgentFamily -RepoRoot $RepoRoot
    if ($null -ne (Get-AgentField $loaded 'Agents')) { $fam = $loaded }
} catch {
    Write-Host "note: build/AgentFamily.psm1 did not load the family ($($_.Exception.Message)); using $familyRel directly"
}

$familyAgents = @(Get-AgentField $fam 'Agents' @())
$roster = [System.Collections.Generic.List[string]]::new()
foreach ($agent in $familyAgents) { $roster.Add([string](Get-AgentField $agent 'Id')) }
$roster.Sort([System.StringComparer]::Ordinal)
$agentById = @{}
foreach ($agent in $familyAgents) { $agentById[[string](Get-AgentField $agent 'Id')] = $agent }

$selected = [System.Collections.Generic.List[string]]::new()
if ($requested.Count -eq 0) {
    foreach ($id in $roster) { $selected.Add($id) }
} else {
    foreach ($id in $requested) {
        if ($roster.Contains($id)) { if (-not $selected.Contains($id)) { $selected.Add($id) } }
        else { Add-SourceError 'LAYOUT-AGENT' $familyRel 1 "unknown agent '$id' (roster: $($roster -join ', '))" }
    }
}

$agentsDir = Join-Path $RepoRoot 'agents'
if ($requested.Count -eq 0 -and -not $registry['Legacy']) {
    # One family of several: the parent pass checks agents/ against the union of the rosters.
    foreach ($id in $roster) {
        if (-not (Test-Path -LiteralPath (Join-Path $agentsDir $id) -PathType Container)) { Add-SourceError 'LAYOUT-ROSTER' "agents/$id" 0 'roster agent has no folder' }
    }
} elseif ($requested.Count -eq 0) {
    $entries = @(if (Test-Path -LiteralPath $agentsDir -PathType Container) { Get-ChildItem -LiteralPath $agentsDir -Force })
    $folders = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $entries) {
        if ($entry.PSIsContainer) { $folders.Add($entry.Name) }
        else { Add-SourceError 'LAYOUT-ROSTER' (Get-RelPath $entry.FullName) 0 'only agent folders may live directly under agents/' }
    }
    foreach ($name in $folders) {
        if (-not $roster.Contains($name)) { Add-SourceError 'LAYOUT-ROSTER' "agents/$name" 0 "folder is not in the family roster ($familyRel)" }
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

    if ($null -ne $rootLicense -and $bytes[$id].ContainsKey('LICENSE')) {
        $mine = $bytes[$id]['LICENSE']
        if ($mine.Length -ne $rootLicense.Length -or -not [System.Linq.Enumerable]::SequenceEqual([byte[]]$mine, [byte[]]$rootLicense)) {
            Add-SourceError 'LAYOUT-LICENSE' "agents/$id/LICENSE" 0 'must be a byte-identical copy of the repository root LICENSE'
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
    if (-not $registry['Legacy']) { $composeArgs += @('-Family', $familyId) }
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
$allowedHosts = [string[]]@(Get-AgentField $fam 'AllowedHosts' @())
# Skill tools are named and pinned only by a family whose SkillPolicy lists their skill; restricted names in
# AllowRestrictedMentions may be named un-negated (never pinned).
$allowedSkillTools = Get-AgentAllowedSkillTools -Family $fam -Catalog $catalog
$allowRestricted = [string[]]@(@(Get-AgentField $fam 'AllowRestrictedMentions' @()) | Where-Object { $_ -is [string] })
$skillPolicy = Get-AgentSkillPolicy $fam

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
        Add-Issues (Invoke-ToolNameLint -Text $text -Path "agents/$id/$($pair[0])" -Kind $pair[1] -Catalog $catalog -AllowedSkillTools $allowedSkillTools -AllowRestrictedMentions $allowRestricted)
    }
    if ($manifests.ContainsKey($id)) {
        foreach ($field in $manifests[$id].Fields) {
            Add-Issues (Invoke-ToolNameLint -Text $field.Text -Path "agents/$id/manifest.json" -Kind 'manifest' -Catalog $catalog -AllowedSkillTools $allowedSkillTools -AllowRestrictedMentions $allowRestricted) @{ 1 = $field.Line }
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

$fragmentDir = Join-Path $RepoRoot $familyContext['FragmentsRelDir']
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
    Add-SourceError 'BUDGET-FRAGMENT' $familyContext['FragmentsRelDir'] 0 'fragment folder is missing'
}

# =============================================================================================================
Enter-Section 'E' 'Budgets'
# =============================================================================================================

$lead = [string](Get-AgentField $fam 'Lead' 'lead-developer')
$readmeCaps = Get-AgentField $fam 'ReadmeCaps'
$readmeCapLead = [int](Get-AgentField $readmeCaps 'Lead' 24576)
$readmeCapOther = [int](Get-AgentField $readmeCaps 'Other' 12288)
$budgetRows = [System.Collections.Generic.List[object]]::new()
foreach ($id in $selected) {
    $entry = $agentById[$id]
    $cap = [int](Get-AgentField $entry 'SoulCap' 0)
    if ($bytes[$id].ContainsKey('SOUL.md')) {
        $size = $bytes[$id]['SOUL.md'].Length
        if ($cap -le 0) { Add-SourceError 'BUDGET-SOUL' $familyRel 1 "agent '$id' has no SoulCap" }
        elseif ($size -gt $cap) { Add-SourceError 'BUDGET-SOUL' "agents/$id/SOUL.md" 0 "$size bytes; cap $cap (over by $($size - $cap))" }
        $budgetRows.Add([pscustomobject]@{ Id = $id; Bytes = $size; Cap = $cap })
    }
    if ($bytes[$id].ContainsKey('TOOLS.md') -and $bytes[$id]['TOOLS.md'].Length -gt 2048) {
        Add-SourceError 'BUDGET-TOOLS' "agents/$id/TOOLS.md" 0 "$($bytes[$id]['TOOLS.md'].Length) bytes; at most 2,048"
    }
    $readmeCap = if ($id -ceq $lead) { $readmeCapLead } else { $readmeCapOther }
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
    Add-Issues (Test-AgentManifest -Manifest $m.Parsed -Raw $m.Raw -Id $id -Family $fam -ToolsMd $tools -Path "agents/$id/manifest.json" -Catalog $catalog)
}

# MAN-SKILL-VERSION: every SkillPolicy skill is in skills/ at its MinVersion or later.
foreach ($skill in $skillPolicy.Skills) {
    $skillRel = "skills/$($skill.Name)/manifest.json"
    $skillPath = Join-Path $RepoRoot $skillRel
    if (-not (Test-Path -LiteralPath $skillPath -PathType Leaf)) {
        Add-SourceError 'MAN-SKILL-VERSION' $skillRel 0 "the family SkillPolicy requires skill '$($skill.Name)', which has no manifest in skills/"
        continue
    }
    $skillVersion = $null
    try { $skillVersion = Get-AgentField (Get-Content -LiteralPath $skillPath -Raw -Encoding utf8 | ConvertFrom-Json -ErrorAction Stop) 'version' } catch { $skillVersion = $null }
    $have = if ($skillVersion -is [string]) { [regex]::Match($skillVersion, '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$') } else { $null }
    if ($null -eq $have -or -not $have.Success) {
        Add-SourceError 'MAN-SKILL-VERSION' $skillRel 1 "version '$skillVersion' is not SemVer"
        continue
    }
    if ($null -eq $skill.MinVersion) { continue }
    $need = [regex]::Match($skill.MinVersion, '^(\d+)\.(\d+)\.(\d+)$')
    $haveCore = [version]::new([int]$have.Groups[1].Value, [int]$have.Groups[2].Value, [int]$have.Groups[3].Value)
    $needCore = [version]::new([int]$need.Groups[1].Value, [int]$need.Groups[2].Value, [int]$need.Groups[3].Value)
    $preRelease = $skillVersion.Contains('-')
    if ($haveCore -lt $needCore -or ($haveCore -eq $needCore -and $preRelease)) {
        Add-SourceError 'MAN-SKILL-VERSION' $skillRel 1 "version $skillVersion is below the SkillPolicy MinVersion $($skill.MinVersion) ($familyRel)"
    }
}

# =============================================================================================================
Enter-Section 'G' 'TOOLS.md'
# =============================================================================================================

foreach ($id in $selected) {
    if (-not $toolsParsed.ContainsKey($id)) { continue }
    $parsed = $toolsParsed[$id]
    Add-Issues $parsed.Issues
    Add-Issues (Test-ToolsMdPins -ToolsMd $parsed -Path "agents/$id/TOOLS.md" -Catalog $catalog -AllowedSkillTools $allowedSkillTools)
}

# =============================================================================================================
Enter-Section 'H' 'Attribution'
# =============================================================================================================

$values = Get-AgentField $fam 'Values' @{}
$trailer = [string](Get-AgentField $values 'CommitTrailer' '')
$footer = [string](Get-AgentField $values 'PrFooter' '')

# Which agents carry attribution: those whose template or included fragments use {{= CommitTrailer}} or
# {{= PrFooter}} (the commit and PR fragments). Derived from the sources, so no fragment name is hardcoded.
$attributionUsers = @{}
$sourceTexts = @{}
foreach ($id in $selected) {
    $users = [System.Collections.Generic.List[string]]::new()
    $composed = $null
    try { $composed = Invoke-AgentCompose -RepoRoot $RepoRoot -Id $id -Family $fam } catch { $composed = $null }
    if ($null -ne $composed) {
        $sources = @([pscustomobject]@{ Name = $id; Rel = [string]$composed['Template'] }) +
            @(@($composed['Included']) | ForEach-Object { [pscustomobject]@{ Name = [string]$_; Rel = (Get-AgentFragmentPath -RepoRoot $RepoRoot -FragmentId ([string]$_)) } })
        foreach ($source in $sources) {
            if (-not $sourceTexts.ContainsKey($source.Rel)) {
                $full = Join-Path $RepoRoot $source.Rel
                $sourceTexts[$source.Rel] = if (Test-Path -LiteralPath $full -PathType Leaf) { [IO.File]::ReadAllText($full) } else { '' }
            }
            $sourceText = $sourceTexts[$source.Rel]
            if ($sourceText.Contains('{{= CommitTrailer}}', $ord) -or $sourceText.Contains('{{= PrFooter}}', $ord)) { $users.Add($source.Name) }
        }
    }
    $attributionUsers[$id] = $users.ToArray()
}
$usesAttribution = @($selected | Where-Object { $attributionUsers[$_].Count -gt 0 }).Count -gt 0

if ($usesAttribution -and (-not $trailer -or -not $footer)) {
    Add-SourceError 'ATTR-VALUES' $familyRel 1 'Values.CommitTrailer and Values.PrFooter are required (an agent includes a commit or PR fragment)'
} else {
    $footerAnchor = 'Generated with [Sophon]'
    $anchorOffset = if ($footer) { $footer.IndexOf($footerAnchor, $ord) } else { -1 }
    # The legacy single family scans every file under agents/; a family of several scans its own folders.
    $scanDirs = if ($requested.Count -eq 0 -and $registry['Legacy']) { @($agentsDir) } else { @($selected | ForEach-Object { Join-Path $agentsDir $_ }) }
    foreach ($scanDir in $scanDirs) {
        if (-not (Test-Path -LiteralPath $scanDir -PathType Container)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $scanDir -File -Recurse -Force)) {
            $rel = Get-RelPath $file.FullName
            $isSoul = [string]::Equals($file.Name, 'SOUL.md', $ord)
            $text = $null
            try { $text = $utf8Strict.GetString([IO.File]::ReadAllBytes($file.FullName)) } catch { continue }

            $at = $text.IndexOf('Co-Authored-By:', $ordIgnore)
            while ($at -ge 0) {
                if (-not $trailer) {
                    if (-not $isSoul) { Add-SourceError 'ATTR-UNEXPECTED' $rel (Get-LineAt $text $at) "a commit trailer, but $familyRel defines no Values.CommitTrailer" }
                } elseif ($text.Length - $at -lt $trailer.Length -or -not [string]::Equals($text.Substring($at, $trailer.Length), $trailer, $ord)) {
                    $found = [regex]::Match($text.Substring($at), '^Co-Authored-By:[^"''`\r\n]*', 'IgnoreCase').Value
                    Add-SourceError 'ATTR-TRAILER' $rel (Get-LineAt $text $at) "commit trailer '$found' differs from the canonical '$trailer'"
                }
                $at = $text.IndexOf('Co-Authored-By:', $at + 1, $ordIgnore)
            }

            $at = $text.IndexOf($footerAnchor, $ordIgnore)
            while ($at -ge 0) {
                $start = $at - $anchorOffset
                if (-not $footer) {
                    if (-not $isSoul) { Add-SourceError 'ATTR-UNEXPECTED' $rel (Get-LineAt $text $at) "a PR footer, but $familyRel defines no Values.PrFooter" }
                } elseif ($start -lt 0 -or $text.Length - $start -lt $footer.Length -or -not [string]::Equals($text.Substring($start, $footer.Length), $footer, $ord)) {
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
        $users = @($attributionUsers[$id])
        if ($users.Count -gt 0) {
            if (-not $soul.Contains($trailer, $ord)) { Add-SourceError 'ATTR-MISSING' "agents/$id/SOUL.md" 0 "includes $($users -join ', ') but does not contain the commit trailer '$trailer'" }
            if (-not $soul.Contains($footer, $ord)) { Add-SourceError 'ATTR-MISSING' "agents/$id/SOUL.md" 0 "includes $($users -join ', ') but does not contain the PR footer" }
        } else {
            if ($soul.IndexOf('Co-Authored-By:', $ordIgnore) -ge 0) { Add-SourceError 'ATTR-UNEXPECTED' "agents/$id/SOUL.md" (Get-LineAt $soul $soul.IndexOf('Co-Authored-By:', $ordIgnore)) 'an agent without a commit or PR fragment must not carry the commit trailer' }
            if ($soul.IndexOf($footerAnchor, $ordIgnore) -ge 0) { Add-SourceError 'ATTR-UNEXPECTED' "agents/$id/SOUL.md" (Get-LineAt $soul $soul.IndexOf($footerAnchor, $ordIgnore)) 'an agent without a commit or PR fragment must not carry the PR footer' }
        }
    }
}

# =============================================================================================================
Enter-Section 'I' 'Credits'
# =============================================================================================================

# CreditsSentence: the family's verbatim README sentence (absent or empty: no sentence check).
$creditSentence = [string](Get-AgentField $fam 'CreditsSentence' '')
$licenseSentence = 'Licensed under the MIT License; see LICENSE.'
$credits = Get-AgentField $fam 'Credits' @{}
foreach ($id in $selected) {
    $readme = $texts[$id]['README.md']
    if ($null -eq $readme) { continue }
    $rel = "agents/$id/README.md"
    foreach ($key in @(Get-AgentField $agentById[$id] 'Credits' @())) {
        $credit = Get-AgentField $credits ([string]$key)
        if ($null -eq $credit) { Add-SourceError 'CREDITS-KEY' $familyRel 1 "agent '$id' lists credit '$key', which Credits does not define"; continue }
        if (-not $readme.Contains([string]$credit, $ord)) { Add-SourceError 'CREDITS-MISSING' $rel 0 "missing the credit '$credit'" }
    }
    if (-not $creditSentence) { continue }
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
$familyNote = if ($registry['Legacy']) { '' } else { " in family $familyId" }
Write-Host "Test-AgentSources: OK ($($selected.Count) agent(s)$($familyNote): $($selected -join ', '))."
exit 0
