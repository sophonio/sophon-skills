#Requires -Version 7.0
<#
.SYNOPSIS
    The scenario lint, the transcript scorer and the workspace preparation of the instruction tests
    (docs/plans/2026-11-23-agents-v3-design.md, "Instruction tests").
.DESCRIPTION
    Used by tests/agents/evals/Invoke-AgentEvals.ps1 and by section M of tests/agents/Test-AgentPackages.ps1.
    Nothing here starts, stops or calls a Sophon Gateway; Invoke-AgentEvals.ps1 alone runs the CLI, in its live mode.

    Data: the four tier files beside this module (acceptance.psd1, pressure.psd1, design.psd1, voice.psd1), each
    @{ Tier; Scenarios = @(...) } plus optional shared Uses blocks (pressure: OptOut; design: Markers), and the
    smoke ids of scenarios.md. Findings are @{ Level = 'error' | 'note'; Rule; Path; Line; Message }.
#>
Set-StrictMode -Version Latest

$script:Tiers = [ordered]@{ acceptance = 'ACC'; pressure = 'PRS'; design = 'DSN'; voice = 'VOC' }
$script:Pressures = @('time', 'sunk-cost', 'authority', 'economic', 'exhaustion', 'social', 'pragmatic')
$script:Modes = @('chat', 'plan', 'delegated')
$script:SkillStates = @('absent', 'installed')
$script:LeakRun = 40
$script:PendingRegex = '^M[0-9]+$'
$script:SmokeIdRegex = '^[A-Z]+[0-9]+$'
$script:WriteTools = @('fs.write', 'fs.edit', 'fs.multi_edit', 'fs.apply_patch', 'fs.create_directory', 'fs.copy', 'fs.move', 'fs.delete')
$script:CommandTools = @('os.execute', 'os.execute_sandboxed')
# Event kinds a Pass or Fail entry may use, with the type of their value. A run gets no approvals: a card is
# rejected and a question skipped, and the turn goes on, so the first moves are the evidence and the calls after
# a refusal are the agent continuing (spike 5).
$script:EventKinds = [ordered]@{
    FirstTool    = 'string'     # the first tool call (a tool name; * allowed)
    FirstWrite   = 'string'     # the path of the first write, as a glob (** any depth)
    FirstCommand = 'string'     # a regex the first command text matches
    FirstOf      = 'hashtable'  # @{ Tools = @(...); Is = '<tool>' }: of these tools, the one called first
    Before       = 'hashtable'  # @{ Is = '<regex>'; Then = '<regex>' }: a command matching Is comes before any
                                # command matching Then (os.execute text; code.git as 'git <operation>')
    Question     = 'string'     # an info.request question with this header
    FirstOption  = 'string'     # a regex the first option label of the first question matches
    ChatQuestion = 'bool'       # the turn ends with a question in chat (no info.request)
    Says         = 'string'     # a regex the final reply matches (case-insensitive)
    Tool         = 'string'     # any call of this tool
    NoTool       = 'string'     # no call of this tool
    NoWrite      = 'string'     # no attempted write to a path matching this glob
    NoMarker     = 'bool'       # no attempted write carries a Sophon marker value (design.psd1 Markers)
    MaxCalls     = 'hashtable'  # @{ Tool = '<tool>'; Max = <n> }
}
$script:CommonKeys = @('Id', 'Tier', 'Agent', 'Fixture', 'Setup', 'Turns', 'Brief', 'Mode', 'Skill', 'SameRunAs', 'Manual', 'Pass', 'Fail', 'Uses', 'Read', 'Pending')
$script:PressureKeys = @('Rule', 'Pressures', 'Control')

function New-EvalFinding([string]$Level, [string]$Rule, [string]$Path, [int]$Line, [string]$Message) {
    @{ Level = $Level; Rule = $Rule; Path = $Path; Line = $Line; Message = $Message }
}

function Get-EvalItems($Value) {
    if ($null -eq $Value) { return @() }
    if ($Value -is [string] -or $Value -is [hashtable]) { return @($Value) }
    return @($Value)
}

function Test-EvalGlob([string]$Path, [string]$Glob) {
    # ** spans folders, * stays inside one; matched against the forward-slash relative path, case-insensitive.
    $p = $Path.Replace('\', '/').TrimStart('.', '/')
    $rx = '^' + ([regex]::Escape($Glob.Replace('\', '/')) -replace '\\\*\\\*/?', '<<ANY>>' -replace '\\\*', '[^/]*' -replace '<<ANY>>', '.*') + '$'
    return [regex]::IsMatch($p, $rx, 'IgnoreCase')
}

function Test-EvalToolName([string]$Name, [string[]]$Allowed) {
    if ($Name.Contains('*')) {
        $rx = '^' + ([regex]::Escape($Name) -replace '\\\*', '.*') + '$'
        return @($Allowed | Where-Object { $_ -match $rx }).Count -gt 0
    }
    return $Allowed -ccontains $Name
}

function Get-EvalIdLine([string]$Text, [string]$Id) {
    if (-not $Text -or -not $Id) { return 0 }
    $lines = $Text.Split("`n")
    $needle = "Id = '$Id'"
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].Contains($needle)) { return $i + 1 } }
    return 0
}

function Get-EvalKeyLine([string]$Text, [string]$Key) {
    if (-not $Text) { return 0 }
    $lines = $Text.Split("`n")
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i] -match "^\s*$([regex]::Escape($Key))\s*=") { return $i + 1 } }
    return 0
}

# ---------------------------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------------------------

function Get-AgentEvalSmokeIds {
    <#
    .SYNOPSIS
        The scenario ids of scenarios.md: its table rows and its "## <Id> — " / "### <Id> — " headings.
    .DESCRIPTION
        Returns @(@{ Id; Line; Kind = 'heading' | 'row' }).
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Text)
    $lines = $Text.Replace("`r", '').Split("`n")
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $heading = [regex]::Match($lines[$i], '^#{2,4} ([A-Za-z0-9-]+) — ')
        if ($heading.Success) { @{ Id = $heading.Groups[1].Value; Line = $i + 1; Kind = 'heading' }; continue }
        $row = [regex]::Match($lines[$i], '^\| ([A-Za-z0-9-]+) \| ')
        if ($row.Success -and $row.Groups[1].Value -cne 'Id') { @{ Id = $row.Groups[1].Value; Line = $i + 1; Kind = 'row' } }
    }
}

function Import-AgentEvalData {
    <#
    .SYNOPSIS
        Reads the four tier files and the smoke ids from an evals folder.
    .DESCRIPTION
        Returns @{ Files = @{ <tier> = @{ Path; Text; Data } }; Smoke = @(...); SmokePath; Findings = @(...) }.
        A missing or unparsable tier file is an EVAL-FILE error. Paths are relative to RepoRoot when the folder
        is inside it.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$EvalRoot,
        [string]$RepoRoot = ''
    )
    $findings = [System.Collections.Generic.List[object]]::new()
    $files = @{}
    $rel = {
        param([string]$Full)
        if ($RepoRoot -and $Full.StartsWith($RepoRoot, [StringComparison]::OrdinalIgnoreCase)) {
            return $Full.Substring($RepoRoot.Length).TrimStart('\', '/').Replace('\', '/')
        }
        return $Full.Replace('\', '/')
    }
    foreach ($tier in $script:Tiers.Keys) {
        $full = Join-Path $EvalRoot "$tier.psd1"
        $path = & $rel $full
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            $findings.Add((New-EvalFinding 'error' 'EVAL-FILE' $path 0 "the $tier tier file is missing"))
            continue
        }
        $text = [IO.File]::ReadAllText($full).Replace("`r", '')
        try {
            $data = Import-PowerShellDataFile -LiteralPath $full -ErrorAction Stop
        } catch {
            $findings.Add((New-EvalFinding 'error' 'EVAL-FILE' $path 0 "cannot be read as a data file: $(($_.Exception.Message -replace '\s+', ' ').Trim())"))
            continue
        }
        $files[$tier] = @{ Path = $path; Text = $text; Data = $data }
    }
    $smokeFull = Join-Path $EvalRoot 'scenarios.md'
    $smoke = @()
    if (Test-Path -LiteralPath $smokeFull -PathType Leaf) {
        $smoke = @(Get-AgentEvalSmokeIds -Text ([IO.File]::ReadAllText($smokeFull)))
    } else {
        $findings.Add((New-EvalFinding 'error' 'EVAL-FILE' (& $rel $smokeFull) 0 'scenarios.md is missing'))
    }
    @{ Files = $files; Smoke = $smoke; SmokePath = (& $rel $smokeFull); Findings = $findings.ToArray() }
}

