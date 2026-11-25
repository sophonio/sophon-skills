#Requires -Version 7.0

<#
.SYNOPSIS
    Tool-name lint, scanner preflight, TOOLS.md parser and manifest checks for the agent packages in agents/.
.DESCRIPTION
    Data lives in build/agent-src/catalog/sophon-tools.psd1 (tool catalogue) and
    build/agent-src/catalog/scan-rules.psd1 (scanner rules). Every check returns issues of the shape
    [pscustomobject]@{ Rule; Path; Line; Message } with stable rule ids:

      LINT-UNKNOWN LINT-DENIED LINT-RESTRICTED LINT-SKILL LINT-WIRE LINT-CLAUDE LINT-GITOP LINT-HEADING
      SCAN-P1 SCAN-P2 SCAN-P3 SCAN-P4 SCAN-P5 SCAN-P6 SCAN-WORD
      TOOLS-FRONTMATTER TOOLS-GRAMMAR TOOLS-DUP TOOLS-EMPTY TOOLS-BODY TOOLS-PARSE
      TOOLS-PIN-UNKNOWN TOOLS-PIN-DENIED TOOLS-PIN-RESTRICTED TOOLS-PIN-EDIT TOOLS-PIN-CORE TOOLS-PIN-COUNT
      MAN-JSON MAN-FORMAT MAN-KEYS MAN-ORDER MAN-TYPE MAN-NAME MAN-DISPLAY MAN-VERSION MAN-DESC MAN-META
      MAN-TAGS MAN-AGENT MAN-REQUIRES MAN-DEFAULTS MAN-SOPHON

    Family keys read here (build/AgentFamily.psm1 documents them): Category, RequiredTag, Lead, SkillPolicy, the agent
    key Skills and, through the callers, AllowRestrictedMentions. Skill rules are evaluated per agent: an agent's
    Skills list (absent = every SkillPolicy skill, @() = none) decides which skill tools it may name and pin and what
    requires.skills holds. A family with a SkillPolicy may name and pin the tools of its
    skills (LINT-SKILL and TOOLS-PIN-UNKNOWN are waived for those tools only) and lists the skills in
    requires.skills; every other family keeps the single-family rules.

    Pure PowerShell 7, no Sophon CLI and no Windows-only APIs, so it runs in CI on Linux too.
#>

Set-StrictMode -Version Latest

$script:Opt = [System.Text.RegularExpressions.RegexOptions]
$script:CI = $script:Opt::CultureInvariant
$script:CII = $script:Opt::CultureInvariant -bor $script:Opt::IgnoreCase

# Lint patterns (docs/plans/2026-11-15-agents-v2-design.md section 7.3, lint items 1-6). What 3.0 adds to
# sections C, D, F and G (the skill rules, findings at the source line): docs/plans/2026-11-23-agents-v3-design.md, "Static checks".
$script:CandidateRx = [regex]::new('(?<![\w./\\@:-])([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)(?![\w/\\(@-]|\.[A-Za-z0-9_])', $script:CI)
$script:WireRx = [regex]::new('(?<![\w./\\@:-])([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?![\w/\\(@-]|\.[A-Za-z0-9_])', $script:CI)
$script:NegationRx = [regex]::new("\b(?:no|not|never|cannot|can't|can$([char]0x2019)t|does not|doesn't|doesn$([char]0x2019)t|isn't|isn$([char]0x2019)t|instead of|there is no)\b", $script:CII)
$script:HeadingRx = [regex]::new('^(?:## Interaction|## Tool Access|## Workspace|## Memory Knowledge Graph|### Available tool index)', $script:CI)
$script:ClaudePhraseRx = [regex]::new('\bclaude code\b', $script:CII)
# A call-shaped operation value: quoted (operation:"push", "operation": "push") or first in braces
# ({operation: push}). Prose such as "the exact operation: amend" is not a call.
$script:OperationRx = [regex]::new('(?<![\w-])["'']?operation["'']?\s*:\s*["'']([A-Za-z][A-Za-z_-]*)["'']|\{\s*operation\s*:\s*([A-Za-z][A-Za-z_-]*)', $script:CI)
# A tool-call shape "<name> {": sets the context for the operation values that follow, so a single-segment
# tool such as diff {operation:"text_diff"} is not read as code.git.
$script:CallShapeRx = [regex]::new('(?<![\w./\\@:-])([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*)\s*\{', $script:CI)
$script:StashActionRx = [regex]::new('(?<![\w-])stash_action["'']?\s*:\s*["'']?([A-Za-z][A-Za-z_-]*)', $script:CI)
$script:GitProseRx = [regex]::new('(?<![\w./\\@:-])code\.git`?\s+["''`]?([a-z][a-z_-]*)', $script:CI)

$script:ManifestKeyOrder = @(
    'type', 'schemaVersion', 'name', 'displayName', 'version', 'description', 'author', 'license', 'category',
    'tags', 'agent', 'requires', 'defaults', 'sophon'
)

# ---------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------

function New-AgentIssue {
    param([string]$Rule, [string]$Path, [int]$Line, [string]$Message)
    [pscustomobject]@{ Rule = $Rule; Path = $Path; Line = $Line; Message = $Message }
}

function New-StringSet {
    param([object[]]$Items = @())
    $set = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
    foreach ($item in $Items) {
        if ($null -ne $item) { [void]$set.Add([string]$item) }
    }
    return , $set
}

function Test-OrdinalEqual {
    # Exact string equality. -ceq/-cne compare culture-sensitively and ignore zero-width characters
    # (U+FEFF, U+200B, ...), so a planted invisible character would compare equal; this never does.
    param([AllowNull()][object]$Left, [AllowNull()][object]$Right)
    if ($Left -isnot [string] -or $Right -isnot [string]) { return $false }
    [string]::Equals($Left, $Right, [System.StringComparison]::Ordinal)
}

function Get-AgentField {
    # Reads a key from a hashtable or a property from an object; $Default when absent.
    param($Object, [string]$Name, $Default = $null)
    if ($null -eq $Object) { return $Default }
    if ($Object -is [System.Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $Default
    }
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop) { return $prop.Value }
    return $Default
}

function Get-FieldNames {
    param($Object)
    if ($null -eq $Object) { return @() }
    if ($Object -is [System.Collections.IDictionary]) { return @($Object.Keys | ForEach-Object { [string]$_ }) }
    return @($Object.PSObject.Properties | ForEach-Object { $_.Name })
}

function Split-AgentLines {
    # Splits on LF only, so a CR stays visible to the checks that look for it. A final LF does not
    # produce an extra empty line.
    param([AllowEmptyString()][string]$Text)
    if ($Text.Length -eq 0) { return , [string[]]@() }
    $lines = $Text.Split([char]10)
    if ($Text.EndsWith([string][char]10, [System.StringComparison]::Ordinal)) {
        if ($lines.Length -eq 1) { return , [string[]]@() }
        $lines = $lines[0..($lines.Length - 2)]
    }
    return , [string[]]$lines
}

function Get-LineStarts {
    param([AllowEmptyString()][string]$Text)
    $starts = [System.Collections.Generic.List[int]]::new()
    $starts.Add(0)
    for ($i = 0; $i -lt $Text.Length; $i++) {
        if ($Text[$i] -eq [char]10) { $starts.Add($i + 1) }
    }
    return , $starts.ToArray()
}

function Get-LineOfIndex {
    param([int[]]$Starts, [int]$Index)
    $pos = [Array]::BinarySearch($Starts, $Index)
    if ($pos -ge 0) { return $pos + 1 }
    return (-bnot $pos)
}

function Get-CodePointLabel {
    param([string]$Text, [int]$Index)
    $cp = [int]$Text[$Index]
    if ([char]::IsHighSurrogate($Text[$Index]) -and $Index + 1 -lt $Text.Length -and [char]::IsLowSurrogate($Text[$Index + 1])) {
        $cp = [char]::ConvertToUtf32($Text[$Index], $Text[$Index + 1])
    }
    return ('U+{0:X4}' -f $cp)
}

function Expand-AgentFixtureText {
    <#
    .SYNOPSIS
        Expands fixture escapes: {U+XXXX} becomes that code point, {REPEAT:<text>:<n>} becomes <text> n times.
        Lines (an array) are joined with LF. Lets fixtures hold invisible characters and long blobs without
        committing them.
    #>
    param($Case, [string]$Field = 'Text')
    $value = Get-AgentField $Case $Field
    if ($null -eq $value) {
        $lines = Get-AgentField $Case 'Lines'
        if ($Field -eq 'Text' -and $null -ne $lines) { $value = [string]::Join([string][char]10, [string[]]@($lines)) }
        elseif ($Field -eq 'ToolsText') {
            $toolsLines = Get-AgentField $Case 'ToolsLines'
            if ($null -ne $toolsLines) { $value = [string]::Join([string][char]10, [string[]]@($toolsLines)) + [char]10 }
        }
    }
    if ($null -eq $value) { return $null }
    $text = [string]$value
    $text = [regex]::Replace($text, '\{REPEAT:([^:}]+):(\d+)\}', { param($m) $m.Groups[1].Value * [int]$m.Groups[2].Value })
    $text = [regex]::Replace($text, '\{U\+([0-9A-Fa-f]{4,6})\}', { param($m) [char]::ConvertFromUtf32([Convert]::ToInt32($m.Groups[1].Value, 16)) })
    return $text
}

# ---------------------------------------------------------------------------------------------------------------
# Catalogue and scan rules
# ---------------------------------------------------------------------------------------------------------------