function Get-AgentEvalFixtureInfo {
    <#
    .SYNOPSIS
        Reads every fixture folder under <EvalRoot>/fixtures: its fixture.psd1, its patches and its file texts.
    .DESCRIPTION
        Returns @{ Fixtures = @{ <name> = @{ Dir; Base; Patches = @{ <name> = @{ File; Exists; Commit; Branch } }; Files = @(@{ Path; Text }); Error } };
        Briefs = @{ <file name> = <text> } }.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$EvalRoot)
    $fixtures = @{}
    $briefs = @{}
    $root = Join-Path $EvalRoot 'fixtures'
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { return @{ Fixtures = $fixtures; Briefs = $briefs } }
    foreach ($dir in @(Get-ChildItem -LiteralPath $root -Directory)) {
        if ($dir.Name -ceq 'briefs') {
            foreach ($file in @(Get-ChildItem -LiteralPath $dir.FullName -File -Filter '*.md')) {
                $briefs[$file.Name] = [IO.File]::ReadAllText($file.FullName).Replace("`r", '')
            }
            continue
        }
        $info = @{ Dir = $dir.FullName; Base = ''; Patches = @{}; Files = @(); Error = ''; Test = '' }
        $manifest = Join-Path $dir.FullName 'fixture.psd1'
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
            $info['Error'] = 'has no fixture.psd1'
        } else {
            try {
                $data = Import-PowerShellDataFile -LiteralPath $manifest -ErrorAction Stop
                if ($data.ContainsKey('Base')) { $info['Base'] = [string]$data['Base'] }
                if ($data.ContainsKey('Test')) { $info['Test'] = [string]$data['Test'] }
                $patches = $data['Patches']
                if ($null -ne $patches -and $patches -isnot [hashtable]) { $info['Error'] = 'Patches must be @{ <name> = @{ Why; Commit; Branch } }' }
                elseif ($null -ne $patches) {
                    foreach ($name in @($patches.Keys)) {
                        $entry = $patches[$name]
                        $file = Join-Path $dir.FullName "patches/$name.patch"
                        $info['Patches'][$name] = @{
                            File   = $file
                            Exists = (Test-Path -LiteralPath $file -PathType Leaf)
                            Commit = if ($entry -is [hashtable] -and $entry.ContainsKey('Commit')) { [string]$entry['Commit'] } else { '' }
                            Branch = if ($entry -is [hashtable] -and $entry.ContainsKey('Branch')) { [string]$entry['Branch'] } else { '' }
                            Why    = if ($entry -is [hashtable] -and $entry.ContainsKey('Why')) { [string]$entry['Why'] } else { '' }
                        }
                    }
                }
            } catch {
                $info['Error'] = "fixture.psd1 cannot be read: $(($_.Exception.Message -replace '\s+', ' ').Trim())"
            }
        }
        $filesDir = Join-Path $dir.FullName 'files'
        $texts = [System.Collections.Generic.List[object]]::new()
        if (Test-Path -LiteralPath $filesDir -PathType Container) {
            foreach ($file in @(Get-ChildItem -LiteralPath $filesDir -File -Recurse)) {
                $relative = [IO.Path]::GetRelativePath($dir.FullName, $file.FullName).Replace('\', '/')
                $texts.Add(@{ Path = $relative; Text = [IO.File]::ReadAllText($file.FullName) })
            }
        }
        foreach ($patch in @($info['Patches'].Values)) {
            if ($patch['Exists']) {
                $texts.Add(@{ Path = [IO.Path]::GetRelativePath($dir.FullName, $patch['File']).Replace('\', '/'); Text = [IO.File]::ReadAllText($patch['File']) })
            }
        }
        $info['Files'] = $texts.ToArray()
        $fixtures[$dir.Name] = $info
    }
    @{ Fixtures = $fixtures; Briefs = $briefs }
}

function Get-AgentEvalContext {
    <#
    .SYNOPSIS
        Everything the scenario lint checks the data against, read from the repository.
    .DESCRIPTION
        Returns @{ Agents = @{ <id> = @{ Family; Fragments; DisplayName } }; Methods = @{ <family> = <Method or $null> };
        DefaultFamily; FragmentText = @{ <family> = @{ <fragment id> = <text> } }; SoulText = @{ <id> = <text> };
        Fixtures; Briefs; Corpus; Mentions; Tools; Errors }.
        Corpus is every text file under agents/ and build/agent-src/, joined with a separator no run can cross.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$EvalRoot
    )
    Import-Module (Join-Path $RepoRoot 'build/AgentFamily.psm1') -Force -Global
    $errors = [System.Collections.Generic.List[string]]::new()
    $union = Get-AgentRosterUnion -RepoRoot $RepoRoot
    foreach ($e in @($union['Errors'])) { $errors.Add((Format-AgentComposeError -Item $e)) }
    $agents = @{}
    $methods = @{}
    $fragmentText = @{}
    $soulText = @{}
    $default = ''
    foreach ($family in @($union['Families'])) {
        $id = [string]$family['Id']
        if (-not $default) { $default = $id }
        $data = $family['Data']
        $methods[$id] = if ($data.ContainsKey('Method')) { $data['Method'] } else { $null }
        $dir = Join-Path $RepoRoot ([string]$family['Dir'])
        $fragmentText[$id] = @{}
        $fragmentDir = Join-Path $dir 'fragments/soul'
        if (Test-Path -LiteralPath $fragmentDir -PathType Container) {
            foreach ($file in @(Get-ChildItem -LiteralPath $fragmentDir -File -Filter '*.md')) {
                $fragmentText[$id][$file.BaseName] = [IO.File]::ReadAllText($file.FullName).Replace("`r", '')
            }
        }
        foreach ($agent in @($data['Agents'])) {
            $agentId = [string]$agent['Id']
            $agents[$agentId] = @{
                Family      = $id
                Fragments   = [string[]]@(if ($agent.ContainsKey('Fragments')) { $agent['Fragments'] })
                DisplayName = if ($agent.ContainsKey('DisplayName')) { [string]$agent['DisplayName'] } else { '' }
            }
            $soul = Join-Path $dir "souls/$agentId.md"
            if (Test-Path -LiteralPath $soul -PathType Leaf) { $soulText[$agentId] = [IO.File]::ReadAllText($soul).Replace("`r", '') }
        }
    }

    $corpus = [System.Text.StringBuilder]::new()
    foreach ($top in @('agents', 'build/agent-src')) {
        $dir = Join-Path $RepoRoot $top
        if (-not (Test-Path -LiteralPath $dir -PathType Container)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $dir -File -Recurse | Where-Object { $_.Extension -in '.md', '.json', '.psd1', '.txt' })) {
            [void]$corpus.Append([IO.File]::ReadAllText($file.FullName).Replace("`r", '')).Append("`n`u{0}`n")
        }
    }

    # Words a fixture must not contain: the family's multi-word display names and hyphenated ids, the runner's
    # name and the tier prefixes.
    $mentions = [System.Collections.Generic.List[string]]::new()
    foreach ($agentId in @($agents.Keys)) {
        if ($agentId.Contains('-')) { $mentions.Add($agentId) }
        $name = $agents[$agentId]['DisplayName']
        if ($name -and $name.Contains(' ')) { $mentions.Add($name) }
    }
    $mentions.Add('Invoke-AgentEvals')
    $mentions.Add('sophon')

    $catalogPath = Join-Path $RepoRoot 'build/agent-src/catalog/sophon-tools.psd1'
    $tools = [string[]]@()
    if (Test-Path -LiteralPath $catalogPath -PathType Leaf) { $tools = [string[]]@((Import-PowerShellDataFile -LiteralPath $catalogPath)['Allowed']) }

    $fixtureInfo = Get-AgentEvalFixtureInfo -EvalRoot $EvalRoot
    @{
        Agents        = $agents
        Methods       = $methods
        DefaultFamily = $default
        FragmentText  = $fragmentText
        SoulText      = $soulText
        Fixtures      = $fixtureInfo['Fixtures']
        Briefs        = $fixtureInfo['Briefs']
        Corpus        = $corpus.ToString()
        Mentions      = $mentions.ToArray()
        Tools         = $tools
        Errors        = $errors.ToArray()
    }
}

# ---------------------------------------------------------------------------------------------
# The scenario lint
# ---------------------------------------------------------------------------------------------

function Get-EvalBriefTask([string]$Text) {
    # The part of a brief after its runtime opening: everything from the first "Task:" line on.
    $at = $Text.IndexOf("`nTask:`n", [StringComparison]::Ordinal)
    if ($at -lt 0) { return $Text }
    return $Text.Substring($at + 1)
}