function Get-AgentCatalog {
    <#
    .SYNOPSIS
        Loads build/agent-src/catalog/sophon-tools.psd1 and the tool names declared in skills/*/manifest.json.
    .DESCRIPTION
        SkillTools holds every skill tool name; SkillToolOwner maps each one to its skill folder name (the
        first skill, in ordinal folder order, that declares it).
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)

    $root = [IO.Path]::GetFullPath($RepoRoot)
    $file = Join-Path $root 'build/agent-src/catalog/sophon-tools.psd1'
    $data = Import-PowerShellDataFile -LiteralPath $file

    $allowed = New-StringSet $data.Allowed
    $denied = [System.Collections.Generic.Dictionary[string, string]]::new([System.StringComparer]::Ordinal)
    foreach ($key in $data.Denied.Keys) { $denied[[string]$key] = [string]$data.Denied[$key] }

    $restrictedExact = New-StringSet
    $restrictedPrefixes = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in $data.Restricted) {
        if ($entry.EndsWith('.*', [System.StringComparison]::Ordinal)) { $restrictedPrefixes.Add($entry.Substring(0, $entry.Length - 1)) }
        else { [void]$restrictedExact.Add($entry) }
    }

    $skillTools = New-StringSet
    $skillToolOwner = [System.Collections.Generic.Dictionary[string, string]]::new([System.StringComparer]::Ordinal)
    $warnings = [System.Collections.Generic.List[string]]::new()
    $skillsDir = Join-Path $root 'skills'
    if (Test-Path -LiteralPath $skillsDir -PathType Container) {
        foreach ($dir in (Get-ChildItem -LiteralPath $skillsDir -Directory | Sort-Object Name)) {
            $manifestPath = Join-Path $dir.FullName 'manifest.json'
            if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { continue }
            try {
                $json = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
            } catch {
                $warnings.Add("skills/$($dir.Name)/manifest.json: not valid JSON; its tools are not in SkillTools")
                continue
            }
            if ($json -isnot [System.Collections.IDictionary] -or -not $json.Contains('tools')) { continue }
            foreach ($tool in @($json['tools'])) {
                if ($tool -is [System.Collections.IDictionary] -and $tool.Contains('name') -and $tool['name'] -is [string]) {
                    if ($skillTools.Add($tool['name'])) { $skillToolOwner[$tool['name']] = $dir.Name }
                }
            }
        }
    }

    $namespaces = New-StringSet $data.Namespaces
    foreach ($name in @($allowed) + @($denied.Keys) + @($skillTools)) {
        $dot = $name.IndexOf('.')
        if ($dot -gt 0) { [void]$namespaces.Add($name.Substring(0, $dot)) }
    }

    $wire = [System.Collections.Generic.Dictionary[string, string]]::new([System.StringComparer]::Ordinal)
    foreach ($name in $allowed) {
        if ($name.Contains('.')) { $wire[$name.Replace('.', '_')] = $name }
    }

    $profileCore = @{}
    foreach ($key in $data.ProfileCore.Keys) { $profileCore[[string]$key] = New-StringSet $data.ProfileCore[$key] }

    $claudeNames = @($data.ClaudeCodeNames | ForEach-Object { [regex]::Escape($_) }) -join '|'

    [pscustomobject]@{
        SophonCommit       = $data.SophonCommit
        SophonVersion      = $data.SophonVersion
        Allowed            = $allowed
        Denied             = $denied
        RestrictedExact    = $restrictedExact
        RestrictedPrefixes = $restrictedPrefixes.ToArray()
        Restricted         = [string[]]$data.Restricted
        RemovedInV3        = New-StringSet $data.RemovedInV3
        ClaudeCodeNames    = [string[]]$data.ClaudeCodeNames
        ClaudeCodeRx       = [regex]::new('`(?:' + $claudeNames + ')(?:\([^`]*\))?`', $script:CI)
        NotTools           = New-StringSet $data.NotTools
        Namespaces         = $namespaces
        Tlds               = New-StringSet $data.Tlds
        FileExtensions     = New-StringSet $data.FileExtensions
        SkillTools         = $skillTools
        SkillToolOwner     = $skillToolOwner
        Wire               = $wire
        CodeGitOperations  = New-StringSet $data.CodeGitOperations
        StashActions       = New-StringSet $data.StashActions
        GitVerbs           = New-StringSet $data.GitVerbs
        EditTools          = New-StringSet $data.EditTools
        MetaTools          = New-StringSet $data.MetaTools
        ProfileCore        = $profileCore
        ChildProfiles      = New-StringSet $data.ChildProfiles
        Warnings           = $warnings.ToArray()
    }
}

function Get-ScanRules {
    <#
    .SYNOPSIS
        Loads build/agent-src/catalog/scan-rules.psd1 and compiles its regexes.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)

    $root = [IO.Path]::GetFullPath($RepoRoot)
    $d = Import-PowerShellDataFile -LiteralPath (Join-Path $root 'build/agent-src/catalog/scan-rules.psd1')

    $literals = [System.Collections.Generic.List[object]]::new()
    foreach ($tier in 'High', 'Medium', 'Low') {
        foreach ($literal in $d.P2[$tier]) {
            $first = $literal[0]; $last = $literal[$literal.Length - 1]
            $pre = if ([char]::IsLetterOrDigit($first) -or $first -eq '_') { '(?<![\p{L}\p{Nd}_])' } else { '' }
            $post = if ([char]::IsLetterOrDigit($last) -or $last -eq '_') { '(?![\p{L}\p{Nd}_])' } else { '' }
            $literals.Add([pscustomobject]@{
                    Tier    = $tier
                    Literal = $literal
                    Regex   = [regex]::new($pre + [regex]::Escape($literal) + $post, $script:CI)
                })
        }
    }

    $p4 = foreach ($rule in $d.P4) {
        $opts = if ($rule.IgnoreCase) { $script:CII } else { $script:CI }
        $pipe = $rule['PipePattern']
        [pscustomobject]@{
            Id    = $rule.Id
            Regex = [regex]::new($rule.Pattern, $opts)
            Pipe  = if ($pipe) { [regex]::new($pipe, $opts) } else { $null }
        }
    }

    $p3 = foreach ($rule in $d.P3) {
        [pscustomobject]@{ Id = $rule.Id; Regex = [regex]::new($rule.Pattern, $script:CI); Message = $rule.Message }
    }

    $p1Rules = foreach ($rule in $d.P1.Rules) {
        $opts = if ($rule.IgnoreCase) { $script:CII } else { $script:CI }
        [pscustomobject]@{
            Id               = $rule.Id
            Regex            = [regex]::new($rule.Pattern, $opts)
            Group            = [int]$rule.Group
            NameMustBeSecret = [bool]$rule.NameMustBeSecret
        }
    }

    $p6 = foreach ($rule in $d.P6) {
        [pscustomobject]@{ Id = $rule.Id; Regex = [regex]::new($rule.Pattern, $script:CI); Message = $rule.Message }
    }

    $word = foreach ($rule in $d.Word) {
        [pscustomobject]@{ Id = $rule.Id; Regex = [regex]::new($rule.Pattern, $script:CII); Message = $rule.Message }
    }

    [pscustomobject]@{
        P2Literals = $literals.ToArray()
        P4         = @($p4)
        P3         = @($p3)
        P1         = [pscustomobject]@{
            Parts         = [string[]]$d.P1.SensitiveKeyParts
            Suffixes      = [string[]]$d.P1.SensitiveKeySuffixes
            Names         = New-StringSet $d.P1.SensitiveKeyNames
            RedactedValue = [regex]::new($d.P1.RedactedValue, $script:CII)
            Exempt        = @($d.P1.ExemptLines | ForEach-Object { [regex]::new($_, $script:CI) })
            Rules         = @($p1Rules)
        }
        P5         = [pscustomobject]@{
            UrlHost  = [regex]::new($d.P5.UrlHostPattern, $script:CII)
            BareHost = [regex]::new($d.P5.BareHostPattern, $script:CII)
            Loopback = New-StringSet $d.P5.LoopbackHosts
        }
        P6         = @($p6)
        Word       = @($word)
    }
}

# ---------------------------------------------------------------------------------------------------------------
# Tool-name lint
# ---------------------------------------------------------------------------------------------------------------

function Test-RestrictedToolName {
    param([string]$Name, $Catalog)
    if ($Catalog.RestrictedExact.Contains($Name)) { return $true }
    foreach ($prefix in $Catalog.RestrictedPrefixes) {
        if ($Name.StartsWith($prefix, [System.StringComparison]::Ordinal)) { return $true }
    }
    return $false
}

function Get-AgentToolClass {
    <#
    .SYNOPSIS
        Classifies a dotted name: denied, restricted, allowed, skill or unknown.
    #>
    param([string]$Name, $Catalog)
    if ($Catalog.Denied.ContainsKey($Name)) { return 'denied' }
    if (Test-RestrictedToolName $Name $Catalog) { return 'restricted' }
    if ($Catalog.Allowed.Contains($Name)) { return 'allowed' }
    if ($Catalog.SkillTools.Contains($Name)) { return 'skill' }
    return 'unknown'
}

function Get-AgentSkillRoster {
    <#
    .SYNOPSIS
        An agent's optional Skills key: @{ Has; Names }. Has is $false when the agent entry has no Skills key
        (the agent uses every SkillPolicy skill); Names is the listed skill names (empty for Skills = @()).
    #>
    param($Family, [string]$AgentId)
    $entry = $null
    foreach ($agent in @(Get-AgentField $Family 'Agents' @())) {
        if ([string](Get-AgentField $agent 'Id') -ceq $AgentId) { $entry = $agent; break }
    }
    # Read the key without the pipeline: an empty array returned through a function becomes $null.
    $has = $false
    $value = $null
    if ($entry -is [System.Collections.IDictionary]) {
        if ($entry.Contains('Skills')) { $has = $true; $value = $entry['Skills'] }
    } elseif ($null -ne $entry -and $null -ne $entry.PSObject.Properties['Skills']) {
        $has = $true
        $value = $entry.PSObject.Properties['Skills'].Value
    }
    $names = [string[]]@(foreach ($item in @($value)) { if ($item -is [string]) { $item } })
    [pscustomobject]@{ Has = $has; Names = $names }
}

function Get-AgentSkillPolicy {
    <#
    .SYNOPSIS
        A family's SkillPolicy, normalised: @{ Skills (ordinal by Name, each @{ Name; MinVersion }); Names;
        ExtraRequiredTools; Any }. Empty lists when the family has no SkillPolicy.
    .PARAMETER AgentId
        Evaluate the policy for one agent: when its entry has a Skills key, only those skills count (Skills = @()
        means none). Without the key, or without AgentId, every SkillPolicy skill counts. ExtraRequiredTools stay
        family-wide.
    #>
    param($Family, [string]$AgentId = '')
    $policy = Get-AgentField $Family 'SkillPolicy'
    $roster = if ($AgentId) { Get-AgentSkillRoster $Family $AgentId } else { [pscustomobject]@{ Has = $false; Names = [string[]]@() } }
    $skills = [System.Collections.Generic.List[object]]::new()
    foreach ($skill in @(Get-AgentField $policy 'Skills' @())) {
        if ($null -eq $skill) { continue }
        $name = Get-AgentField $skill 'Name'
        if ($name -isnot [string]) { continue }
        if ($roster.Has -and $name -cnotin $roster.Names) { continue }
        $min = Get-AgentField $skill 'MinVersion'
        $skills.Add([pscustomobject]@{ Name = $name; MinVersion = $(if ($min -is [string]) { $min } else { $null }) })
    }
    $ordered = [object[]]$skills.ToArray()
    $names = [string[]]@($ordered | ForEach-Object { $_.Name })
    if ($ordered.Length -gt 1) { [Array]::Sort($names, $ordered, [System.StringComparer]::Ordinal) }
    $extras = [string[]]@(@(Get-AgentField $policy 'ExtraRequiredTools' @()) | Where-Object { $_ -is [string] })
    [pscustomobject]@{
        Skills             = $ordered
        Names              = $names
        ExtraRequiredTools = $extras
        Any                = ($names.Length -gt 0 -or $extras.Length -gt 0)
    }
}

function Get-AgentNegationRegex {
    <#
    .SYNOPSIS
        The tool lint's negation words (no, not, never, cannot, instead of, there is no and their contractions) as
        one case-insensitive regex. METHOD-CONTROLLER (build/AgentFamily.psm1) uses the same list.
    #>
    return $script:NegationRx
}
function Get-AgentAllowedSkillTools {
    <#
    .SYNOPSIS
        The skill tools a family may name and pin: every tool (Catalog.SkillToolOwner) of a SkillPolicy skill,
        in ordinal order. Empty for a family without a SkillPolicy. With AgentId, only the skills that agent
        uses (its Skills key; absent means all).
    #>
    param([Parameter(Mandatory)]$Family, [Parameter(Mandatory)]$Catalog, [string]$AgentId = '')
    $names = New-StringSet (Get-AgentSkillPolicy $Family $AgentId).Names
    $list = [System.Collections.Generic.List[string]]::new()
    foreach ($pair in $Catalog.SkillToolOwner.GetEnumerator()) {
        if ($names.Contains($pair.Value)) { $list.Add($pair.Key) }
    }
    $list.Sort([System.StringComparer]::Ordinal)
    return , [string[]]$list.ToArray()
}

function Invoke-ToolNameLint {
    <#
    .SYNOPSIS
        Checks the tool names in one text (v2 design section 7.3, lint items 1-6).
    .PARAMETER Kind
        soul | tools | readme | manifest. Claude Code names and the phrase are checked in soul and tools only.
    .PARAMETER AllowedSkillTools
        Skill tools this family may name (Get-AgentAllowedSkillTools); LINT-SKILL is waived for them only.
    .PARAMETER AllowRestrictedMentions
        Restricted tool names this family may name un-negated (family AllowRestrictedMentions); LINT-RESTRICTED
        is waived for them only. Pinning them stays forbidden (Test-ToolsMdPins).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][ValidateSet('soul', 'tools', 'readme', 'manifest')][string]$Kind,
        [Parameter(Mandatory)]$Catalog,
        [AllowEmptyCollection()][string[]]$AllowedSkillTools = @(),
        [AllowEmptyCollection()][string[]]$AllowRestrictedMentions = @()
    )

    $issues = [System.Collections.Generic.List[object]]::new()
    $seen = New-StringSet
    $skillOk = New-StringSet $AllowedSkillTools
    $restrictedOk = New-StringSet $AllowRestrictedMentions
    $add = {
        param($rule, $line, $key, $message)
        if ($seen.Add("$rule|$line|$key")) { $issues.Add((New-AgentIssue $rule $Path $line $message)) }
    }

    $lines = Split-AgentLines $Text
    $context = $null
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i].TrimEnd([char]13)
        $n = $i + 1
        $prev = if ($i -gt 0) { $lines[$i - 1] } else { '' }
        $negated = $script:NegationRx.IsMatch($line) -or $script:NegationRx.IsMatch($prev)

        if ($line.Trim().Length -eq 0 -or $line.StartsWith('#', [System.StringComparison]::Ordinal)) { $context = $null }

        if ($script:HeadingRx.IsMatch($line)) {
            & $add 'LINT-HEADING' $n 'heading' "line starts with a heading Sophon appends itself ('$($line.Trim())'); rename it"
        }

        if ($Kind -in 'soul', 'tools') {
            foreach ($m in $Catalog.ClaudeCodeRx.Matches($line)) {
                & $add 'LINT-CLAUDE' $n $m.Value "Claude Code tool name $($m.Value) in agent text; name the Sophon tool instead"
            }
            if ($script:ClaudePhraseRx.IsMatch($line)) {
                & $add 'LINT-CLAUDE' $n 'phrase' 'the phrase "Claude Code" is not allowed in SOUL or TOOLS text'
            }
        }

        # Events in line order: tool mentions set the code.git context for later operation:"..." values.
        $events = [System.Collections.Generic.List[object]]::new()

        foreach ($m in $script:CandidateRx.Matches($line)) {
            $token = $m.Groups[1].Value
            $segments = $token.Split('.')
            $last = $segments[$segments.Length - 1]
            $class = Get-AgentToolClass $token $Catalog
            $listed = $class -in 'denied', 'restricted', 'allowed'
            if (-not $listed -and $Catalog.FileExtensions.Contains($last)) { continue }
            if (-not $listed -and $Catalog.Tlds.Contains($last)) { continue }
            if ($Catalog.NotTools.Contains($token)) { continue }
            if (-not $Catalog.Namespaces.Contains($segments[0])) { continue }

            if ($Catalog.RemovedInV3.Contains($token)) {
                & $add 'LINT-V3' $n $token "$token is removed in Sophon v3 (no alias); do not name it, negated or not"
            }
            switch ($class) {
                'denied' {
                    if (-not $negated) {
                        & $add 'LINT-DENIED' $n $token "$token is not a Sophon tool: $($Catalog.Denied[$token]) (or name it only in a negated statement)"
                    }
                }
                'restricted' {
                    if (-not $negated -and -not $restrictedOk.Contains($token)) {
                        & $add 'LINT-RESTRICTED' $n $token "$token may appear only in a negated statement (no, not, never, cannot, instead of, there is no, ...)"
                    }
                }
                'skill' {
                    if (-not $negated -and -not $skillOk.Contains($token)) {
                        & $add 'LINT-SKILL' $n $token "$token is a marketplace skill tool, not a built-in; agents in this family do not use skill tools"
                    }
                }
                'unknown' {
                    & $add 'LINT-UNKNOWN' $n $token "unknown tool reference $token (not in build/agent-src/catalog/sophon-tools.psd1)"
                }
            }
            if ($class -ne 'unknown') { $events.Add([pscustomobject]@{ Index = $m.Index; Kind = 'tool'; Value = $token }) }
        }

        foreach ($m in $script:WireRx.Matches($line)) {
            $token = $m.Groups[1].Value
            if ($Catalog.Wire.ContainsKey($token)) {
                $dotted = $Catalog.Wire[$token]
                if (-not $line.Contains($dotted)) {
                    & $add 'LINT-WIRE' $n $token "provider wire form $token; write the tool name $dotted"
                }
            } elseif ($Catalog.Denied.ContainsKey($token) -and -not $negated) {
                & $add 'LINT-DENIED' $n $token "$token is not a Sophon tool: $($Catalog.Denied[$token])"
            }
        }

        foreach ($m in $script:CallShapeRx.Matches($line)) {
            $events.Add([pscustomobject]@{ Index = $m.Index; Kind = 'tool'; Value = $m.Groups[1].Value })
        }
        foreach ($m in $script:OperationRx.Matches($line)) {
            $value = if ($m.Groups[1].Success) { $m.Groups[1].Value } else { $m.Groups[2].Value }
            $events.Add([pscustomobject]@{ Index = $m.Index; Kind = 'operation'; Value = $value })
        }
        foreach ($event in ($events | Sort-Object Index, @{ Expression = { if ($_.Kind -eq 'tool') { 0 } else { 1 } } })) {
            if ($event.Kind -eq 'tool') { $context = $event.Value; continue }
            if ($context -ceq 'code.git' -and -not $Catalog.CodeGitOperations.Contains($event.Value)) {
                & $add 'LINT-GITOP' $n "op:$($event.Value)" "code.git has no operation `"$($event.Value)`"; operations: $(@($Catalog.CodeGitOperations) -join ', ')"
            }
        }

        foreach ($m in $script:StashActionRx.Matches($line)) {
            $value = $m.Groups[1].Value
            if (-not $Catalog.StashActions.Contains($value)) {
                & $add 'LINT-GITOP' $n "stash:$value" "code.git stash_action `"$value`" does not exist; use save, pop, list or drop"
            }
        }

        foreach ($m in $script:GitProseRx.Matches($line)) {
            $verb = $m.Groups[1].Value
            if ($Catalog.GitVerbs.Contains($verb) -and -not $Catalog.CodeGitOperations.Contains($verb) -and -not $negated) {
                & $add 'LINT-GITOP' $n "verb:$verb" "code.git has no $verb operation; use os.execute git $verb (or negate the statement)"
            }
        }
    }

    return $issues.ToArray()
}

# ---------------------------------------------------------------------------------------------------------------
# Preflight (scanner replay)
# ---------------------------------------------------------------------------------------------------------------

function Get-KeyWords {
    # Port of ToolArgsRedactor.Words.
    param([string]$Text)
    $words = [System.Collections.Generic.List[string]]::new()
    $current = [System.Text.StringBuilder]::new()
    for ($i = 0; $i -lt $Text.Length; $i++) {
        $c = $Text[$i]
        if (-not [char]::IsLetterOrDigit($c)) {
            if ($current.Length -gt 0) { $words.Add($current.ToString()); [void]$current.Clear() }
            continue
        }
        if ([char]::IsUpper($c) -and $i -gt 0 -and ([char]::IsLower($Text[$i - 1]) -or [char]::IsDigit($Text[$i - 1]))) {
            if ($current.Length -gt 0) { $words.Add($current.ToString()); [void]$current.Clear() }
        }
        [void]$current.Append([char]::ToLowerInvariant($c))
    }
    if ($current.Length -gt 0) { $words.Add($current.ToString()) }
    return , $words.ToArray()
}

function Test-SensitiveKeyName {
    <#
    .SYNOPSIS
        Port of ToolArgsRedactor.IsSensitiveKey.
    #>
    param([string]$Name, $Rules)
    $builder = [System.Text.StringBuilder]::new()
    foreach ($c in $Name.ToCharArray()) {
        if ([char]::IsLetterOrDigit($c)) { [void]$builder.Append([char]::ToLowerInvariant($c)) }
    }
    $normalized = $builder.ToString()
    if ($normalized.Length -eq 0) { return $false }
    foreach ($part in $Rules.P1.Parts) {
        if ($normalized.Contains($part, [System.StringComparison]::Ordinal)) { return $true }
    }
    foreach ($suffix in $Rules.P1.Suffixes) {
        if ($normalized.EndsWith($suffix, [System.StringComparison]::Ordinal)) { return $true }
    }
    if ($Rules.P1.Names.Contains($normalized)) { return $true }
    $words = Get-KeyWords $Name
    return ($words.Length -gt 0 -and $Rules.P1.Names.Contains($words[$words.Length - 1]))
}

function Find-PossibleSecret {
    # One line through the RedactText rules; returns "<rule> <name>" for the first hit, or $null.
    param([string]$Line, $Rules)
    foreach ($rule in $Rules.P1.Rules) {
        $m = $rule.Regex.Match($Line)
        while ($m.Success) {
            $resume = $m.Index + $m.Length
            $hit = $true
            if ($rule.NameMustBeSecret) {
                $name = $m.Groups['name']
                if (-not (Test-SensitiveKeyName $name.Value $Rules)) {
                    $hit = $false
                    $resume = $name.Index + $name.Length
                }
            }
            if ($hit) {
                $secret = $m.Groups[$rule.Group].Value
                if (-not $Rules.P1.RedactedValue.IsMatch($secret)) {
                    $label = if ($rule.NameMustBeSecret) { "$($rule.Id) '$($m.Groups['name'].Value)'" } else { $rule.Id }
                    return $label
                }
            }
            if ($resume -le $m.Index) { $resume = $m.Index + 1 }
            if ($resume -gt $Line.Length) { break }
            $m = $rule.Regex.Match($Line, $resume)
        }
    }
    return $null
}

function Invoke-AgentPreflight {
    <#
    .SYNOPSIS
        Replays the marketplace and runtime scanners over one text (v2 design section 7.3, preflight P1-P6) plus
        the family's wording policy (SCAN-WORD).
    .PARAMETER Rules
        The object from Get-ScanRules.
    .PARAMETER AllowedHosts
        Hosts that URLs and bare host names may use (family.psd1 AllowedHosts).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)]$Rules,
        [Parameter(Mandatory)][AllowEmptyCollection()][string[]]$AllowedHosts,
        [Parameter(Mandatory)][ValidateSet('soul', 'tools', 'readme', 'manifest')][string]$Kind
    )

    $issues = [System.Collections.Generic.List[object]]::new()
    $seen = New-StringSet
    $add = {
        param($rule, $line, $key, $message)
        if ($seen.Add("$rule|$line|$key")) { $issues.Add((New-AgentIssue $rule $Path $line $message)) }
    }
    $hosts =New-StringSet (@($AllowedHosts | ForEach-Object { $_.ToLowerInvariant() }) + @($Rules.P5.Loopback))

    # P2: whole text, as SuspiciousPatterns.Scan normalises it (control characters become spaces).
    $starts = Get-LineStarts $Text
    $normalized = [regex]::Replace($Text, '\p{Cc}', ' ').ToLowerInvariant()
    foreach ($literal in $Rules.P2Literals) {
        if ($literal.Tier -eq 'Low') { continue }
        foreach ($m in $literal.Regex.Matches($normalized)) {
            $line = Get-LineOfIndex $starts $m.Index
            & $add 'SCAN-P2' $line $literal.Literal "$($literal.Tier) injection literal '$($literal.Literal)' (SuspiciousPatterns.cs); rephrase"
        }
    }

    $lines = Split-AgentLines $Text
    $p3Counts = @{}
    $p3First = @{}
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        $n = $i + 1

        # P3: hidden and control characters; per class the first 3 lines are reported, the rest are counted.
        $reported = [System.Collections.Generic.HashSet[int]]::new()
        foreach ($class in $Rules.P3) {
            foreach ($m in $class.Regex.Matches($line)) {
                if ($reported.Add($m.Index)) {
                    $p3Counts[$class.Id] = 1 + [int]$p3Counts[$class.Id]
                    if ($p3Counts[$class.Id] -le 3) {
                        $label = Get-CodePointLabel $line $m.Index
                        & $add 'SCAN-P3' $n "$($class.Id):$label" "$($class.Message): $label at column $($m.Index + 1)"
                    } elseif (-not $p3First.ContainsKey($class.Id)) {
                        $p3First[$class.Id] = $n
                    }
                    break
                }
            }
        }

        # P1: possible_secret, per line.
        $exempt = $false
        if ($Kind -eq 'tools') {
            foreach ($rx in $Rules.P1.Exempt) { if ($rx.IsMatch($line)) { $exempt = $true } }
        }
        if (-not $exempt) {
            $secret = Find-PossibleSecret $line $Rules
            if ($null -ne $secret) {
                & $add 'SCAN-P1' $n 'secret' "reads as a credential to the CLI possible_secret check ($secret); rephrase (e.g. 'Red first -' instead of 'first pass:')"
            }
        }

        # P4: marketplace moderator heuristics.
        foreach ($rule in $Rules.P4) {
            $hit = $false
            if ($null -ne $rule.Pipe) {
                $m = $rule.Regex.Match($line)
                if ($m.Success) { $hit = $rule.Pipe.IsMatch($line.Substring($m.Index + $m.Length)) }
            } else {
                $hit = $rule.Regex.IsMatch($line)
            }
            if ($hit) { & $add 'SCAN-P4' $n $rule.Id "marketplace heuristic '$($rule.Id)' (AgentPromptHeuristics.cs); rephrase" }
        }

        # SCAN-WORD: the family's stricter wording policy.
        foreach ($rule in $Rules.Word) {
            if ($rule.Regex.IsMatch($line)) { & $add 'SCAN-WORD' $n $rule.Id "$($rule.Id): $($rule.Message)" }
        }

        # P5: hosts.
        foreach ($m in $Rules.P5.UrlHost.Matches($line)) {
            $hostName = $m.Groups[1].Value.TrimEnd('.').ToLowerInvariant()
            if ($hostName.Length -gt 0 -and -not $hosts.Contains($hostName)) {
                & $add 'SCAN-P5' $n $hostName "link host '$hostName' is not in AllowedHosts ($(@($AllowedHosts) -join ', '))"
            }
        }
        foreach ($m in $Rules.P5.BareHost.Matches($line)) {
            $hostName = $m.Groups[1].Value.ToLowerInvariant()
            if (-not $hosts.Contains($hostName)) {
                & $add 'SCAN-P5' $n $hostName "host name '$hostName' is not in AllowedHosts ($(@($AllowedHosts) -join ', '))"
            }
        }

        # P6: residue.
        foreach ($rule in $Rules.P6) {
            if ($rule.Regex.IsMatch($line)) { & $add 'SCAN-P6' $n $rule.Id $rule.Message }
        }
    }

    foreach ($class in $Rules.P3) {
        if ($p3First.ContainsKey($class.Id)) {
            $more = [int]$p3Counts[$class.Id] - 3
            & $add 'SCAN-P3' $p3First[$class.Id] "$($class.Id):more" "$($class.Message): $more more line(s) from here on"
        }
    }

    return $issues.ToArray()
}

# ---------------------------------------------------------------------------------------------------------------
# TOOLS.md
# ---------------------------------------------------------------------------------------------------------------

function Get-PinIndent {
    param([string]$Line)
    $n = 0
    while ($n -lt $Line.Length -and ($Line[$n] -eq ' ' -or $Line[$n] -eq "`t")) { $n++ }
    return $n
}

function ConvertTo-CleanPinToken {
    param([string]$Token)
    return $Token.Trim().Trim([char[]]@('"', "'", '`')).Trim()
}

function Split-InlinePinList {
    param([string]$Value)
    $inner = $Value.Trim()
    if ($inner.Length -ge 2 -and $inner[0] -eq '[' -and $inner[$inner.Length - 1] -eq ']') {
        $inner = $inner.Substring(1, $inner.Length - 2)
    }
    $result = [System.Collections.Generic.List[string]]::new()
    foreach ($part in $inner.Split(',', [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $clean = ConvertTo-CleanPinToken $part
        if ($clean.Length -gt 0) { $result.Add($clean) }
    }
    return , $result
}

function Read-PinListValue {
    param([string[]]$Lines, [ref]$Index)
    $i = $Index.Value
    $trimmed = $Lines[$i].Trim()
    $after = $trimmed.Substring($trimmed.IndexOf(':') + 1).Trim()
    $i++
    if ($after.Length -gt 0) {
        $Index.Value = $i
        return , (Split-InlinePinList $after)
    }
    $items = [System.Collections.Generic.List[string]]::new()
    while ($i -lt $Lines.Length) {
        $itemTrimmed = $Lines[$i].TrimStart()
        if (-not $itemTrimmed.StartsWith('-', [System.StringComparison]::Ordinal)) { break }
        $name = ConvertTo-CleanPinToken $itemTrimmed.Substring(1)
        if ($name.Length -gt 0) { $items.Add($name) }
        $i++
    }
    $Index.Value = $i
    return , $items
}

function Get-DedupedPins {
    param($Names)
    $seen = New-StringSet
    $result = [System.Collections.Generic.List[string]]::new()
    foreach ($name in $Names) {
        if ($seen.Add($name)) { $result.Add($name) }
    }
    return , [string[]]$result.ToArray()
}

function Invoke-AgentToolPinsParse {
    <#
    .SYNOPSIS
        Port of AgentToolPins.Parse and FrontmatterParser (sophon a431e1a64,
        src/Sophon.Core/Skills/ToolSelection/AgentToolPins.cs and FrontmatterParser.cs): what the runtime reads.
    #>
    [CmdletBinding()]
    param([AllowNull()][AllowEmptyString()][string]$Text)

    $empty = [pscustomobject]@{ Pins = [string[]]@(); ProfilePins = [ordered]@{} }
    if ([string]::IsNullOrEmpty($Text)) { return $empty }

    # FrontmatterParser.TryExtract
    $all = $Text.Replace("`r`n", "`n").Split([char]10)
    if ($all.Length -eq 0 -or $all[0].Trim() -cne '---') { return $empty }
    $closeAt = -1
    for ($k = 1; $k -lt $all.Length; $k++) {
        if ($all[$k].Trim() -ceq '---') { $closeAt = $k; break }
    }
    if ($closeAt -lt 0) { return $empty }
    $body = if ($closeAt -gt 1) { [string]::Join("`n", $all[1..($closeAt - 1)]) } else { '' }
    if ([string]::IsNullOrEmpty($body)) { return $empty }

    $lines = $body.Replace("`r`n", "`n").Split([char]10)
    $globalPins = [System.Collections.Generic.List[string]]::new()
    $profilePins = $null

    $i = 0
    while ($i -lt $lines.Length) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { $i++; continue }
        if ((Get-PinIndent $line) -eq 0) {
            $trimmed = $line.Trim()
            if ($trimmed.StartsWith('pins:', [System.StringComparison]::Ordinal)) {
                $ref = [ref]$i
                $globalPins.AddRange([string[]](Read-PinListValue $lines $ref))
                $i = $ref.Value
                continue
            }
            if ($trimmed.StartsWith('profiles:', [System.StringComparison]::Ordinal)) {
                $i++
                # ParseProfiles
                while ($i -lt $lines.Length) {
                    $pline = $lines[$i]
                    if ([string]::IsNullOrWhiteSpace($pline)) { $i++; continue }
                    $indent = Get-PinIndent $pline
                    if ($indent -eq 0) { break }
                    $ptrimmed = $pline.Trim()
                    if ($ptrimmed.EndsWith(':', [System.StringComparison]::Ordinal) -and $ptrimmed.Length -gt 1) {
                        $name = $ptrimmed.Substring(0, $ptrimmed.Length - 1).Trim()
                        $nameIndent = $indent
                        $i++
                        # ParseProfileBody
                        $pins = [System.Collections.Generic.List[string]]::new()
                        while ($i -lt $lines.Length) {
                            $bline = $lines[$i]
                            if ([string]::IsNullOrWhiteSpace($bline)) { $i++; continue }
                            if ((Get-PinIndent $bline) -le $nameIndent) { break }
                            $btrimmed = $bline.Trim()
                            if ($btrimmed.StartsWith('pins:', [System.StringComparison]::Ordinal)) {
                                $ref = [ref]$i
                                $pins.AddRange([string[]](Read-PinListValue $lines $ref))
                                $i = $ref.Value
                                continue
                            }
                            $i++
                        }
                        if ($name.Length -gt 0) {
                            if ($null -eq $profilePins) { $profilePins = [ordered]@{} }
                            $profilePins[$name] = Get-DedupedPins $pins
                        }
                        continue
                    }
                    $i++
                }
                continue
            }
        }
        $i++
    }

    if ($globalPins.Count -eq 0 -and $null -eq $profilePins) { return $empty }
    return [pscustomobject]@{
        Pins        = Get-DedupedPins $globalPins
        ProfilePins = if ($null -eq $profilePins) { [ordered]@{} } else { $profilePins }
    }
}

function Read-ToolsMd {
    <#
    .SYNOPSIS
        Strict TOOLS.md parse (block lists only, the line shapes of v2 design section 7.5 G), plus a check that
        the runtime's parser reads the same pins.
    .OUTPUTS
        @{ GlobalPins; Profiles (ordered: profile -> pins); Body; BodyLines; PinLines; Issues }
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text,
        [string]$Path = 'TOOLS.md'
    )

    $issues = [System.Collections.Generic.List[object]]::new()
    $globalPins = [System.Collections.Generic.List[string]]::new()
    $profiles = [ordered]@{}
    $pinLines = @{}
    $result = {
        $bodyLinesValue = if ($null -ne $st.Body) { $st.Body.Length } else { 0 }
        [pscustomobject]@{
            GlobalPins = [string[]]$globalPins.ToArray()
            Profiles   = $profiles
            Body       = if ($null -ne $st.Body) { [string]::Join("`n", [string[]]$st.Body) } else { '' }
            BodyLines  = $bodyLinesValue
            PinLines   = $pinLines
            Issues     = $issues.ToArray()
        }
    }
    $st = @{ State = 'top'; Current = $null; Count = 0; BlockLine = 0; SeenGlobal = $false; SeenProfiles = $false; Body = $null }

    $lines = Split-AgentLines $Text
    if ($lines.Length -eq 0 -or $lines[0] -cne '---') {
        $issues.Add((New-AgentIssue 'TOOLS-FRONTMATTER' $Path 1 'line 1 must be exactly "---" (TOOLS.md starts with its frontmatter)'))
        return (& $result)
    }
    $close = -1
    for ($k = 1; $k -lt $lines.Length; $k++) {
        if ($lines[$k] -ceq '---') { $close = $k; break }
    }
    if ($close -lt 0) {
        $issues.Add((New-AgentIssue 'TOOLS-FRONTMATTER' $Path 1 'the frontmatter has no closing "---" line'))
        return (& $result)
    }

    $closeBlock = {
        switch ($st.State) {
            'globalPins' {
                if ($st.Count -eq 0) { $issues.Add((New-AgentIssue 'TOOLS-EMPTY' $Path $st.BlockLine '"pins:" has no list items')) }
            }
            'profileHead' {
                $issues.Add((New-AgentIssue 'TOOLS-EMPTY' $Path $st.BlockLine "profile '$($st.Current)' has no ""    pins:"" list"))
            }
            'profilePins' {
                if ($st.Count -eq 0) { $issues.Add((New-AgentIssue 'TOOLS-EMPTY' $Path $st.BlockLine "profile '$($st.Current)' pins: has no list items")) }
            }
        }
    }

    for ($k = 1; $k -lt $close; $k++) {
        $line = $lines[$k]
        $n = $k + 1
        if ($line -cmatch '^pins:$') {
            & $closeBlock
            if ($st.SeenGlobal) { $issues.Add((New-AgentIssue 'TOOLS-DUP' $Path $n 'a second top-level "pins:" key')) }
            $st.SeenGlobal = $true; $st.State = 'globalPins'; $st.Count = 0; $st.BlockLine = $n; $st.Current = $null
            continue
        }
        if ($line -cmatch '^profiles:$') {
            & $closeBlock
            if ($st.SeenProfiles) { $issues.Add((New-AgentIssue 'TOOLS-DUP' $Path $n 'a second "profiles:" key')) }
            $st.SeenProfiles = $true; $st.State = 'profiles'; $st.Count = 0; $st.BlockLine = $n; $st.Current = $null
            continue
        }
        if ($line -cmatch '^  - ([a-z][a-z0-9_.]*)$') {
            $pin = $Matches[1]
            if ($st.State -ne 'globalPins') {
                $issues.Add((New-AgentIssue 'TOOLS-GRAMMAR' $Path $n 'a 2-space list item belongs directly under the top-level "pins:"'))
            } elseif ($globalPins.Contains($pin)) {
                $issues.Add((New-AgentIssue 'TOOLS-DUP' $Path $n "duplicate pin $pin"))
            } else {
                $globalPins.Add($pin); $st.Count++; $pinLines["(global)|$pin"] = $n
            }
            continue
        }
        if ($line -cmatch '^  (chat|voice|heartbeat|cron|subagent|graphnode|coding|coding\.subagent|coding\.graphnode):$') {
            $name = $Matches[1]
            if ($st.State -notin 'profiles', 'profileHead', 'profilePins') {
                $issues.Add((New-AgentIssue 'TOOLS-GRAMMAR' $Path $n "profile '$name' belongs under ""profiles:"""))
                continue
            }
            & $closeBlock
            if ($profiles.Contains($name)) {
                $issues.Add((New-AgentIssue 'TOOLS-DUP' $Path $n "profile '$name' is declared twice"))
            } else {
                $profiles[$name] = [System.Collections.Generic.List[string]]::new()
            }
            $st.State = 'profileHead'; $st.Current = $name; $st.Count = 0; $st.BlockLine = $n
            continue
        }
        if ($line -cmatch '^    pins:$') {
            if ($st.State -ne 'profileHead') {
                $issues.Add((New-AgentIssue 'TOOLS-GRAMMAR' $Path $n '"    pins:" belongs directly under a profile line'))
            } else {
                $st.State = 'profilePins'; $st.Count = 0; $st.BlockLine = $n
            }
            continue
        }
        if ($line -cmatch '^      - ([a-z][a-z0-9_.]*)$') {
            $pin = $Matches[1]
            if ($st.State -ne 'profilePins') {
                $issues.Add((New-AgentIssue 'TOOLS-GRAMMAR' $Path $n 'a 6-space list item belongs directly under a profile''s "    pins:"'))
            } else {
                $list = $profiles[$st.Current]
                if ($null -eq $list) { continue }
                if ($list.Contains($pin)) {
                    $issues.Add((New-AgentIssue 'TOOLS-DUP' $Path $n "duplicate pin $pin in profile '$($st.Current)'"))
                } else {
                    $list.Add($pin); $st.Count++; $pinLines["$($st.Current)|$pin"] = $n
                }
            }
            continue
        }
        $why = if ($line.Trim().Length -eq 0) { 'blank lines are not allowed in the frontmatter' }
        elseif ($line -match '\t') { 'tabs are not allowed; indent with spaces' }
        elseif ($line -match '^\s*pins:\s*\S') { 'inline lists are not allowed; write a block list ("  - name" lines)' }
        elseif ($line -match '^\s*[A-Za-z0-9_.-]+:\s*$') { "unknown key or profile '$($line.Trim())' (profiles: chat, voice, heartbeat, cron, subagent, graphnode, coding, coding.subagent, coding.graphnode)" }
        else { 'line does not match the TOOLS.md frontmatter grammar' }
        $issues.Add((New-AgentIssue 'TOOLS-GRAMMAR' $Path $n $why))
    }
    & $closeBlock
    if (-not $st.SeenGlobal -and -not $st.SeenProfiles) {
        $issues.Add((New-AgentIssue 'TOOLS-EMPTY' $Path 1 'the frontmatter declares neither "pins:" nor "profiles:"'))
    } elseif ($st.SeenProfiles -and $profiles.Count -eq 0) {
        $issues.Add((New-AgentIssue 'TOOLS-EMPTY' $Path 1 '"profiles:" declares no profile'))
    }

    # Body: plain text, 1-5 lines.
    if ($close + 1 -le $lines.Length - 1) { $st.Body = [string[]]@($lines[($close + 1)..($lines.Length - 1)]) }
    else { $st.Body = [string[]]@() }
    $bodyText = [string]::Join("`n", [string[]]$st.Body)
    if ($bodyText.Trim().Length -eq 0) {
        $issues.Add((New-AgentIssue 'TOOLS-BODY' $Path ($close + 2) 'the body is empty; add one plain sentence that explains the pins'))
    } elseif ($st.Body.Length -gt 5) {
        $issues.Add((New-AgentIssue 'TOOLS-BODY' $Path ($close + 2) "the body has $($st.Body.Length) lines; at most 5"))
    }
    for ($k = 0; $k -lt $st.Body.Length; $k++) {
        if ($st.Body[$k] -match '^\s*(?:#|[-*+>|]\s|```|\d+[.)]\s)') {
            $issues.Add((New-AgentIssue 'TOOLS-BODY' $Path ($close + 2 + $k) 'the body must be plain text (no headings, lists, quotes, tables or code fences)'))
        }
    }

    # The runtime parser must read exactly what the strict parse reads.
    $port = Invoke-AgentToolPinsParse -Text $Text
    $grammarClean = -not ($issues | Where-Object { $_.Rule -in 'TOOLS-FRONTMATTER', 'TOOLS-GRAMMAR', 'TOOLS-DUP' })
    if ($grammarClean) {
        $strictProfiles = @($profiles.Keys)
        $portProfiles = @($port.ProfilePins.Keys)
        $same = ([string]::Join(',', [string[]]$port.Pins) -ceq [string]::Join(',', [string[]]$globalPins.ToArray())) -and
                ([string]::Join(',', [string[]]$portProfiles) -ceq [string]::Join(',', [string[]]$strictProfiles))
        if ($same) {
            foreach ($name in $strictProfiles) {
                if ([string]::Join(',', [string[]]$port.ProfilePins[$name]) -cne [string]::Join(',', [string[]]$profiles[$name].ToArray())) { $same = $false }
            }
        }
        $portCount = $port.Pins.Length + @($port.ProfilePins.Values | ForEach-Object { $_ }).Count
        if ($portCount -eq 0) {
            $issues.Add((New-AgentIssue 'TOOLS-PARSE' $Path 1 'the runtime parser (AgentToolPins.Parse) reads no pins from this file'))
        } elseif (-not $same) {
            $issues.Add((New-AgentIssue 'TOOLS-PARSE' $Path 1 'the runtime parser (AgentToolPins.Parse) reads different pins than the strict parse'))
        }
    }

    # Freeze profile lists as arrays.
    foreach ($name in @($profiles.Keys)) { $profiles[$name] = [string[]]$profiles[$name].ToArray() }
    return (& $result)
}

function Test-ToolsMdPins {
    <#
    .SYNOPSIS
        Pin semantics for a parsed TOOLS.md: real, not restricted or denied, never an edit tool, core duplicates
        only in child profiles, at most 8 per profile.
    .PARAMETER AllowedSkillTools
        Skill tools this family may pin (Get-AgentAllowedSkillTools); TOOLS-PIN-UNKNOWN is waived for them only.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]$ToolsMd,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)]$Catalog,
        [AllowEmptyCollection()][string[]]$AllowedSkillTools = @()
    )

    $issues = [System.Collections.Generic.List[object]]::new()
    $skillOk = New-StringSet $AllowedSkillTools
    $rootCore = New-StringSet
    foreach ($profile in 'chat', 'voice', 'heartbeat', 'cron', 'coding') {
        foreach ($tool in $Catalog.ProfileCore[$profile]) { [void]$rootCore.Add($tool) }
    }

    $scopes = [System.Collections.Generic.List[object]]::new()
    $scopes.Add([pscustomobject]@{ Name = '(global)'; Pins = [string[]]$ToolsMd.GlobalPins })
    foreach ($name in $ToolsMd.Profiles.Keys) { $scopes.Add([pscustomobject]@{ Name = [string]$name; Pins = [string[]]$ToolsMd.Profiles[$name] }) }

    foreach ($scope in $scopes) {
        $label = if ($scope.Name -eq '(global)') { 'the global pins' } else { "profile '$($scope.Name)'" }
        if ($scope.Pins.Length -gt 8) {
            $first = $ToolsMd.PinLines["$($scope.Name)|$($scope.Pins[0])"]
            $issues.Add((New-AgentIssue 'TOOLS-PIN-COUNT' $Path ([int]$first) "$label has $($scope.Pins.Length) pins; at most 8"))
        }
        foreach ($pin in $scope.Pins) {
            $line = [int]($ToolsMd.PinLines["$($scope.Name)|$pin"])
            if ($Catalog.EditTools.Contains($pin)) {
                $issues.Add((New-AgentIssue 'TOOLS-PIN-EDIT' $Path $line "never pin the edit tool $pin; the Workspace section names the edit tool for the model's provider"))
                continue
            }
            if ($Catalog.Denied.ContainsKey($pin)) {
                $issues.Add((New-AgentIssue 'TOOLS-PIN-DENIED' $Path $line "$pin is not a Sophon tool: $($Catalog.Denied[$pin])"))
                continue
            }
            if (Test-RestrictedToolName $pin $Catalog) {
                $issues.Add((New-AgentIssue 'TOOLS-PIN-RESTRICTED' $Path $line "$pin is restricted and may not be pinned"))
                continue
            }
            if ($Catalog.RemovedInV3.Contains($pin)) {
                $issues.Add((New-AgentIssue 'TOOLS-PIN-V3' $Path $line "$pin is removed in Sophon v3 and may not be pinned"))
                continue
            }
            if (-not $Catalog.Allowed.Contains($pin)) {
                if ($skillOk.Contains($pin)) { continue }
                $issues.Add((New-AgentIssue 'TOOLS-PIN-UNKNOWN' $Path $line "$pin is not a Sophon tool (build/agent-src/catalog/sophon-tools.psd1)"))
                continue
            }
            $isMeta = $Catalog.MetaTools.Contains($pin)
            if ($scope.Name -eq '(global)') {
                if ($isMeta -or $rootCore.Contains($pin)) {
                    $issues.Add((New-AgentIssue 'TOOLS-PIN-CORE' $Path $line "$pin is already a core tool; a global pin of it only makes sense in a child profile"))
                }
            } elseif (-not $Catalog.ChildProfiles.Contains($scope.Name)) {
                $core = $Catalog.ProfileCore[$scope.Name]
                if ($isMeta -or ($null -ne $core -and $core.Contains($pin))) {
                    $issues.Add((New-AgentIssue 'TOOLS-PIN-CORE' $Path $line "$pin is already in the '$($scope.Name)' core; core duplicates belong only in subagent, coding.subagent, graphnode or coding.graphnode"))
                }
            }
        }
    }
    return $issues.ToArray()
}

function Get-ToolsMdPinUnion {
    <#
    .SYNOPSIS
        The ordinal-sorted, de-duplicated union of every pin in a parsed TOOLS.md (what requires.tools must be).
    #>
    param([Parameter(Mandatory)]$ToolsMd)
    $set = New-StringSet $ToolsMd.GlobalPins
    foreach ($name in $ToolsMd.Profiles.Keys) {
        foreach ($pin in $ToolsMd.Profiles[$name]) { [void]$set.Add($pin) }
    }
    $list = [System.Collections.Generic.List[string]]::new($set)
    $list.Sort([System.StringComparer]::Ordinal)
    return , [string[]]$list.ToArray()
}

# ---------------------------------------------------------------------------------------------------------------
# manifest.json
# ---------------------------------------------------------------------------------------------------------------

function Find-JsonKeyLine {
    param([string]$Raw, [string]$Key)
    $lines = Split-AgentLines $Raw
    $needle = '"' + $Key + '"'
    for ($i = 0; $i -lt $lines.Length; $i++) {
        if ($lines[$i].Contains($needle)) { return $i + 1 }
    }
    return 1
}

function Get-AgentFamilyEntry {
    param($Family, [string]$Id)
    foreach ($agent in @(Get-AgentField $Family 'Agents' @())) {
        if ([string](Get-AgentField $agent 'Id') -ceq $Id) { return $agent }
    }
    return $null
}

function Test-AgentRequiresPolicy {
    # requires for a family with a SkillPolicy: keys skills then tools; skills == SkillPolicy.Skills sorted by
    # name; tools == RequiredTools; never a skill tool in tools. Reports through the caller's $Add block.
    param($Requires, $Policy, [string[]]$RequiredTools, $Catalog, [scriptblock]$Add)
    # Read the arrays without the pipeline, which would unroll a one-element array into its element.
    $rawField = {
        param($obj, $name)
        if ($obj -is [System.Collections.IDictionary]) { return , $obj[$name] }
        $prop = $obj.PSObject.Properties[$name]
        if ($null -eq $prop) { return $null }
        return , $prop.Value
    }
    $reqKeys = @(Get-FieldNames $Requires)
    $allowedKeys = @(@('skills', 'tools') | Where-Object { ($_ -ceq 'skills' -and $Policy.Names.Length -gt 0) -or ($_ -ceq 'tools' -and $RequiredTools.Length -gt 0) })
    $holds = if ($allowedKeys.Count -gt 0) { $allowedKeys -join ' then ' } else { 'nothing' }
    foreach ($key in $reqKeys) {
        if ($key -cnotin $allowedKeys) { & $Add 'MAN-REQUIRES' $key "requires.$key is not allowed (requires holds $holds for this family)" }
    }
    foreach ($key in $allowedKeys) {
        if ($key -cnotin $reqKeys) { & $Add 'MAN-REQUIRES' 'requires' "requires.$key is required" }
    }
    $present = [string[]]@($reqKeys | Where-Object { $_ -cin $allowedKeys })
    $canonical = [string[]]@($allowedKeys | Where-Object { $_ -cin $present })
    if (-not (Test-OrdinalEqual ([string]::Join(',', $present)) ([string]::Join(',', $canonical)))) {
        & $Add 'MAN-REQUIRES' 'requires' 'requires keys must be in the order skills, tools'
    }

    if ($reqKeys -ccontains 'skills' -and $Policy.Names.Length -gt 0) {
        $want = [string[]]@(foreach ($skill in $Policy.Skills) {
                if ($null -ne $skill.MinVersion) { '{"name":"' + $skill.Name + '","minVersion":"' + $skill.MinVersion + '"}' }
                else { '{"name":"' + $skill.Name + '"}' }
            })
        $skills = & $rawField $Requires 'skills'
        $got = [System.Collections.Generic.List[string]]::new()
        foreach ($entry in @($skills)) {
            if ($entry -is [System.Management.Automation.PSCustomObject] -or $entry -is [System.Collections.IDictionary]) {
                $pairs = foreach ($k in @(Get-FieldNames $entry)) {
                    $v = Get-AgentField $entry $k
                    '"' + $k + '":' + $(if ($v -is [string]) { '"' + $v + '"' } else { [string]$v })
                }
                $got.Add('{' + (@($pairs) -join ',') + '}')
            }
            else { $got.Add([string]$entry) }
        }
        if ($skills -isnot [System.Array] -or -not (Test-OrdinalEqual ([string]::Join(',', [string[]]$got.ToArray())) ([string]::Join(',', $want)))) {
            & $Add 'MAN-REQUIRES' 'skills' "requires.skills must equal the family SkillPolicy, sorted by name: [$([string]::Join(', ', $want))]"
        }
    }

    if ($reqKeys -ccontains 'tools' -and $RequiredTools.Length -gt 0) {
        $tools = & $rawField $Requires 'tools'
        if ($tools -isnot [System.Array]) { & $Add 'MAN-REQUIRES' 'requires' 'requires.tools must be an array' }
        else {
            if ($null -ne $Catalog) {
                foreach ($tool in $tools) {
                    if ($tool -is [string] -and $Catalog.SkillTools.Contains($tool)) {
                        & $Add 'MAN-REQUIRES' 'requires' "requires.tools lists the skill tool $tool; skill tools never go in requires.tools (requires.skills names the skill)"
                    }
                }
            }
            if (-not (Test-OrdinalEqual ([string]::Join(',', [string[]]@($tools))) ([string]::Join(',', $RequiredTools)))) {
                & $Add 'MAN-REQUIRES' 'requires' "requires.tools must equal the sorted union of the built-in TOOLS.md pins and SkillPolicy.ExtraRequiredTools: [$([string]::Join(', ', $RequiredTools))]"
            }
        }
    }
}

function Test-AgentManifest {
    <#
    .SYNOPSIS
        Manifest rules of the family contract (v2 design section 7.5 F; the skill rules: v3 design, "Static checks").
    .PARAMETER Manifest
        The parsed manifest (ConvertFrom-Json output); $null when Raw did not parse.
    .PARAMETER Raw
        The manifest.json text, for format, key order and line numbers.
    .PARAMETER Family
        family.psd1 data (or Get-AgentFamily output): FamilyMajor, MinSophonVersion, Author, License, Category,
        RequiredTag, Lead, SkillPolicy, Agents[] with Id, DisplayName (MAN-DISPLAY expects it exactly), SubAgents and the
        optional Skills.
    .PARAMETER ToolsMd
        The Read-ToolsMd result for the same agent; $null when TOOLS.md is missing.
    .PARAMETER Catalog
        The Get-AgentCatalog result. A family with a SkillPolicy needs it: it tells skill-tool pins from
        built-in pins and checks ExtraRequiredTools. Without it every pin counts as built-in.
    .DESCRIPTION
        requires: without a SkillPolicy it holds tools only, equal to the sorted union of the TOOLS.md pins, and
        is absent when there are no pins. With a SkillPolicy it holds skills (exactly SkillPolicy.Skills, sorted
        by name, as {"name", "minVersion"}) and then tools (the sorted union of the built-in pins and
        ExtraRequiredTools; never a skill tool).
    #>
    [CmdletBinding()]
    param(
        [AllowNull()]$Manifest,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Raw,
        [Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)]$Family,
        [AllowNull()]$ToolsMd,
        [string]$Path,
        [AllowNull()]$Catalog = $null
    )

    if (-not $Path) { $Path = "agents/$Id/manifest.json" }
    $issues = [System.Collections.Generic.List[object]]::new()
    $add = { param($rule, $key, $message) $issues.Add((New-AgentIssue $rule $Path (Find-JsonKeyLine $Raw $key) $message)) }

    # Format: LF, no tabs, 2-space indentation, one trailing LF.
    if ($Raw.Length -gt 0 -and $Raw[0] -eq [char]0xFEFF) { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path 1 'starts with a BOM')) }
    if ($Raw.Contains("`r")) { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path 1 'contains CR; use LF line endings')) }
    if (-not $Raw.EndsWith("`n") -or $Raw.EndsWith("`n`n")) { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path 1 'must end with exactly one LF')) }
    $rawLines = Split-AgentLines $Raw
    for ($i = 0; $i -lt $rawLines.Length; $i++) {
        $l = $rawLines[$i]
        if ($l.Contains("`t")) { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path ($i + 1) 'contains a tab; indent with 2 spaces')); continue }
        $indent = $l.Length - $l.TrimStart(' ').Length
        if ($indent % 2 -ne 0) { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path ($i + 1) "indentation of $indent spaces; use 2-space steps")) }
        if ($l -match '\s$') { $issues.Add((New-AgentIssue 'MAN-FORMAT' $Path ($i + 1) 'trailing whitespace')) }
    }

    if ($null -eq $Manifest) {
        try { $Manifest = $Raw | ConvertFrom-Json -ErrorAction Stop } catch {
            $issues.Add((New-AgentIssue 'MAN-JSON' $Path 1 "not valid JSON: $($_.Exception.Message)"))
            return $issues.ToArray()
        }
    }
    if ($Manifest -isnot [System.Management.Automation.PSCustomObject] -and $Manifest -isnot [System.Collections.IDictionary]) {
        $issues.Add((New-AgentIssue 'MAN-JSON' $Path 1 'the top level must be a JSON object'))
        return $issues.ToArray()
    }

    $agentEntry = Get-AgentFamilyEntry $Family $Id
    $roster = @(@(Get-AgentField $Family 'Agents' @()) | ForEach-Object { [string](Get-AgentField $_ 'Id') })
    $lead = [string](Get-AgentField $Family 'Lead' 'lead-developer')
    $pins = [string[]]@()
    if ($null -ne $ToolsMd) { $pins = Get-ToolsMdPinUnion $ToolsMd }

    # What requires must hold: the built-in pins plus the family SkillPolicy (skill-tool pins never count).
    # Per agent: an agent's Skills key narrows the policy skills (absent = all, @() = none).
    $policy = Get-AgentSkillPolicy $Family $Id
    $policyTools = New-StringSet
    if ($null -ne $Catalog -and $policy.Any) { $policyTools = New-StringSet (Get-AgentAllowedSkillTools $Family $Catalog $Id) }
    $requiredSet = New-StringSet (@($pins | Where-Object { -not $policyTools.Contains($_) }) + @($policy.ExtraRequiredTools))
    $requiredList = [System.Collections.Generic.List[string]]::new($requiredSet)
    $requiredList.Sort([System.StringComparer]::Ordinal)
    $requiredTools = [string[]]$requiredList.ToArray()
    $needsRequires = $requiredTools.Length -gt 0 -or $policy.Names.Length -gt 0

    # Keys and order.
    $keys = @(Get-FieldNames $Manifest)
    $expected = @($script:ManifestKeyOrder | Where-Object { $_ -ne 'requires' -or $needsRequires })
    foreach ($key in $keys) {
        if ($key -cnotin $script:ManifestKeyOrder) { & $add 'MAN-KEYS' $key "unexpected top-level key '$key' (no icon, no heartbeat, nothing outside the family contract)" }
    }
    foreach ($key in $expected) {
        if ($key -cnotin $keys) { $issues.Add((New-AgentIssue 'MAN-KEYS' $Path 1 "missing top-level key '$key'")) }
    }
    if (-not $needsRequires -and 'requires' -cin $keys) {
        $why = if ($policy.Any) { 'requires must be absent when there are no built-in pins, required skills or extra required tools' } else { 'requires must be absent when TOOLS.md has no pins' }
        & $add 'MAN-REQUIRES' 'requires' $why
    }
    $known = @($keys | Where-Object { $_ -cin $script:ManifestKeyOrder })
    $canonical = @($script:ManifestKeyOrder | Where-Object { $_ -cin $known })
    if (([string]::Join(',', [string[]]$known)) -cne ([string]::Join(',', [string[]]$canonical))) {
        $issues.Add((New-AgentIssue 'MAN-ORDER' $Path 1 "top-level keys must follow the contract order: $([string]::Join(', ', [string[]]$canonical))"))
    }

    $get = { param($obj, $name) Get-AgentField $obj $name }

    # type, schemaVersion, name.
    if (-not (Test-OrdinalEqual (& $get $Manifest 'type') 'agent')) { & $add 'MAN-TYPE' 'type' 'type must be "agent"' }
    $schema = & $get $Manifest 'schemaVersion'
    if (-not (($schema -is [long] -or $schema -is [int]) -and $schema -eq 1)) { & $add 'MAN-TYPE' 'schemaVersion' 'schemaVersion must be the number 1' }
    $name = & $get $Manifest 'name'
    if (-not (Test-OrdinalEqual $name $Id)) { & $add 'MAN-NAME' 'name' "name must equal the folder name '$Id'" }
    if ($name -isnot [string] -or $name -cnotmatch '^[a-z0-9][a-z0-9-]{1,63}$') { & $add 'MAN-NAME' 'name' 'name must match ^[a-z0-9][a-z0-9-]{1,63}$' }

    # displayName.
    $display = & $get $Manifest 'displayName'
    # The roster's DisplayName (a required family key) is the only source of the expected name.
    $expectedDisplay = Get-AgentField $agentEntry 'DisplayName'
    if ($display -isnot [string] -or $display.Trim().Length -eq 0) { & $add 'MAN-DISPLAY' 'displayName' 'displayName is required' }
    else {
        if ($display.Length -gt 64) { & $add 'MAN-DISPLAY' 'displayName' 'displayName must be at most 64 characters' }
        if ($display -match '[\p{Cc}\p{Cf}]') { & $add 'MAN-DISPLAY' 'displayName' 'displayName must not contain control or formatting characters' }
        if ($null -ne $expectedDisplay -and -not (Test-OrdinalEqual $display ([string]$expectedDisplay))) { & $add 'MAN-DISPLAY' 'displayName' "displayName must be '$expectedDisplay'" }
    }

    # version.
    $version = & $get $Manifest 'version'
    $major = [int](Get-AgentField $Family 'FamilyMajor' 2)
    $semver = '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$'
    $versionMatch = if ($version -is [string]) { [regex]::Match($version, $semver) } else { $null }
    if ($null -eq $versionMatch -or -not $versionMatch.Success) { & $add 'MAN-VERSION' 'version' 'version must be SemVer (e.g. 2.0.0)' }
    elseif ([int]$versionMatch.Groups[1].Value -ne $major) { & $add 'MAN-VERSION' 'version' "version major must be the family major $major" }

    # description.
    $description = & $get $Manifest 'description'
    if ($description -isnot [string] -or $description.Trim().Length -eq 0) { & $add 'MAN-DESC' 'description' 'description is required' }
    elseif ($description.Length -gt 600) { & $add 'MAN-DESC' 'description' "description has $($description.Length) characters; at most 600" }
    elseif ($description -match '[\p{Cc}\p{Cf}]') { & $add 'MAN-DESC' 'description' 'description must not contain control or formatting characters' }

    # author, license, category.
    foreach ($pair in @(@('author', 'Author', 'Buildersoft LLC'), @('license', 'License', 'MIT'), @('category', 'Category', 'development'))) {
        $want = [string](Get-AgentField $Family $pair[1] $pair[2])
        if ($pair[0] -cne 'author') { $want = [string](Get-AgentField $agentEntry $pair[1] $want) }
        if (-not (Test-OrdinalEqual (& $get $Manifest $pair[0]) $want)) { & $add 'MAN-META' $pair[0] "$($pair[0]) must be '$want'" }
    }

    # tags.
    $tags = & $get $Manifest 'tags'
    if ($tags -isnot [System.Array]) { & $add 'MAN-TAGS' 'tags' 'tags must be an array' }
    else {
        if ($tags.Length -eq 0 -or $tags.Length -gt 10) { & $add 'MAN-TAGS' 'tags' "tags must hold 1-10 items (has $($tags.Length))" }
        $tagSet = New-StringSet
        foreach ($tag in $tags) {
            if ($tag -isnot [string] -or $tag.Length -gt 32 -or $tag -cnotmatch '^[a-z0-9]+(?:-[a-z0-9]+)*\z') { & $add 'MAN-TAGS' 'tags' "tag '$tag' must be kebab-case, at most 32 characters" }
            elseif (-not $tagSet.Add($tag)) { & $add 'MAN-TAGS' 'tags' "duplicate tag '$tag'" }
        }
        # The agent's RequiredTags override the family RequiredTag.
        $familyTag = [string](Get-AgentField $Family 'RequiredTag' 'development')
        foreach ($required in @(Get-AgentField $agentEntry 'RequiredTags' @($familyTag))) {
            if (-not $tagSet.Contains([string]$required)) { & $add 'MAN-TAGS' 'tags' ('tags must include "{0}"' -f $required) }
        }
    }

    # agent.whenToUse.
    $agent = & $get $Manifest 'agent'
    if ($null -eq $agent -or ($agent -isnot [System.Management.Automation.PSCustomObject] -and $agent -isnot [System.Collections.IDictionary])) { & $add 'MAN-AGENT' 'agent' 'agent must be an object with whenToUse' }
    else {
        $agentKeys = @(Get-FieldNames $agent)
        foreach ($key in $agentKeys) { if ($key -cne 'whenToUse') { & $add 'MAN-AGENT' $key "agent.$key is not allowed (agent holds whenToUse only)" } }
        $when = & $get $agent 'whenToUse'
        if ($when -isnot [string] -or $when.Trim().Length -eq 0) { & $add 'MAN-AGENT' 'whenToUse' 'agent.whenToUse is required' }
        else {
            if ($when.Length -gt 950) { & $add 'MAN-AGENT' 'whenToUse' "agent.whenToUse has $($when.Length) characters; at most 950" }
            if (-not $when.Contains('Not for', [System.StringComparison]::Ordinal)) { & $add 'MAN-AGENT' 'whenToUse' 'agent.whenToUse must contain "Not for"' }
            $siblings = @($roster | Where-Object { $_ -cne $Id -and $when -cmatch ('(?<![\w-])' + [regex]::Escape($_) + '(?![\w-])') })
            if ($roster.Count -gt 1 -and $siblings.Count -eq 0) { & $add 'MAN-AGENT' 'whenToUse' 'agent.whenToUse must name at least one sibling agent id' }
            if (-not $when.EndsWith("Family role: $Id.", [System.StringComparison]::Ordinal)) { & $add 'MAN-AGENT' 'whenToUse' "agent.whenToUse must end with 'Family role: $Id.'" }
            if ($when -match '[\p{Cc}\p{Cf}]') { & $add 'MAN-AGENT' 'whenToUse' 'agent.whenToUse must not contain control or formatting characters' }
        }
    }

    # requires: tools == the sorted union of pins (no SkillPolicy), or the SkillPolicy shape.
    $requires = & $get $Manifest 'requires'
    if ($null -ne $requires -and $policy.Any) {
        Test-AgentRequiresPolicy -Requires $requires -Policy $policy -RequiredTools $requiredTools -Catalog $Catalog -Add $add
    }
    elseif ($null -ne $requires) {
        $reqKeys = @(Get-FieldNames $requires)
        foreach ($key in $reqKeys) { if ($key -cne 'tools') { & $add 'MAN-REQUIRES' $key "requires.$key is not allowed (requires holds tools only)" } }
        # Read the property directly: returning a one-element array through a function unrolls it to a scalar.
        $tools = $null
        if ($requires -is [System.Collections.IDictionary]) { if ($requires.Contains('tools')) { $tools = $requires['tools'] } }
        elseif ($null -ne $requires.PSObject.Properties['tools']) { $tools = $requires.PSObject.Properties['tools'].Value }
        if ($tools -is [System.Collections.IList] -and $tools -isnot [System.Array]) { $tools = [object[]]@($tools) }
        if ($tools -isnot [System.Array]) { & $add 'MAN-REQUIRES' 'requires' 'requires.tools must be an array' }
        elseif (-not (Test-OrdinalEqual ([string]::Join(',', [string[]]@($tools))) ([string]::Join(',', $pins)))) {
            & $add 'MAN-REQUIRES' 'requires' "requires.tools must equal the sorted union of TOOLS.md pins: [$([string]::Join(', ', $pins))]"
        }
    }
    if ($policy.Any -and $null -ne $Catalog) {
        $rootCore = New-StringSet
        foreach ($profile in 'chat', 'voice', 'heartbeat', 'cron', 'coding') {
            foreach ($tool in $Catalog.ProfileCore[$profile]) { [void]$rootCore.Add($tool) }
        }
        foreach ($extra in $policy.ExtraRequiredTools) {
            if (-not $Catalog.Allowed.Contains($extra)) { & $add 'MAN-REQUIRES' 'requires' "SkillPolicy.ExtraRequiredTools entry $extra is not a built-in Sophon tool (build/agent-src/catalog/sophon-tools.psd1)" }
            elseif (Test-RestrictedToolName $extra $Catalog) { & $add 'MAN-REQUIRES' 'requires' "SkillPolicy.ExtraRequiredTools entry $extra is restricted" }
            elseif ($Catalog.RemovedInV3.Contains($extra)) { & $add 'MAN-REQUIRES' 'requires' "SkillPolicy.ExtraRequiredTools entry $extra is removed in Sophon v3" }
            elseif ($rootCore.Contains($extra) -or $Catalog.MetaTools.Contains($extra)) { & $add 'MAN-REQUIRES' 'requires' "SkillPolicy.ExtraRequiredTools entry $extra is a core tool; core tools are always present" }
        }
    }

    # defaults.
    $defaults = & $get $Manifest 'defaults'
    if ($null -eq $defaults) { }
    else {
        foreach ($key in @(Get-FieldNames $defaults)) { if ($key -cnotin 'subAgents', 'modelRouting') { & $add 'MAN-DEFAULTS' $key "defaults.$key is not allowed" } }
        $routing = & $get $defaults 'modelRouting'
        $routingKeys = @(Get-FieldNames $routing)
        if ($null -eq $routing -or $routingKeys.Count -ne 1 -or -not (Test-OrdinalEqual (& $get $routing 'mode') 'inherit')) { & $add 'MAN-DEFAULTS' 'modelRouting' 'defaults.modelRouting must be exactly {"mode":"inherit"}' }
        $sub = & $get $defaults 'subAgents'
        $wantSub = Get-AgentField $agentEntry 'SubAgents'
        $wantEnabled = if ($null -ne $wantSub) { [bool](Get-AgentField $wantSub 'enabled') } else { $Id -ceq $lead }
        $wantDepth = if ($null -ne $wantSub) { [int](Get-AgentField $wantSub 'maxDepth') } elseif ($Id -ceq $lead) { 1 } else { 0 }
        if ($null -eq $sub) { & $add 'MAN-DEFAULTS' 'defaults' 'defaults.subAgents is required' }
        else {
            $subKeys = @(Get-FieldNames $sub)
            $enabled = & $get $sub 'enabled'
            $depth = & $get $sub 'maxDepth'
            $okShape = $subKeys.Count -eq 2 -and $enabled -is [bool] -and ($depth -is [long] -or $depth -is [int])
            if (-not $okShape -or $enabled -ne $wantEnabled -or $depth -ne $wantDepth) {
                & $add 'MAN-DEFAULTS' 'subAgents' "defaults.subAgents must be {""enabled"": $($wantEnabled.ToString().ToLowerInvariant()), ""maxDepth"": $wantDepth}"
            }
        }
    }

    # sophon.minVersion.
    $sophon = & $get $Manifest 'sophon'
    $minVersion = [string](Get-AgentField $Family 'MinSophonVersion' '2.2.0')
    if ($null -ne $sophon) {
        foreach ($key in @(Get-FieldNames $sophon)) { if ($key -cne 'minVersion') { & $add 'MAN-SOPHON' $key "sophon.$key is not allowed" } }
        if (-not (Test-OrdinalEqual (& $get $sophon 'minVersion') $minVersion)) { & $add 'MAN-SOPHON' 'minVersion' "sophon.minVersion must be '$minVersion'" }
    }

    return $issues.ToArray()
}

# ---------------------------------------------------------------------------------------------------------------
# Fixture runner
# ---------------------------------------------------------------------------------------------------------------

function Get-AgentLintTestFamily {
    <#
    .SYNOPSIS
        The family contract as data, for fixtures that must not depend on build/agent-src/family.psd1.
    #>
    # The fixture family carries its own display names, so no name lives in code outside it.
    $names = [ordered]@{
        'code-reviewer'      = 'Code Reviewer'
        'debugger'           = 'Debugger'
        'developer'          = 'Developer'
        'lead-developer'     = 'Lead Developer'
        'qa-engineer'        = 'QA Engineer'
        'researcher'         = 'Researcher'
        'security-reviewer'  = 'Security Reviewer'
        'software-architect' = 'Software Architect'
        'ui-ux-designer'     = 'UI/UX Designer'
    }
    $agents = foreach ($id in $names.Keys) {
        $lead = $id -ceq 'lead-developer'
        @{ Id = $id; DisplayName = $names[$id]; SubAgents = @{ enabled = $lead; maxDepth = $(if ($lead) { 1 } else { 0 }) } }
    }
    # One agent with its own license, for the per-agent License override.
    $agents = @($agents) + @(@{ Id = 'frontend-developer'; DisplayName = 'Frontend Developer'; License = 'Apache-2.0'; SubAgents = @{ enabled = $false; maxDepth = 0 } })
    @{
        FamilyMajor      = 2
        MinSophonVersion = '2.2.0'
        Author           = 'Buildersoft LLC'
        License          = 'MIT'
        Category         = 'development'
        Lead             = 'lead-developer'
        Values           = @{
            CommitTrailer = 'Co-Authored-By: Sophon <noreply@buildersoft.io>'
            PrFooter      = ([char]::ConvertFromUtf32(0x1F916) + ' Generated with [Sophon](https://sophon.buildersoft.io)')
            PlanDir       = 'docs/plans'
        }
        AllowedHosts     = @('sophon.buildersoft.io', 'marketplace.sophon.buildersoft.io', 'github.com')
        Agents           = @($agents)
    }
}

function Invoke-AgentLintFixtures {
    <#
    .SYNOPSIS
        Runs tests/agents/fixtures/{lint,scan,toolsmd,manifest}/cases.psd1 and returns every case that did not
        behave as its Expect says (empty when all pass). A 'fail' case passes when at least one issue carries
        its Rule (or any issue when Rule is empty); a 'pass' case passes when there are no issues.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)

    $root = [IO.Path]::GetFullPath($RepoRoot)
    $catalog = Get-AgentCatalog -RepoRoot $root
    $rules = Get-ScanRules -RepoRoot $root
    $family = Get-AgentLintTestFamily
    $hosts = [string[]]$family.AllowedHosts
    $failures = [System.Collections.Generic.List[object]]::new()
    $total = 0

    foreach ($suite in 'lint', 'scan', 'toolsmd', 'manifest') {
        $file = Join-Path $root "tests/agents/fixtures/$suite/cases.psd1"
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            $failures.Add([pscustomobject]@{ Suite = $suite; Name = '(file)'; Expect = 'present'; Rule = ''; Got = 'missing'; Detail = $file })
            continue
        }
        $data = Import-PowerShellDataFile -LiteralPath $file
        foreach ($case in $data.Cases) {
            $total++
            $name = [string]$case.Name
            $kind = [string](Get-AgentField $case 'Kind' 'soul')
            $issues = @()
            try {
                switch ($suite) {
                    'lint' {
                        $text = Expand-AgentFixtureText $case
                        $issues = @(Invoke-ToolNameLint -Text $text -Path "fixture:$name" -Kind $kind -Catalog $catalog)
                    }
                    'scan' {
                        $text = Expand-AgentFixtureText $case
                        $issues = @(Invoke-AgentPreflight -Text $text -Path "fixture:$name" -Rules $rules -AllowedHosts $hosts -Kind $kind)
                    }
                    'toolsmd' {
                        $text = Expand-AgentFixtureText $case
                        $parsed = Read-ToolsMd -Text $text -Path "fixture:$name"
                        $issues = @($parsed.Issues) + @(Test-ToolsMdPins -ToolsMd $parsed -Path "fixture:$name" -Catalog $catalog)
                    }
                    'manifest' {
                        $raw = Expand-AgentFixtureText $case 'Json'
                        if ($null -eq $raw) {
                            $raw = [string]$data.Base
                            foreach ($pair in @(Get-AgentField $case 'Replace' @())) {
                                $target = Expand-AgentFixtureText @{ Text = [string]$pair[0] }
                                if (-not $raw.Contains($target)) { throw "Replace target not found: $($pair[0])" }
                                $raw = $raw.Replace($target, (Expand-AgentFixtureText @{ Text = [string]$pair[1] }))
                            }
                        }
                        $toolsText = Expand-AgentFixtureText $case 'ToolsText'
                        if ($null -eq $toolsText) { $toolsText = [string]$data.BaseTools }
                        $tools = Read-ToolsMd -Text $toolsText -Path "fixture:$name/TOOLS.md"
                        $id = [string](Get-AgentField $case 'Id' 'lead-developer')
                        $parsedManifest = $null
                        try { $parsedManifest = $raw | ConvertFrom-Json -ErrorAction Stop } catch { $parsedManifest = $null }
                        $issues = @(Test-AgentManifest -Manifest $parsedManifest -Raw $raw -Id $id -Family $family -ToolsMd $tools -Path "fixture:$name" -Catalog $catalog)
                    }
                }
            } catch {
                $failures.Add([pscustomobject]@{ Suite = $suite; Name = $name; Expect = $case.Expect; Rule = $case.Rule; Got = 'exception'; Detail = $_.Exception.Message })
                continue
            }

            $got = @($issues | ForEach-Object { $_.Rule } | Select-Object -Unique)
            $wantRule = [string](Get-AgentField $case 'Rule' '')
            $ok = if ($case.Expect -eq 'pass') { $issues.Count -eq 0 }
            elseif ($wantRule) { $got -contains $wantRule }
            else { $issues.Count -gt 0 }
            if (-not $ok) {
                $detail = @($issues | Select-Object -First 4 | ForEach-Object { "$($_.Rule) L$($_.Line): $($_.Message)" }) -join ' | '
                $failures.Add([pscustomobject]@{ Suite = $suite; Name = $name; Expect = $case.Expect; Rule = $wantRule; Got = ($got -join ','); Detail = $detail })
            }
        }
    }

    Write-Verbose "Invoke-AgentLintFixtures: $total case(s), $($failures.Count) failure(s)"
    return $failures.ToArray()
}

Export-ModuleMember -Function @(
    'Get-AgentCatalog', 'Get-ScanRules', 'Get-AgentToolClass', 'Invoke-ToolNameLint', 'Invoke-AgentPreflight',
    'Read-ToolsMd', 'Invoke-AgentToolPinsParse', 'Test-ToolsMdPins', 'Get-ToolsMdPinUnion', 'Test-AgentManifest',
    'Get-AgentSkillPolicy', 'Get-AgentSkillRoster', 'Get-AgentAllowedSkillTools', 'Get-AgentNegationRegex',
    'Test-SensitiveKeyName', 'Get-AgentField', 'Get-AgentLintTestFamily', 'Expand-AgentFixtureText',
    'Invoke-AgentLintFixtures'
)