function Find-EvalLeak {
    <#
    .SYNOPSIS
        The first run of Length characters of Text that also occurs in Corpus, or '' when there is none.
    .DESCRIPTION
        A run of Length characters contains a Length/2 window that starts at a multiple of Length/2, so those
        windows are searched first and only their neighbourhood is checked in full.
    #>
    [CmdletBinding()]
    param([string]$Text, [string]$Corpus, [int]$Length = 40)
    if (-not $Text -or $Text.Length -lt $Length -or -not $Corpus) { return '' }
    $half = [Math]::Max(1, [int][Math]::Floor($Length / 2))
    for ($k = 0; $k + $half -le $Text.Length; $k += $half) {
        if ($Corpus.IndexOf($Text.Substring($k, $half), [StringComparison]::Ordinal) -lt 0) { continue }
        $from = [Math]::Max(0, $k + $half - $Length)
        $to = [Math]::Min($k, $Text.Length - $Length)
        for ($s = $from; $s -le $to; $s++) {
            $run = $Text.Substring($s, $Length)
            if ($Corpus.IndexOf($run, [StringComparison]::Ordinal) -ge 0) { return $run }
        }
    }
    return ''
}

function Test-EvalEventShape($EventList, [string]$Field, [string[]]$Tools) {
    # Yields one message per malformed Pass or Fail entry.
    foreach ($event in @(Get-EvalItems $EventList)) {
        if ($event -isnot [hashtable] -or $event.Count -ne 1) { "$Field entries must be @{ <kind> = <value> } with one kind ($($script:EventKinds.Keys -join ', '))"; continue }
        $kind = [string]@($event.Keys)[0]
        if (-not $script:EventKinds.Contains($kind)) { "$Field has unknown event kind '$kind' (kinds: $($script:EventKinds.Keys -join ', '))"; continue }
        $value = $event[$kind]
        $type = $script:EventKinds[$kind]
        $typeOk = switch ($type) {
            'string' { $value -is [string] -and [bool]$value }
            'bool' { $value -is [bool] }
            'hashtable' { $value -is [hashtable] }
        }
        if (-not $typeOk) { "$Field $kind must be $(@{ string = 'a non-empty string'; bool = '$true or $false'; hashtable = 'a hashtable' }[$type])"; continue }
        $named = switch ($kind) {
            { $_ -in 'FirstTool', 'Tool', 'NoTool' } { @($value) }
            'FirstOf' { @(Get-EvalItems $value['Tools']) + @($value['Is']) }
            'MaxCalls' { @($value['Tool']) }
            default { @() }
        }
        if ($kind -ceq 'FirstOf' -and (@(Get-EvalItems $value['Tools']).Count -lt 2 -or -not ($value['Is'] -is [string]) -or @(Get-EvalItems $value['Tools']) -notcontains $value['Is'])) {
            "$Field FirstOf needs Tools (two or more) and Is (one of them)"
        }
        if ($kind -ceq 'Before') {
            if ($value.Count -ne 2 -or -not ($value['Is'] -is [string] -and $value['Is']) -or -not ($value['Then'] -is [string] -and $value['Then'])) {
                "$Field Before needs Is and Then, two command regexes, and nothing else"
            } else {
                foreach ($k in 'Is', 'Then') { try { [void][regex]::new([string]$value[$k]) } catch { "$Field Before $k '$($value[$k])' is not a valid regex" } }
            }
        }
        if ($kind -ceq 'MaxCalls' -and (-not ($value['Tool'] -is [string]) -or -not ($value['Max'] -is [int]) -or $value['Max'] -lt 0)) {
            "$Field MaxCalls needs Tool and a whole-number Max"
        }
        if ($kind -in 'FirstCommand', 'Says', 'FirstOption') {
            try { [void][regex]::new([string]$value) } catch { "$Field $kind '$value' is not a valid regex" }
        }
        if ($Tools.Count -gt 0) {
            foreach ($tool in @($named | Where-Object { $_ -is [string] })) {
                if (-not (Test-EvalToolName $tool $Tools)) { "$Field $kind names '$tool', which is not a Sophon tool" }
            }
        }
    }
}

function Test-EvalUses {
    # Checks Uses entries against the fragment or role text that must contain them. Returns @{ Missing; Shape }.
    param($Uses, [hashtable]$Context, [string]$Family)
    $missing = [System.Collections.Generic.List[string]]::new()
    $shape = [System.Collections.Generic.List[string]]::new()
    foreach ($use in @(Get-EvalItems $Uses)) {
        if ($use -isnot [hashtable] -or -not ($use['Text'] -is [string]) -or -not $use['Text']) { $shape.Add('Uses entries must be @{ Text; Fragment } or @{ Text; Agent }'); continue }
        $where = @(@('Fragment', 'Agent') | Where-Object { $use.ContainsKey($_) })
        $extra = @(@($use.Keys) | Where-Object { $_ -notin 'Text', 'Fragment', 'Agent', 'Kind', 'Why' })
        if ($where.Count -ne 1 -or $extra.Count -gt 0) { $shape.Add("Uses '$($use['Text'])' names exactly one of Fragment or Agent (other keys: Kind, Why)"); continue }
        if ($where[0] -ceq 'Fragment') {
            $texts = $Context['FragmentText'][$Family]
            $id = [string]$use['Fragment']
            if ($null -eq $texts -or -not $texts.ContainsKey($id)) { $missing.Add("Uses '$($use['Text'])': fragment $id does not exist"); continue }
            if (-not $texts[$id].Contains([string]$use['Text'])) { $missing.Add("Uses '$($use['Text'])': fragment $id does not contain it") }
        } else {
            $id = [string]$use['Agent']
            if (-not $Context['SoulText'].ContainsKey($id)) { $missing.Add("Uses '$($use['Text'])': agent $id has no role text"); continue }
            if (-not $Context['SoulText'][$id].Contains([string]$use['Text'])) { $missing.Add("Uses '$($use['Text'])': the role text of $id does not contain it") }
        }
    }
    @{ Missing = $missing.ToArray(); Shape = $shape.ToArray() }
}

function Test-AgentEvalData {
    <#
    .SYNOPSIS
        The scenario lint: checks the tier data against the repository context.
    .DESCRIPTION
        Data is the Import-AgentEvalData result (or the same shape in memory); Context the Get-AgentEvalContext
        result (or the same shape). Returns @{ Findings; Counts = @{ <tier> = n }; Pending = @{ <milestone> = n };
        Rules = @{ <rule id> = @(<scenario ids>) } }.

        Checks: ids unique across the four files and scenarios.md, with their tier's prefix; the agent is in a
        roster; a pressure row names a registered rule the agent carries, and every registered rule has a
        pressure row (both skipped with a note while the family has no Method key); exactly three known,
        distinct pressures, Control = 'must-fail' and no opt-out phrase in a pressure row; the fixture, its
        patches and the brief exist; every Uses text is in its fragment or role text; no 40-character run of a
        Turns text (or of a brief after its opening) occurs under agents/ or build/agent-src/; no fixture file
        names an agent of a family. A row with Pending = 'M<n>' reports a missing agent, an unregistered or
        uncarried rule and a missing Uses text as notes; with -Release a remaining Pending is an error.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Data,
        [Parameter(Mandatory)][hashtable]$Context,
        [switch]$Release
    )
    $findings = [System.Collections.Generic.List[object]]::new()
    foreach ($f in @($Data['Findings'])) { if ($null -ne $f) { $findings.Add($f) } }
    $counts = [ordered]@{}
    $pendingCounts = @{}
    $ruleRows = @{}
    $seen = @{}
    $rows = [System.Collections.Generic.List[object]]::new()
    $tools = [string[]]@($Context['Tools'])
    $default = [string]$Context['DefaultFamily']

    # Smoke ids: letters then digits, unique among the headings.
    $smokePath = if ($Data.ContainsKey('SmokePath')) { [string]$Data['SmokePath'] } else { 'scenarios.md' }
    foreach ($smoke in @($Data['Smoke'] | Where-Object { $null -ne $_ })) {
        if ($smoke['Id'] -cnotmatch $script:SmokeIdRegex) {
            $findings.Add((New-EvalFinding 'error' 'EVAL-ID' $smokePath $smoke['Line'] "smoke id '$($smoke['Id'])' must be letters followed by digits"))
            continue
        }
        if ($smoke['Kind'] -ceq 'heading') {
            if ($seen.ContainsKey($smoke['Id'])) { $findings.Add((New-EvalFinding 'error' 'EVAL-ID' $smokePath $smoke['Line'] "smoke id $($smoke['Id']) has two sections")) }
            else { $seen[$smoke['Id']] = "${smokePath}:$($smoke['Line'])" }
        }
    }

    # Shared Uses blocks (pressure OptOut, design Markers): @{ Pending; Uses }.
    $optOut = [string[]]@()
    $markers = [string[]]@()
    foreach ($tier in $script:Tiers.Keys) {
        $file = $Data['Files'][$tier]
        if ($null -eq $file) { continue }
        $path = [string]$file['Path']
        $text = [string]$file['Text']
        $top = $file['Data']
        $allowedTop = @('Tier', 'Scenarios') + $(if ($tier -eq 'pressure') { 'OptOut' } elseif ($tier -eq 'design') { 'Markers' } else { @() })
        foreach ($key in @($top.Keys)) {
            if ($key -notin $allowedTop) { $findings.Add((New-EvalFinding 'error' 'EVAL-SHAPE' $path (Get-EvalKeyLine $text $key) "unknown top-level key $key (keys: $($allowedTop -join ', '))")) }
        }
        if (-not ($top['Tier'] -ceq $tier)) { $findings.Add((New-EvalFinding 'error' 'EVAL-SHAPE' $path (Get-EvalKeyLine $text 'Tier') "Tier must be '$tier'")) }
        foreach ($blockKey in @('OptOut', 'Markers')) {
            if (-not $top.ContainsKey($blockKey) -or $blockKey -notin $allowedTop) { continue }
            $block = $top[$blockKey]
            $line = Get-EvalKeyLine $text $blockKey
            if ($block -isnot [hashtable] -or @(Get-EvalItems $block['Uses']).Count -eq 0) { $findings.Add((New-EvalFinding 'error' 'EVAL-SHAPE' $path $line "$blockKey must be @{ Pending; Uses = @(@{ Text; Fragment }) }")); continue }
            $values = [string[]]@(foreach ($use in @(Get-EvalItems $block['Uses'])) { if ($use -is [hashtable]) { [string]$use['Text'] } })
            # An OptOut text keeps its quote marks so that it matches the fragment, but a user types the phrase
            # without them: the turns are searched for the text with one pair of surrounding quotes removed.
            if ($blockKey -eq 'OptOut') { $optOut = [string[]]@(foreach ($v in $values) { if ($v -match '^(["''])(.+)\1$') { $Matches[2] } else { $v } }) }
            else { $markers = $values }
            $pending = if ($block.ContainsKey('Pending')) { [string]$block['Pending'] } else { '' }
            $check = Test-EvalUses -Uses $block['Uses'] -Context $Context -Family $default
            foreach ($m in $check['Shape']) { $findings.Add((New-EvalFinding 'error' 'EVAL-SHAPE' $path $line "${blockKey}: $m")) }
            foreach ($m in $check['Missing']) {
                if ($pending) { $findings.Add((New-EvalFinding 'note' 'EVAL-USES' $path $line "${blockKey} (pending $pending): $m")) }
                else { $findings.Add((New-EvalFinding 'error' 'EVAL-USES' $path $line "${blockKey}: $m")) }
            }
            if ($pending) {
                if ($pending -cnotmatch $script:PendingRegex) { $findings.Add((New-EvalFinding 'error' 'EVAL-PENDING' $path $line "$blockKey Pending '$pending' must be a milestone such as 'M5'")) }
                elseif ($Release) { $findings.Add((New-EvalFinding 'error' 'EVAL-PENDING' $path $line "$blockKey is still Pending $pending")) }
                elseif ($check['Missing'].Count -eq 0) { $findings.Add((New-EvalFinding 'note' 'EVAL-PENDING' $path $line "$blockKey Pending $pending can be deleted: every text is present")) }
                $pendingCounts[$pending] = 1 + [int]$pendingCounts[$pending]
            }
        }

        $counts[$tier] = 0
        foreach ($row in @(Get-EvalItems $top['Scenarios'])) {
            $counts[$tier]++
            $id = if ($row -is [hashtable] -and $row['Id'] -is [string]) { $row['Id'] } else { '' }
            $line = Get-EvalIdLine $text $id
            if ($row -isnot [hashtable]) { $findings.Add((New-EvalFinding 'error' 'EVAL-SHAPE' $path 0 'every scenario must be a hashtable')); continue }
            $rows.Add(@{ Row = $row; Tier = $tier; Path = $path; Line = $line })
            if ($id -cnotmatch "^$($script:Tiers[$tier])-[A-Z0-9]+$") {
                $findings.Add((New-EvalFinding 'error' 'EVAL-ID' $path $line "id '$id' must start with $($script:Tiers[$tier])- followed by capitals or digits"))
            } elseif ($seen.ContainsKey($id)) {
                $findings.Add((New-EvalFinding 'error' 'EVAL-ID' $path $line "id $id is also used at $($seen[$id])"))
            } else {
                $seen[$id] = "${path}:$line"
            }
        }
    }

    $byId = @{}
    foreach ($entry in $rows) { $id = $entry['Row']['Id']; if ($id -is [string] -and -not $byId.ContainsKey($id)) { $byId[$id] = $entry } }

    foreach ($entry in $rows) {
        $row = $entry['Row']; $tier = $entry['Tier']; $path = $entry['Path']; $line = $entry['Line']
        $id = [string]$row['Id']
        $pending = if ($row.ContainsKey('Pending')) { [string]$row['Pending'] } else { '' }
        $deferred = [System.Collections.Generic.List[string]]::new()   # what Pending excuses
        $err = { param([string]$Rule, [string]$Message) $findings.Add((New-EvalFinding 'error' $Rule $path $line "${id}: $Message")) }
        $later = {
            param([string]$Rule, [string]$Message)
            if ($pending) { $deferred.Add($Message); $findings.Add((New-EvalFinding 'note' $Rule $path $line "$id (pending $pending): $Message")) }
            else { $findings.Add((New-EvalFinding 'error' $Rule $path $line "${id}: $Message")) }
        }

        # Keys and types.
        $allowed = $script:CommonKeys + $(if ($tier -eq 'pressure') { $script:PressureKeys } else { @() })
        foreach ($key in @($row.Keys)) {
            if ($key -notin $allowed) { & $err 'EVAL-SHAPE' "unknown key $key$(if ($key -in $script:PressureKeys) { ' (only a pressure scenario has a rule and a control arm)' })" }
        }
        if (-not ($row['Tier'] -ceq $tier)) { & $err 'EVAL-SHAPE' "Tier must be '$tier'" }
        foreach ($key in @('Agent', 'Fixture', 'Read')) {
            if (-not ($row[$key] -is [string]) -or -not $row[$key]) { & $err 'EVAL-SHAPE' "$key must be a non-empty string" }
        }
        $sameRun = if ($row.ContainsKey('SameRunAs')) { [string]$row['SameRunAs'] } else { '' }
        $turns = @(Get-EvalItems $row['Turns'])
        $brief = if ($row.ContainsKey('Brief')) { [string]$row['Brief'] } else { '' }
        if (-not $sameRun -and $turns.Count -eq 0 -and -not $brief) { & $err 'EVAL-SHAPE' 'needs Turns, a Brief or SameRunAs' }
        foreach ($turn in $turns) { if ($turn -isnot [string] -or -not $turn.Trim()) { & $err 'EVAL-SHAPE' 'every Turns entry must be non-empty text' } }
        if (@(Get-EvalItems $row['Pass']).Count -eq 0) { & $err 'EVAL-SHAPE' 'Pass must hold at least one event' }
        if ($tier -in 'acceptance', 'pressure' -and @(Get-EvalItems $row['Fail']).Count -eq 0) { & $err 'EVAL-SHAPE' "Fail must hold at least one event (the forbidden first move)" }
        foreach ($field in @('Pass', 'Fail')) {
            foreach ($m in @(Test-EvalEventShape $row[$field] $field $tools)) { & $err 'EVAL-EVENT' $m }
        }
        $mode = if ($row.ContainsKey('Mode')) { [string]$row['Mode'] } else { 'chat' }
        if ($mode -notin $script:Modes) { & $err 'EVAL-SHAPE' "Mode '$mode' is not one of $($script:Modes -join ', ')" }
        if ($mode -eq 'delegated' -and -not $brief) { & $err 'EVAL-SHAPE' 'a delegated scenario needs a Brief' }
        if ($brief -and $mode -ne 'delegated') { & $err 'EVAL-SHAPE' "a Brief needs Mode = 'delegated'" }
        if ($row.ContainsKey('Skill') -and [string]$row['Skill'] -notin $script:SkillStates) { & $err 'EVAL-SHAPE' "Skill must be one of $($script:SkillStates -join ', ')" }
        if ($row.ContainsKey('Manual') -and $row['Manual'] -isnot [bool]) { & $err 'EVAL-SHAPE' 'Manual must be $true or $false' }

        # Pending.
        if ($pending) {
            if ($pending -cnotmatch $script:PendingRegex) { & $err 'EVAL-PENDING' "Pending '$pending' must be a milestone such as 'M5'" }
            elseif ($Release) { & $err 'EVAL-PENDING' "is still Pending $pending; delete the field in the commit that lands its agent or rule" }
            $pendingCounts[$pending] = 1 + [int]$pendingCounts[$pending]
        }

        # The agent.
        $agentId = [string]$row['Agent']
        $agent = if ($agentId -and $Context['Agents'].ContainsKey($agentId)) { $Context['Agents'][$agentId] } else { $null }
        if ($agentId -and $null -eq $agent) { & $later 'EVAL-AGENT' "agent '$agentId' is in no roster" }
        $family = if ($null -ne $agent) { [string]$agent['Family'] } else { $default }

        # SameRunAs: the other scenario exists, with the same agent and fixture.
        if ($sameRun) {
            if (-not $byId.ContainsKey($sameRun)) { & $err 'EVAL-SHAPE' "SameRunAs '$sameRun' is not a scenario of the four files" }
            else {
                $other = $byId[$sameRun]['Row']
                if (-not ($other['Agent'] -ceq $row['Agent']) -or -not ($other['Fixture'] -ceq $row['Fixture'])) { & $err 'EVAL-SHAPE' "SameRunAs $sameRun has another agent or fixture" }
                if ($other.ContainsKey('SameRunAs')) { & $err 'EVAL-SHAPE' "SameRunAs $sameRun is itself a SameRunAs row" }
            }
        }

        # Fixture, patches and brief.
        $fixture = [string]$row['Fixture']
        if ($fixture -and $fixture -cne 'none') {
            $info = if ($Context['Fixtures'].ContainsKey($fixture)) { $Context['Fixtures'][$fixture] } else { $null }
            if ($null -eq $info) { & $err 'EVAL-FIXTURE' "fixture '$fixture' does not exist under fixtures/" }
            else {
                foreach ($patch in @(Get-EvalItems $row['Setup'])) {
                    if ($patch -isnot [string]) { & $err 'EVAL-SHAPE' 'Setup entries are patch names'; continue }
                    if (-not $info['Patches'].ContainsKey($patch)) { & $err 'EVAL-FIXTURE' "fixture $fixture has no patch '$patch' in its fixture.psd1" }
                    elseif (-not $info['Patches'][$patch]['Exists']) { & $err 'EVAL-FIXTURE' "patch file fixtures/$fixture/patches/$patch.patch is missing" }
                }
            }
        } elseif (@(Get-EvalItems $row['Setup']).Count -gt 0) {
            & $err 'EVAL-FIXTURE' 'Setup needs a fixture'
        }
        if ($brief -and -not $Context['Briefs'].ContainsKey($brief)) { & $err 'EVAL-FIXTURE' "brief fixtures/briefs/$brief does not exist" }

        # Uses.
        $uses = Test-EvalUses -Uses $row['Uses'] -Context $Context -Family $family
        foreach ($m in $uses['Shape']) { & $err 'EVAL-SHAPE' $m }
        foreach ($m in $uses['Missing']) { & $later 'EVAL-USES' $m }

        # Pressure rows: three known pressures, the control arm, no opt-out phrase, a registered rule.
        if ($tier -eq 'pressure') {
            $pressures = @(Get-EvalItems $row['Pressures'])
            $unknown = @($pressures | Where-Object { $_ -isnot [string] -or $_ -notin $script:Pressures })
            if ($pressures.Count -ne 3 -or $unknown.Count -gt 0 -or @($pressures | Select-Object -Unique).Count -ne $pressures.Count) {
                & $err 'EVAL-PRESSURE' "names exactly three distinct pressures from $($script:Pressures -join ', ') (got: $($pressures -join ', '))"
            }
            if (-not ($row['Control'] -ceq 'must-fail')) { & $err 'EVAL-CONTROL' "Control must be 'must-fail' (the same agent composed with -Omit <rule>)" }
            $all = (@($turns) + @(if ($brief -and $Context['Briefs'].ContainsKey($brief)) { $Context['Briefs'][$brief] })) -join "`n"
            foreach ($phrase in $optOut) {
                if ($phrase -and $all.IndexOf($phrase, [StringComparison]::OrdinalIgnoreCase) -ge 0) { & $err 'EVAL-OPTOUT' "contains the opt-out phrase '$phrase', which legitimately switches the rule off" }
            }
            $ruleId = if ($row['Rule'] -is [string]) { [string]$row['Rule'] } else { '' }
            if (-not $ruleId) { & $err 'EVAL-SHAPE' 'Rule must name a Method rule id' }
            else {
                if (-not $ruleRows.ContainsKey($ruleId)) { $ruleRows[$ruleId] = [System.Collections.Generic.List[string]]::new() }
                $ruleRows[$ruleId].Add($id)
                $method = $Context['Methods'][$family]
                if ($null -ne $method -and $null -ne $agent) {
                    $rule = @(@(Get-EvalItems $method['Rules']) | Where-Object { $_ -is [hashtable] -and $_['Id'] -ceq $ruleId }) | Select-Object -First 1
                    if ($null -eq $rule) { & $later 'EVAL-RULE' "rule '$ruleId' is not registered in Method.Rules of family $family" }
                    else {
                        $carried = if ($rule.ContainsKey('Agent')) { $rule['Agent'] -ceq $agentId } else { $agent['Fragments'] -ccontains [string]$rule['Fragment'] }
                        if (-not $carried) { & $later 'EVAL-RULE' "$agentId does not carry rule '$ruleId', so its control arm would equal the treatment" }
                    }
                }
            }
        }

        if ($pending -and $deferred.Count -eq 0 -and -not $Release -and $pending -cmatch $script:PendingRegex) {
            $method = $Context['Methods'][$family]
            # A SameRunAs row is scored from another run, so it stays pending while that run does.
            $runPending = $sameRun -and $byId.ContainsKey($sameRun) -and $byId[$sameRun]['Row'].ContainsKey('Pending')
            if (($tier -ne 'pressure' -or $null -ne $method) -and -not $runPending) {
                $findings.Add((New-EvalFinding 'note' 'EVAL-PENDING' $path $line "$id Pending $pending can be deleted: its agent, rule and Uses texts are all present"))
            }
        }

        # Leaks: no 40-character run of the text sent to the agent occurs in a package or its sources.
        $sent = @($turns | Where-Object { $_ -is [string] })
        if ($brief -and $Context['Briefs'].ContainsKey($brief)) { $sent += Get-EvalBriefTask $Context['Briefs'][$brief] }
        foreach ($text in $sent) {
            $leak = Find-EvalLeak -Text $text -Corpus $Context['Corpus'] -Length $script:LeakRun
            if ($leak) { & $err 'EVAL-LEAK' "the text '$leak' also occurs under agents/ or build/agent-src/" }
        }
    }

    # Coverage: every registered rule has a pressure scenario.
    $pressurePath = if ($Data['Files'].ContainsKey('pressure')) { [string]$Data['Files']['pressure']['Path'] } else { 'pressure.psd1' }
    foreach ($familyId in @($Context['Methods'].Keys | Sort-Object)) {
        $method = $Context['Methods'][$familyId]
        if ($null -eq $method) {
            if ($familyId -ceq $default) { $findings.Add((New-EvalFinding 'note' 'EVAL-COVERAGE' $pressurePath 0 "rules not checked: family $familyId has no Method key yet")) }
            continue
        }
        foreach ($rule in @(Get-EvalItems $method['Rules'])) {
            if ($rule -isnot [hashtable]) { continue }
            if (-not $ruleRows.ContainsKey([string]$rule['Id'])) {
                $findings.Add((New-EvalFinding 'error' 'EVAL-COVERAGE' $pressurePath 0 "registered rule '$($rule['Id'])' of family $familyId has no pressure scenario"))
            }
        }
    }

    # Fixtures name no agent of a family and none of these tests.
    foreach ($name in @($Context['Fixtures'].Keys | Sort-Object)) {
        $info = $Context['Fixtures'][$name]
        if ($info['Error']) { $findings.Add((New-EvalFinding 'error' 'EVAL-FIXTURE' "fixtures/$name" 0 $info['Error'])) }
        if ($info['Base'] -and -not $Context['Fixtures'].ContainsKey($info['Base'])) { $findings.Add((New-EvalFinding 'error' 'EVAL-FIXTURE' "fixtures/$name/fixture.psd1" 0 "Base '$($info['Base'])' is not a fixture")) }
        foreach ($file in @($info['Files'])) {
            foreach ($term in @($Context['Mentions'])) {
                $at = $file['Text'].IndexOf($term, [StringComparison]::OrdinalIgnoreCase)
                if ($at -ge 0) {
                    $lineNo = 1 + ($file['Text'].Substring(0, $at).Split("`n").Count - 1)
                    $findings.Add((New-EvalFinding 'error' 'EVAL-MENTION' "fixtures/$name/$($file['Path'])" $lineNo "names '$term'; a fixture must not mention an agent of the family or these tests"))
                }
            }
            $tierId = [regex]::Match($file['Text'], '\b(?:ACC|PRS|DSN|VOC)-[A-Z0-9]+\b')
            if ($tierId.Success) { $findings.Add((New-EvalFinding 'error' 'EVAL-MENTION' "fixtures/$name/$($file['Path'])" 0 "names the scenario id $($tierId.Value)")) }
        }
    }
    if ($markers.Count -gt 0) { $Context['Markers'] = $markers }

    @{ Findings = $findings.ToArray(); Counts = $counts; Pending = $pendingCounts; Rules = $ruleRows; Markers = $markers }
}

function Format-AgentEvalFinding {
    [CmdletBinding()]
    param([Parameter(Mandatory)][hashtable]$Finding)
    $kind = if ($Finding['Level'] -eq 'error') { 'ERROR' } else { 'NOTE ' }
    "$kind $($Finding['Rule']) $($Finding['Path']):$($Finding['Line']): $($Finding['Message'])"
}

# ---------------------------------------------------------------------------------------------
# Lint fixtures
# ---------------------------------------------------------------------------------------------

function New-AgentEvalTestContext {
    # A small in-memory repository: two agents (dev carries 09b-test-first; lead), one fixture with one patch,
    # one brief, a corpus with one known sentence. Cases override any key.
    @{
        Agents        = @{
            dev  = @{ Family = 'fam'; Fragments = [string[]]@('09b-test-first', '16-reporting'); DisplayName = 'Dev Agent' }
            lead = @{ Family = 'fam'; Fragments = [string[]]@('16-reporting'); DisplayName = 'Lead Agent' }
        }
        Methods       = @{ fam = $null }
        DefaultFamily = 'fam'
        FragmentText  = @{ fam = @{ '09b-test-first' = "## Test first`nWrite the failing test first.`n"; '16-reporting' = "## Reporting`nSay terse to switch.`n"; '07b-discovery' = "## Discovery`nOpt-out: say ""just build it"".`n" } }
        SoulText      = @{ dev = "# Dev`n## Root cause first`n" }
        Fixtures      = @{ 'repo-x' = @{ Dir = ''; Base = ''; Test = ''; Error = ''; Patches = @{ p1 = @{ File = ''; Exists = $true; Commit = ''; Branch = ''; Why = '' }; gone = @{ File = ''; Exists = $false; Commit = ''; Branch = ''; Why = '' } }; Files = @(@{ Path = 'files/README.md'; Text = "A plain project.`n" }) } }
        Briefs        = @{ 'b.md' = "You are a delegated sub-agent working at depth 1 of 3.`n`nTask:`nROLE: dev`n" }
        Corpus        = "Every package says: the quick brown fox jumps over the lazy dog near the river bank today.`n"
        Mentions      = [string[]]@('dev-agent')
        Tools         = [string[]]@('fs.read', 'fs.write', 'fs.edit', 'os.execute', 'info.request', 'agent.delegate', 'canvas.render', 'image.generate')
        Errors        = @()
    }
}

function Invoke-AgentEvalLintFixtures {
    <#
    .SYNOPSIS
        Runs tests/agents/fixtures/evals/cases.psd1 through Test-AgentEvalData.
    .DESCRIPTION
        Each case: @{ Name; Tier; Rows = @(...); Top = @{...}; Smoke = @(...); Context = @{ <key> = <value> }; Release;
        Expect = 'ok' | @{ Level; Rule; Match } }. 'ok' means no error; an Expect table needs a finding of that level
        and rule whose message matches Match. Returns @{ Count; Failures = @(@{ Name; Expect; Got }) }.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$CasesPath)
    $cases = @((Import-PowerShellDataFile -LiteralPath $CasesPath)['Cases'])
    $failures = [System.Collections.Generic.List[object]]::new()
    foreach ($case in $cases) {
        $context = New-AgentEvalTestContext
        if ($case.ContainsKey('Context')) { foreach ($key in @($case['Context'].Keys)) { $context[$key] = $case['Context'][$key] } }
        $tier = if ($case.ContainsKey('Tier')) { [string]$case['Tier'] } else { 'acceptance' }
        $top = @{ Tier = $tier; Scenarios = @($case['Rows']) }
        if ($case.ContainsKey('Top')) { foreach ($key in @($case['Top'].Keys)) { $top[$key] = $case['Top'][$key] } }
        $text = (@(foreach ($row in @($case['Rows'])) { if ($row -is [hashtable] -and $row['Id']) { "    @{ Id = '$($row['Id'])'" } }) -join "`n")
        $data = @{
            Files     = @{ $tier = @{ Path = "$tier.psd1"; Text = $text; Data = $top } }
            Smoke     = @(if ($case.ContainsKey('Smoke')) { $case['Smoke'] })
            SmokePath = 'scenarios.md'
            Findings  = @()
        }
        if ($tier -ne 'pressure') { $data['Files']['pressure'] = @{ Path = 'pressure.psd1'; Text = ''; Data = @{ Tier = 'pressure'; Scenarios = @() } } }
        $result = Test-AgentEvalData -Data $data -Context $context -Release:([bool]$case['Release'])
        $all = @($result['Findings'])
        $errors = @($all | Where-Object { $_['Level'] -eq 'error' })
        $got = (@($all | ForEach-Object { "$($_['Level']) $($_['Rule']): $($_['Message'])" }) -join ' | ')
        $expect = $case['Expect']
        $ok = if ($expect -is [string] -and $expect -eq 'ok') { $errors.Count -eq 0 }
        else {
            @($all | Where-Object { $_['Level'] -eq $expect['Level'] -and $_['Rule'] -ceq $expect['Rule'] -and $_['Message'] -match $expect['Match'] }).Count -gt 0 -and
            ($expect['Level'] -eq 'error' -or $errors.Count -eq 0)
        }
        if (-not $ok) {
            $want = if ($expect -is [string]) { $expect } else { "$($expect['Level']) $($expect['Rule']) /$($expect['Match'])/" }
            $failures.Add(@{ Name = $case['Name']; Expect = $want; Got = $got })
        }
    }
    @{ Count = $cases.Count; Failures = $failures.ToArray() }
}

# ---------------------------------------------------------------------------------------------
# Workspaces and scoring (used by the prepare and live modes; no Gateway here)
# ---------------------------------------------------------------------------------------------

function Invoke-EvalGit([string]$Dir, [string[]]$Arguments) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = @(& git -C $Dir -c core.autocrlf=false -c user.name=eval -c user.email=eval@example.invalid @Arguments 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previous }
    if ($code -ne 0) { throw "git $($Arguments -join ' ') failed in ${Dir}: $($out -join ' / ')" }
    return $out
}

function New-AgentEvalWorkspace {
    <#
    .SYNOPSIS
        Copies a fixture (after its Base) to Destination, makes it a git repository with one commit on main, and
        applies the Setup patches: a patch with Commit is committed (on its Branch when it names one), any other
        patch is left uncommitted.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Fixtures,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Destination,
        [string[]]$Setup = @()
    )
    if (-not $Fixtures.ContainsKey($Name)) { throw "unknown fixture '$Name'" }
    $chain = [System.Collections.Generic.List[hashtable]]::new()
    $current = $Fixtures[$Name]
    while ($null -ne $current) {
        $chain.Insert(0, $current)
        $current = if ($current['Base']) { $Fixtures[$current['Base']] } else { $null }
    }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($item in $chain) {
        $files = Join-Path $item['Dir'] 'files'
        if (Test-Path -LiteralPath $files) { Copy-Item -Path (Join-Path $files '*') -Destination $Destination -Recurse -Force }
    }
    Invoke-EvalGit $Destination @('init', '-q', '-b', 'main') | Out-Null
    Invoke-EvalGit $Destination @('add', '-A') | Out-Null
    Invoke-EvalGit $Destination @('commit', '-q', '-m', 'Initial commit') | Out-Null
    $info = $Fixtures[$Name]
    foreach ($patch in $Setup) {
        $entry = $info['Patches'][$patch]
        if ($null -eq $entry) { throw "fixture $Name has no patch '$patch'" }
        if ($entry['Branch']) { Invoke-EvalGit $Destination @('checkout', '-q', '-b', $entry['Branch']) | Out-Null }
        Invoke-EvalGit $Destination @('apply', '--whitespace=nowarn', $entry['File']) | Out-Null
        if ($entry['Commit']) {
            Invoke-EvalGit $Destination @('add', '-A') | Out-Null
            Invoke-EvalGit $Destination @('commit', '-q', '-m', $entry['Commit']) | Out-Null
        }
    }
    return $Destination
}

function Read-AgentEvalTranscript {
    <#
    .SYNOPSIS
        Parses a `sophon exec --output-format stream-json` transcript (one JSON object per line) into the first
        moves the scorer reads.
    .DESCRIPTION
        Returns @{ Calls = @(@{ Tool; Args; Path; Command; Header; Options; Content; Cut }); Approvals; Text;
        Result }. A call comes from its tool.started line (toolName, argsPreview). argsPreview is parsed as JSON
        when it is complete; the CLI cuts it at 2,048 characters, and a cut preview yields its path, command,
        headers and option labels by pattern (Cut = $true). A path is made relative to -Workspace, or to the
        last '/workspace/' folder in it, with forward slashes. A code.git call's Command is 'git <operation>'.
        A child's call (parentSessionId) is not this agent's move. Checked against live runs in spike 5.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][AllowEmptyCollection()][AllowEmptyString()][string[]]$Lines, [string]$Workspace = '')
    $field = { param([string]$Raw, [string]$Name) $m = [regex]::Match($Raw, '"' + $Name + '"\s*:\s*"((?:[^"\\]|\\.)*)"?'); if ($m.Success) { try { [regex]::Unescape($m.Groups[1].Value) } catch { $m.Groups[1].Value } } else { '' } }
    $root = $Workspace.Replace('\', '/').TrimEnd('/')
    $relative = {
        param([string]$Path)
        if (-not $Path) { return '' }
        $p = $Path.Replace('\', '/')
        if ($root -and $p.StartsWith("$root/", [StringComparison]::OrdinalIgnoreCase)) { $p = $p.Substring($root.Length + 1) }
        else { $i = $p.LastIndexOf('/workspace/', [StringComparison]::OrdinalIgnoreCase); if ($i -ge 0) { $p = $p.Substring($i + 11) } }
        while ($p.StartsWith('./')) { $p = $p.Substring(2) }
        return $p.TrimStart('/')
    }
    $calls = [System.Collections.Generic.List[hashtable]]::new()
    $approvals = 0
    $text = ''
    $result = $null
    $seenCall = @{}
    foreach ($line in $Lines) {
        if (-not $line.Trim()) { continue }
        try { $event = $line | ConvertFrom-Json -AsHashtable -ErrorAction Stop } catch { continue }
        switch ([string]$event['type']) {
            'tool.started' {
                $callId = [string]$event['toolCallId']
                if ($callId -and $seenCall.ContainsKey($callId)) { continue }
                if ($callId) { $seenCall[$callId] = $true }
                if ($event['parentSessionId']) { continue }   # a child's call: not this agent's first move
                $callArgs = @{}
                $preview = [string]$event['argsPreview']
                if ($preview) { try { $callArgs = $preview | ConvertFrom-Json -AsHashtable -ErrorAction Stop } catch { $callArgs = @{ raw = $preview } } }
                $first = if ($callArgs.ContainsKey('questions') -and @($callArgs['questions']).Count -gt 0) { @($callArgs['questions'])[0] } else { $null }
                $tool = [string]$event['toolName']
                $call = @{
                    Tool    = $tool
                    Args    = $callArgs
                    Path    = [string]$(if ($callArgs.ContainsKey('path')) { $callArgs['path'] } elseif ($callArgs.ContainsKey('file_path')) { $callArgs['file_path'] } else { '' })
                    Command = [string]$(if ($callArgs.ContainsKey('command')) { $callArgs['command'] } else { '' })
                    Header  = [string]$(if ($null -ne $first -and $first -is [hashtable] -and $first.ContainsKey('header')) { $first['header'] } else { '' })
                    Headers = [string[]]@(foreach ($q in @($callArgs['questions'])) { if ($q -is [hashtable]) { [string]$q['header'] } })
                    Options = [string[]]@(if ($null -ne $first -and $first -is [hashtable]) { foreach ($o in @($first['options'])) { if ($o -is [hashtable]) { [string]$o['label'] } } })
                    Content = [string]$(if ($callArgs.ContainsKey('content')) { $callArgs['content'] } elseif ($callArgs.ContainsKey('new_string')) { $callArgs['new_string'] } elseif ($callArgs.ContainsKey('raw')) { $callArgs['raw'] } else { '' })
                    Cut     = $callArgs.ContainsKey('raw')
                }
                if ($call['Cut']) {
                    $raw = [string]$callArgs['raw']
                    if (-not $call['Path']) { $call['Path'] = & $field $raw '(?:path|file_path)' }
                    if (-not $call['Command']) { $call['Command'] = & $field $raw 'command' }
                    $heads = [string[]]@([regex]::Matches($raw, '"header"\s*:\s*"((?:[^"\\]|\\.)*)"') | ForEach-Object { [regex]::Unescape($_.Groups[1].Value) })
                    if ($heads.Count -gt 0) { $call['Header'] = $heads[0]; $call['Headers'] = $heads }
                    # Option labels of the first question only: those before a second "header".
                    $firstQ = $raw; $second = [regex]::Matches($raw, '"header"\s*:'); if ($second.Count -gt 1) { $firstQ = $raw.Substring(0, $second[1].Index) }
                    $call['Options'] = [string[]]@([regex]::Matches($firstQ, '"label"\s*:\s*"((?:[^"\\]|\\.)*)"') | ForEach-Object { [regex]::Unescape($_.Groups[1].Value) })
                    if ($tool -ceq 'code.git') { $callArgs['operation'] = & $field $raw 'operation' }
                }
                if ($tool -ceq 'code.git' -and -not $call['Command'] -and $callArgs.ContainsKey('operation') -and $callArgs['operation']) { $call['Command'] = "git $($callArgs['operation'])" }
                $call['Path'] = & $relative $call['Path']
                $calls.Add($call)
            }
            'approval.requested' { $approvals++ }
            'message.completed' { if (-not $event['parentSessionId']) { $text = [string]$event['text'] } }
            'result' { $result = $event; if ($event['text']) { $text = [string]$event['text'] } }
        }
    }
    @{ Calls = $calls.ToArray(); Approvals = $approvals; Text = $text; Result = $result }
}

function Test-AgentEvalEvent {
    # One event against the moves: $true when it holds.
    param([hashtable]$Event, [hashtable]$Moves, [string[]]$Markers = @())
    $kind = [string]@($Event.Keys)[0]
    $value = $Event[$kind]
    $calls = @($Moves['Calls'])
    $match = { param([string]$Tool, [string]$Pattern) if ($Pattern.Contains('*')) { $Tool -like $Pattern } else { $Tool -ceq $Pattern } }
    $writes = @($calls | Where-Object { $_['Tool'] -in $script:WriteTools })
    $questions = @($calls | Where-Object { $_['Tool'] -ceq 'info.request' })
    switch ($kind) {
        'FirstTool' { return ($calls.Count -gt 0 -and (& $match $calls[0]['Tool'] $value)) }
        'FirstWrite' { return ($writes.Count -gt 0 -and (Test-EvalGlob $writes[0]['Path'] $value)) }
        'FirstCommand' {
            $commands = @($calls | Where-Object { $_['Tool'] -in $script:CommandTools })
            return ($commands.Count -gt 0 -and [regex]::IsMatch($commands[0]['Command'], $value))
        }
        'FirstOf' {
            $hit = @($calls | Where-Object { $t = $_['Tool']; @($value['Tools'] | Where-Object { & $match $t $_ }).Count -gt 0 }) | Select-Object -First 1
            return ($null -ne $hit -and (& $match $hit['Tool'] $value['Is']))
        }
        'Before' {
            $texts = @($calls | Where-Object { ($_['Tool'] -in $script:CommandTools -or $_['Tool'] -ceq 'code.git') -and $_['Command'] } | ForEach-Object { [string]$_['Command'] })
            foreach ($t in $texts) {
                if ([regex]::IsMatch($t, $value['Is'])) { return $true }
                if ([regex]::IsMatch($t, $value['Then'])) { return $false }
            }
            return $false
        }
        'Question' { return (@($questions | Where-Object { $_['Headers'] -ccontains $value }).Count -gt 0) }
        'FirstOption' { return ($questions.Count -gt 0 -and $questions[0]['Options'].Count -gt 0 -and [regex]::IsMatch($questions[0]['Options'][0], $value)) }
        'ChatQuestion' { return ((($questions.Count -eq 0) -and ([string]$Moves['Text']).TrimEnd().EndsWith('?')) -eq $value) }
        'Says' { return [regex]::IsMatch([string]$Moves['Text'], $value, 'IgnoreCase') }
        'Tool' { return (@($calls | Where-Object { & $match $_['Tool'] $value }).Count -gt 0) }
        'NoTool' { return (@($calls | Where-Object { & $match $_['Tool'] $value }).Count -eq 0) }
        'NoWrite' { return (@($writes | Where-Object { Test-EvalGlob $_['Path'] $value }).Count -eq 0) }
        'NoMarker' {
            $hit = @($writes | Where-Object { $c = $_['Content']; @($Markers | Where-Object { $c.IndexOf($_, [StringComparison]::OrdinalIgnoreCase) -ge 0 }).Count -gt 0 })
            return (($hit.Count -eq 0) -eq $value)
        }
        'MaxCalls' { return (@($calls | Where-Object { & $match $_['Tool'] $value['Tool'] }).Count -le [int]$value['Max']) }
    }
    throw "unknown event kind $kind"
}

function Get-AgentEvalScore {
    <#
    .SYNOPSIS
        Scores one transcript: it passes when every Pass event holds and no Fail event holds.
    .DESCRIPTION
        Returns @{ Passed; Held = @(<Pass events that held>); Missed = @(<Pass events that did not>);
        Tripped = @(<Fail events that held>) }, each event printed as '<kind>=<value>'.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][hashtable]$Scenario, [Parameter(Mandatory)][hashtable]$Moves, [string[]]$Markers = @())
    $show = { param($e) $k = [string]@($e.Keys)[0]; $v = $e[$k]; if ($v -is [hashtable]) { $v = ($v.GetEnumerator() | Sort-Object Key | ForEach-Object { "$($_.Key)=$($_.Value -join '/')" }) -join ';' }; "$k=$v" }
    $held = [System.Collections.Generic.List[string]]::new()
    $missed = [System.Collections.Generic.List[string]]::new()
    $tripped = [System.Collections.Generic.List[string]]::new()
    foreach ($e in @(Get-EvalItems $Scenario['Pass'])) { if (Test-AgentEvalEvent -Event $e -Moves $Moves -Markers $Markers) { $held.Add((& $show $e)) } else { $missed.Add((& $show $e)) } }
    foreach ($e in @(Get-EvalItems $Scenario['Fail'])) { if (Test-AgentEvalEvent -Event $e -Moves $Moves -Markers $Markers) { $tripped.Add((& $show $e)) } }
    @{ Passed = ($missed.Count -eq 0 -and $tripped.Count -eq 0); Held = $held.ToArray(); Missed = $missed.ToArray(); Tripped = $tripped.ToArray() }
}

function Get-AgentEvalExecArgs {
    <#
    .SYNOPSIS
        The arguments of one 'sophon exec' turn of the runner; the turn itself goes on stdin ('-').
    .DESCRIPTION
        --include-agents puts a delegated child's events in the stream (the scorer still keeps them apart through
        parentSessionId). --allow is never passed, so every card is rejected and every question skipped. The CLI
        sends its current folder as the binding's cwd, so the caller runs this from inside -Workspace.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$AgentId, [Parameter(Mandatory)][string]$Workspace, [int]$TimeoutSeconds = 300, [string]$Session = '', [switch]$Plan)
    $a = @('exec', '--agent', $AgentId, '--workspace', $Workspace, '--trust-workspace', '--include-agents', '--output-format', 'stream-json', '--timeout', "$TimeoutSeconds")
    if ($Plan) { $a += @('--permission-mode', 'plan') }
    if ($Session) { $a += @('--session', $Session) }
    $a += '-'
    return [string[]]$a
}

function Get-AgentEvalPackage {
    <#
    .SYNOPSIS
        The package <AgentId>-<Version>.sophon-agent in -Directory, or an error naming the file that is missing.
    .DESCRIPTION
        The version is the one of agents/<id>/manifest.json, so a 2.1.0 package left in dist/agents is never taken
        for the 3.0.0 one, and 'developer-*' never matches another agent's package.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Directory, [Parameter(Mandatory)][string]$AgentId, [Parameter(Mandatory)][string]$Version)
    $path = Join-Path $Directory "$AgentId-$Version.sophon-agent"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "$Directory has no $AgentId-$Version.sophon-agent: run build/Build-AgentPackages.ps1 first" }
    return [IO.Path]::GetFullPath($path)
}

function Get-AgentEvalPackageSoulHash {
    # The sha256 (lower-case hex) of the SOUL.md inside a package, which is the text the installed agent runs.
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Package)
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($Package)
    try {
        $entry = @($zip.Entries | Where-Object { $_.FullName -ceq 'SOUL.md' }) | Select-Object -First 1
        if ($null -eq $entry) { throw "$Package has no SOUL.md at its root" }
        $stream = $entry.Open()
        try { return [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($stream)).ToLowerInvariant() } finally { $stream.Dispose() }
    } finally { $zip.Dispose() }
}

function Get-AgentEvalRunStatus {
    <#
    .SYNOPSIS
        Reads a turn's result line and exit code: @{ Error; Status; ExitCode; Approvals; Questions }.
    .DESCRIPTION
        Exit 2 with status denied is a normal outcome (a card was rejected or a question skipped; denied counts
        calls). Exit 1, a status of failed, timeout or connection_error, or no result line at all is a run error:
        the row is not scored.
    #>
    [CmdletBinding()]
    param([AllowNull()]$Result, [int]$ExitCode)
    $status = if ($Result -is [hashtable] -and $Result['status']) { [string]$Result['status'] } else { '(no result line)' }
    $denied = if ($Result -is [hashtable] -and $Result['denied'] -is [hashtable]) { $Result['denied'] } else { @{} }
    $isError = ($Result -isnot [hashtable]) -or $ExitCode -eq 1 -or $status -in 'failed', 'timeout', 'connection_error'
    @{
        Error = [bool]$isError; Status = $status; ExitCode = $ExitCode
        Approvals = [int]$(if ($denied.ContainsKey('approvals')) { $denied['approvals'] } else { 0 })
        Questions = [int]$(if ($denied.ContainsKey('questions')) { $denied['questions'] } else { 0 })
    }
}

function Test-AgentEvalGatewayUrl {
    <#
    .SYNOPSIS
        Why a Gateway URL is not a throwaway Gateway for -Run, or '' when it may be used.
    .DESCRIPTION
        The CLI takes its Gateway from SOPHON_GATEWAY_URL or from cli.json (always under the user profile, whatever
        SOPHON_DATA_DIR says), and 'sophon agents install' and 'sophon exec' both talk to that Gateway. So the runner
        needs an explicit URL, and refuses one that is not an absolute http(s) URL, one on the product ports 8080
        or 8470, and the gatewayUrl of cli.json (-CliConfigPath; a missing or unreadable file only skips that
        comparison). localhost, 127.0.0.1 and ::1 count as one host.
    #>
    [CmdletBinding()]
    param([AllowEmptyString()][string]$Url, [string]$CliConfigPath = '')
    $key = {
        param([string]$Text)
        $u = $null
        if (-not [Uri]::TryCreate($Text.Trim(), [UriKind]::Absolute, [ref]$u) -or $u.Scheme -notin 'http', 'https') { return $null }
        $h = $u.Host.ToLowerInvariant().Trim('[', ']')
        if ($h -in 'localhost', '127.0.0.1', '::1') { $h = 'loopback' }
        return @{ Port = $u.Port; Key = "$($u.Scheme)://${h}:$($u.Port)" }
    }
    if (-not $Url -or -not $Url.Trim()) { return 'name the throwaway Gateway with -GatewayUrl or SOPHON_GATEWAY_URL' }
    $target = & $key $Url
    if ($null -eq $target) { return "'$Url' is not an absolute http or https URL" }
    if ($target['Port'] -in 8080, 8470) { return "'$Url' uses port $($target['Port']), the port of a normal Gateway; start the throwaway Gateway on another port" }
    if ($CliConfigPath -and (Test-Path -LiteralPath $CliConfigPath -PathType Leaf)) {
        $configured = ''
        try { $configured = [string]((Get-Content -LiteralPath $CliConfigPath -Raw | ConvertFrom-Json).gatewayUrl) } catch { $configured = '' }
        if ($configured) {
            $real = & $key $configured
            if ($null -ne $real -and $real['Key'] -ceq $target['Key']) { return "'$Url' is the gatewayUrl of $CliConfigPath, the normal Gateway" }
        }
    }
    return ''
}

Export-ModuleMember -Function @(
    'Get-AgentEvalSmokeIds', 'Import-AgentEvalData', 'Get-AgentEvalFixtureInfo', 'Get-AgentEvalContext',
    'Find-EvalLeak', 'Test-AgentEvalData', 'Format-AgentEvalFinding', 'New-AgentEvalTestContext',
    'Invoke-AgentEvalLintFixtures', 'New-AgentEvalWorkspace', 'Read-AgentEvalTranscript', 'Test-AgentEvalEvent',
    'Get-AgentEvalScore', 'Test-EvalGlob', 'Test-AgentEvalGatewayUrl', 'Get-AgentEvalExecArgs', 'Get-AgentEvalPackage',
    'Get-AgentEvalPackageSoulHash', 'Get-AgentEvalRunStatus'
)
