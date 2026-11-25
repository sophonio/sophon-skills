#Requires -Version 7.0
<#
.SYNOPSIS
    Roster loading and SOUL composition for the Buildersoft agent families (agents/<id>/).
.DESCRIPTION
    Families are listed in build/agent-src/families.psd1:
      @{ Families = @( @{ Id = 'development'; Path = 'build/agent-src/family.psd1' }, ... ) }
    Each family's sources live in the folder of its family file (<dir>):
      <dir>/family.psd1                 roster, per-agent fragment order, caps and Values
      <dir>/souls/<id>.md               agent template: role text plus include lines
      <dir>/fragments/soul/<NN-id>.md   that family's shared fragments
      <dir>/readmes/<id>.md             optional: README source (when the folder exists, every agents/<id>/README.md
                                        of the family is generated, after the SOULs)
      <dir>/fragments/readme/<NN-id>.md shared README blocks, included with {{> readme/<NN-id>}}
    Without a registry the single legacy family build/agent-src/family.psd1 applies. Every path
    function below works on the current family context, which Set-AgentFamilyContext selects;
    importing the module selects the legacy paths. An agent id may belong to one family only
    (Get-AgentRosterUnion), and agents/ holds the folders of every family.

    Optional family keys (absent = the development family's behaviour; checked by Test-AgentFamilyData):
      Id                       equals the registry Id
      RequiredTag              tag every manifest must carry (default 'development')
      Category                 manifest category (default 'development')
      CreditsSentence          verbatim sentence every README must carry (absent or '' = no sentence check)
      CreditsSentenceKeys      the Credits keys CreditsSentence speaks for: only an agent carrying one of them must
                               carry the sentence (absent = every agent with Credits)
      ReadmeCaps               @{ Lead = <bytes>; Other = <bytes> } (default 24576 / 12288)
      SkillPolicy              @{ Skills = @(@{ Name; MinVersion }); ExtraRequiredTools = @('<tool>') }:
                               the marketplace skills the agents require (requires.skills) and the built-in
                               tools required beyond the TOOLS.md pins; tools of these skills may be named
                               and pinned
      AllowRestrictedMentions  restricted tool names that may be named un-negated (never pinned)
                               A SkillPolicy skill may also name Fragment = '<NN-id>', its reference fragment: the
                               only source whose lines may name that skill's tools (METHOD-REFERENCE), which an
                               agent includes exactly when it uses the skill (LINT-SKILL-FRAGMENT); and TopicIndex =
                               '<repo path>', the JSON id list its topic pointers are checked against (LINT-TOPIC,
                               with the topics.lock.json beside it for section ids). A policy skill no agent uses
                               fails LINT-SKILL-UNUSED (Test-AgentSkillUse)
      RosterOrder              the agent ids of the README roster table, in table order (DOC-COUNT derives the
                               table and companion counts from it)
      Method                   the registry of tested rules: @{ Controller = @{ Fragments; Terms; Allow };
                               Worker = @{ Fragments; Exempt }; Rules = @(@{ Id; Fragment | Agent; Anchor }) }
                               (METHOD-CONTROLLER, METHOD-EXCUSES; Test-AgentMethod)
      FragmentCaps             @{ '<NN-id>' = <bytes> }: a lower size limit for that fragment than the 4,096 B
                               every fragment has (BUDGET-FRAGMENT); a key must name an existing fragment

    Optional agent keys (beside the required Id, DisplayName, SoulCap, Writer, SubAgents, Effort, Fragments, Credits):
      License, Category, RequiredTags   per-agent overrides of the family values
      Skills                   the SkillPolicy skills this agent uses (absent = all, @() = none); MAN-REQUIRES,
                               LINT-SKILL and TOOLS-PIN-UNKNOWN are evaluated per agent
      Summary, Changes, Commits the agent's roster-table cells (Role, Changes files, Commits) for {{# roster}}
      RoleCap                  the most bytes the role text may take (souls/<id>.md without include and comment
                               lines, values substituted); Test-AgentSources.ps1 BUDGET-ROLE

    Template grammar:
      A line that is exactly {{> soul/<NN-id>}} is replaced by that fragment's lines.
      Fragments may include other fragments the same way.
      {{= Key}} is replaced inline by the family Values entry Key (case-sensitive).
      A line that starts with "%% " (or is exactly "%%") is a template comment and is removed.

    README grammar (Invoke-AgentReadmeCompose): the same include and value lines (a source includes only fragments of
    its own kind), the values FamilyVersion, Id, DisplayName, License, SoulTokens and SoulTokensDelta besides the
    family Values, the generated blocks {{# roster}} and {{# credits}} (each alone on its line), no digit before
    "tokens", and every output rule except '## Output'.

    agents/<id>/SOUL.md, and README.md in a family with a readmes/ folder, are generated by
    build/Compose-AgentSouls.ps1 and never hand-written.

    Error objects are hashtables @{ Path; Line; Message }. Path is relative to the repo root
    with forward slashes; Line is 1-based, or 0 when no line applies.
#>

Set-StrictMode -Version Latest

$script:RegistryRelPath = 'build/agent-src/families.psd1'
$script:LegacyFamilyRelPath = 'build/agent-src/family.psd1'
$script:LegacyFamilyId = 'default'
$script:FamilyId = $script:LegacyFamilyId
$script:FamilyRelPath = 'build/agent-src/family.psd1'
$script:SoulsRelDir = 'build/agent-src/souls'
$script:FragmentsRelDir = 'build/agent-src/fragments/soul'
$script:ReadmesRelDir = 'build/agent-src/readmes'
$script:ReadmeFragmentsRelDir = 'build/agent-src/fragments/readme'
$script:AgentsRelDir = 'agents'
$script:FamilyIdRegex = [regex]::new('^[a-z][a-z0-9-]{1,31}$')
$script:FamilyPathRegex = [regex]::new('^(?:[A-Za-z0-9_.-]+/)*family\.psd1$')
$script:TagRegex = [regex]::new('^[a-z0-9]+(?:-[a-z0-9]+)*$')
$script:SkillNameRegex = [regex]::new('^[a-z0-9][a-z0-9-]{1,63}$')
$script:ToolNameRegex = [regex]::new('^[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)*$')
$script:SemVerCoreRegex = [regex]::new('^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')
$script:Categories = @('utility', 'productivity', 'communication', 'data', 'development', 'integration', 'ai', 'automation', 'other')
$script:StrictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)
$script:LenientUtf8 = [System.Text.UTF8Encoding]::new($false, $false)
$script:IncludeRegex = [regex]::new('^\{\{> (?<ref>[^{}\s]+)\}\}$')
$script:KindRefRegex = [regex]::new('^(?<kind>soul|readme)/(?<id>[0-9]{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*)$')
$script:DirectiveRegex = [regex]::new('^\{\{# (?<name>[a-z]+)\}\}$')
# A hand-written figure: a number (with an optional k suffix) up to three words before "tokens", so
# "4,300 tokens", "about 4,300 more tokens" and "8k tokens" all fail. It runs on the raw source line,
# so "{{= SoulTokensDelta}} more tokens" passes.
$script:TokenFigureRegex = [regex]::new('\b\d[\d,.]*k?\b(?:\s+[A-Za-z-]+){0,3}\s+tokens\b', 'IgnoreCase, CultureInvariant')
$script:FragmentRefRegex = [regex]::new('^soul/(?<id>[0-9]{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*)$')
$script:FragmentIdRegex = [regex]::new('^[0-9]{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*$')
$script:ValueRegex = [regex]::new('\{\{= (?<key>[A-Za-z][A-Za-z0-9]*)\}\}')
$script:ValueKeyRegex = [regex]::new('^[A-Za-z][A-Za-z0-9]*$')
$script:AgentIdRegex = [regex]::new('^[a-z0-9][a-z0-9-]{1,63}$')
$script:AgentKeys = @('Id', 'DisplayName', 'SoulCap', 'Writer', 'SubAgents', 'Effort', 'Fragments', 'Credits')
$script:OptionalAgentKeys = @('License', 'Category', 'RequiredTags', 'RoleCap', 'Skills', 'Summary', 'Changes', 'Commits')
$script:LicenseValues = @('MIT', 'Apache-2.0')
$script:CategoryValues = @('utility', 'productivity', 'communication', 'data', 'development', 'integration', 'ai', 'automation', 'other')
$script:EffortValues = @('high', 'default')
$script:BytesPerToken = 3.8

# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------

function New-AgentComposeError {
    param([string]$Path, [int]$Line, [string]$Message)
    @{ Path = $Path; Line = $Line; Message = $Message }
}

function Get-AgentItems {
    # Emits the items of an array (or the single value); emits nothing for $null.
    param($Value)
    if ($null -ne $Value) { $Value }
}

function Get-AgentIdOf {
    param($Agent)
    if ($Agent -is [hashtable] -and $Agent['Id'] -is [string]) { return [string]$Agent['Id'] }
    ''
}

# PowerShell's -ceq / -ccontains compare culture-sensitively and treat zero-width characters
# (BOM, ZWSP, ...) as ignorable, so every exact comparison here is ordinal.
function Test-AgentSame {
    param([AllowNull()][object]$Left, [AllowNull()][object]$Right)
    if ($null -eq $Left -or $null -eq $Right) { return ($null -eq $Left -and $null -eq $Right) }
    [string]::Equals([string]$Left, [string]$Right, [StringComparison]::Ordinal)
}

function Test-AgentInList {
    param([AllowNull()][object[]]$List, [AllowNull()][object]$Value)
    if ($null -eq $List -or $null -eq $Value) { return $false }
    $needle = [string]$Value
    foreach ($item in $List) {
        if ($null -ne $item -and [string]::Equals([string]$item, $needle, [StringComparison]::Ordinal)) { return $true }
    }
    $false
}

function Test-AgentCommentLine {
    param([string]$Text)
    [string]::Equals($Text, '%%', [StringComparison]::Ordinal) -or $Text.StartsWith('%% ', [StringComparison]::Ordinal)
}

function Join-AgentRepoPath {
    param([string]$Root, [string]$RelativePath)
    [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($Root, $RelativePath))
}

function Test-AgentBytesEqual {
    param([byte[]]$Left, [byte[]]$Right)
    if ($null -eq $Left -or $null -eq $Right) { return $false }
    if ($Left.Length -ne $Right.Length) { return $false }
    [System.Linq.Enumerable]::SequenceEqual($Left, $Right)
}

function Split-AgentTextLines {
    param([string]$Text)
    $list = [System.Collections.Generic.List[string]]::new()
    $ends = $false
    if ($Text.Length -gt 0) {
        $list.AddRange([string[]]$Text.Split([char]10))
        $ends = $Text.EndsWith("`n", [StringComparison]::Ordinal)
        if ($ends) { $list.RemoveAt($list.Count - 1) }
    }
    @{ Lines = $list.ToArray(); EndsWithNewline = $ends }
}

function ConvertTo-AgentVisibleText {
    # Renders a line for DRIFT output: control, format and trailing space characters are escaped.
    # $null (no such line) stays distinct from '' (a blank line), so the parameter is untyped.
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return '(end of file)' }
    $Text = [string]$Value
    if ($Text.Length -eq 0) { return '(blank line)' }
    $trimmed = $Text.TrimEnd(' ')
    $sb = [System.Text.StringBuilder]::new()
    foreach ($ch in $trimmed.ToCharArray()) {
        $code = [int]$ch
        if ($code -eq 13) { [void]$sb.Append('\r') }
        elseif ($code -eq 9) { [void]$sb.Append('\t') }
        elseif ($code -lt 32 -or $code -eq 127 -or $code -eq 0xFEFF -or
            ($code -ge 0x200B -and $code -le 0x200F) -or ($code -ge 0x202A -and $code -le 0x202E) -or
            ($code -ge 0x2060 -and $code -le 0x2069)) {
            [void]$sb.Append(('\u{0:X4}' -f $code))
        }
        else { [void]$sb.Append($ch) }
    }
    $escapedSpace = '\u{0:X4}' -f 32
    for ($i = $trimmed.Length; $i -lt $Text.Length; $i++) { [void]$sb.Append($escapedSpace) }
    $sb.ToString()
}

function Get-AgentMarkdownBaseNames {
    param([string]$Directory)
    if (-not [System.IO.Directory]::Exists($Directory)) { return }
    $names = [string[]]@(
        foreach ($file in [System.IO.Directory]::GetFiles($Directory)) {
            if (Test-AgentSame ([System.IO.Path]::GetExtension($file)) '.md') {
                [System.IO.Path]::GetFileNameWithoutExtension($file)
            }
        }
    )
    [Array]::Sort($names, [StringComparer]::Ordinal)
    $names
}

# ---------------------------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------------------------

function Resolve-AgentFullPath {
    <#
    .SYNOPSIS
        Resolves a path (relative to the current PowerShell location) to a full file-system path.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$Path)
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    [System.IO.Path]::TrimEndingDirectorySeparator([System.IO.Path]::GetFullPath($full))
}

function ConvertTo-AgentRepoPath {
    <#
    .SYNOPSIS
        Returns Path relative to RepoRoot with forward slashes, or the full path when outside it.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$Path
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $full = Resolve-AgentFullPath -Path $Path
    $rel = [System.IO.Path]::GetRelativePath($root, $full)
    if ((Test-AgentSame $rel '..') -or
        $rel.StartsWith('..' + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::Ordinal) -or
        $rel.StartsWith('../', [StringComparison]::Ordinal) -or [System.IO.Path]::IsPathRooted($rel)) {
        return $full.Replace('\', '/')
    }
    $rel.Replace('\', '/')
}

function Get-AgentSoulPath {
    <#
    .SYNOPSIS
        Full path of an agent's generated file (-File, default SOUL.md): agents/<id>/<file>, or <OutDir>/<id>/<file>.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$Id,
        [string]$OutDir,
        [string]$File = 'SOUL.md'
    )
    if ($OutDir) {
        return [System.IO.Path]::Combine((Resolve-AgentFullPath -Path $OutDir), $Id, $File)
    }
    [System.IO.Path]::Combine((Resolve-AgentFullPath -Path $RepoRoot), $script:AgentsRelDir, $Id, $File)
}

function Get-AgentTemplatePath {
    <#
    .SYNOPSIS
        Repo-relative path (default) or full path (-Full) of build/agent-src/souls/<id>.md.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$Id,
        [switch]$Full
    )
    $rel = "$($script:SoulsRelDir)/$Id.md"
    if ($Full) { return Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $rel }
    $rel
}

function Get-AgentFragmentPath {
    <#
    .SYNOPSIS
        Repo-relative path (default) or full path (-Full) of build/agent-src/fragments/soul/<id>.md.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$FragmentId,
        [switch]$Full
    )
    $rel = "$($script:FragmentsRelDir)/$FragmentId.md"
    if ($Full) { return Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $rel }
    $rel
}

function Get-AgentFragmentIds {
    <#
    .SYNOPSIS
        Ids (file base names) of every build/agent-src/fragments/soul/*.md, in ordinal order.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = Resolve-AgentFullPath -Path $RepoRoot
    Get-AgentMarkdownBaseNames -Directory (Join-AgentRepoPath $root $script:FragmentsRelDir)
}

function Get-AgentTemplateIds {
    <#
    .SYNOPSIS
        Base names of every build/agent-src/souls/*.md, in ordinal order.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = Resolve-AgentFullPath -Path $RepoRoot
    Get-AgentMarkdownBaseNames -Directory (Join-AgentRepoPath $root $script:SoulsRelDir)
}

# ---------------------------------------------------------------------------------------------
# Family registry and context
# ---------------------------------------------------------------------------------------------

function Import-AgentDataFile {
    # Loads a .psd1 data file; throws InvalidOperationException with Data['Line'] on a syntax error.
    param([string]$FullPath, [string]$RelativePath)
    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($FullPath, [ref]$tokens, [ref]$parseErrors)
    if ($null -ne $parseErrors -and $parseErrors.Count -gt 0) {
        $exception = [System.InvalidOperationException]::new("syntax error: $($parseErrors[0].Message)")
        $exception.Data['Line'] = $parseErrors[0].Extent.StartLineNumber
        throw $exception
    }
    try {
        Import-PowerShellDataFile -LiteralPath $FullPath
    }
    catch {
        $exception = [System.InvalidOperationException]::new($_.Exception.Message.Replace($FullPath, $RelativePath))
        $exception.Data['Line'] = 1
        throw $exception
    }
}

function Get-AgentRegistryLine {
    # Best-effort line of the registry entry naming Id (1 when not found).
    param([string]$FullPath, [string]$Id)
    if (-not [System.IO.File]::Exists($FullPath)) { return 0 }
    if ($Id) {
        $idRegex = [regex]::new("\bId\s*=\s*'" + [regex]::Escape($Id) + "'")
        $lines = [System.IO.File]::ReadAllLines($FullPath)
        for ($i = 0; $i -lt $lines.Length; $i++) {
            if ($idRegex.IsMatch($lines[$i])) { return $i + 1 }
        }
    }
    1
}

function Get-AgentFamilyRegistry {
    <#
    .SYNOPSIS
        Reads build/agent-src/families.psd1. Returns @{ Legacy; Path; Families; Errors }.
    .DESCRIPTION
        Families holds @{ Id; Path; Dir } per entry, in registry order (Path is the repo-relative family
        file, Dir its folder). Without a registry file, Legacy is $true and Families holds the single
        legacy family (Id 'default', build/agent-src/family.psd1). Errors are error objects; when there
        are any, Families holds only the entries that passed.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $p = $script:RegistryRelPath
    $full = Join-AgentRepoPath $root $p
    $errors = [System.Collections.Generic.List[object]]::new()
    $families = [System.Collections.Generic.List[hashtable]]::new()
    if (-not [System.IO.File]::Exists($full)) {
        $families.Add(@{ Id = $script:LegacyFamilyId; Path = $script:LegacyFamilyRelPath; Dir = 'build/agent-src' })
        return @{ Legacy = $true; Path = $p; Families = $families.ToArray(); Errors = @() }
    }
    $data = $null
    try {
        $data = Import-AgentDataFile -FullPath $full -RelativePath $p
    }
    catch {
        $line = 1
        if ($_.Exception.Data.Contains('Line')) { $line = [int]$_.Exception.Data['Line'] }
        $message = ($_.Exception.Message -replace '\s+', ' ').Trim()
        $errors.Add((New-AgentComposeError $p $line "cannot load the family registry: $message"))
        return @{ Legacy = $false; Path = $p; Families = @(); Errors = $errors.ToArray() }
    }
    $topKeys = [string[]]@($data.Keys)
    [Array]::Sort($topKeys, [StringComparer]::Ordinal)
    foreach ($key in $topKeys) {
        if (-not (Test-AgentSame $key 'Families')) {
            $errors.Add((New-AgentComposeError $p 1 "unknown registry key $key (the registry holds Families only)"))
        }
    }
    $entries = @(Get-AgentItems $data['Families'])
    if ($entries.Count -eq 0) {
        $errors.Add((New-AgentComposeError $p 1 'Families must list at least one family'))
    }
    $seenIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $seenDirs = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($entry in $entries) {
        if ($entry -isnot [hashtable]) {
            $errors.Add((New-AgentComposeError $p 1 'each Families entry must be a hashtable @{ Id; Path }'))
            continue
        }
        $id = $entry['Id']
        $line = if ($id -is [string]) { Get-AgentRegistryLine -FullPath $full -Id $id } else { 1 }
        $good = $true
        $entryKeys = [string[]]@($entry.Keys)
        [Array]::Sort($entryKeys, [StringComparer]::Ordinal)
        foreach ($key in $entryKeys) {
            if (-not (Test-AgentInList @('Id', 'Path') $key)) {
                $errors.Add((New-AgentComposeError $p $line "family entry has unknown key $key (keys: Id, Path)"))
                $good = $false
            }
        }
        if ($id -isnot [string] -or -not $script:FamilyIdRegex.IsMatch($id)) {
            $errors.Add((New-AgentComposeError $p $line "family Id '$id' must match ^[a-z][a-z0-9-]{1,31}$"))
            continue
        }
        if (-not $seenIds.Add($id)) {
            $errors.Add((New-AgentComposeError $p $line "duplicate family Id '$id'"))
            continue
        }
        $path = $entry['Path']
        if ($path -isnot [string] -or -not $script:FamilyPathRegex.IsMatch($path) -or
            (Test-AgentInList ([string[]]$path.Split('/')) '..') -or (Test-AgentInList ([string[]]$path.Split('/')) '.')) {
            $errors.Add((New-AgentComposeError $p $line "family '$id': Path '$path' must be a repo-relative forward-slash path to a family.psd1 (no '.' or '..' segments)"))
            continue
        }
        $dir = if ($path.Contains('/')) { $path.Substring(0, $path.LastIndexOf('/')) } else { '.' }
        if (-not $seenDirs.Add($dir)) {
            $errors.Add((New-AgentComposeError $p $line "family '$id': another family already uses the folder $dir (souls and fragments would be shared)"))
            continue
        }
        if ($good) { $families.Add(@{ Id = $id; Path = $path; Dir = $dir }) }
    }
    @{ Legacy = $false; Path = $p; Families = $families.ToArray(); Errors = $errors.ToArray() }
}

function Set-AgentFamilyPaths {
    param([string]$Id, [string]$RelativePath)
    $dir = if ($RelativePath.Contains('/')) { $RelativePath.Substring(0, $RelativePath.LastIndexOf('/')) } else { '.' }
    $script:FamilyId = $Id
    $script:FamilyRelPath = $RelativePath
    $script:SoulsRelDir = "$dir/souls"
    $script:FragmentsRelDir = "$dir/fragments/soul"
    $script:ReadmesRelDir = "$dir/readmes"
    $script:ReadmeFragmentsRelDir = "$dir/fragments/readme"
}

function Set-AgentFamilyContext {
    <#
    .SYNOPSIS
        Selects the family every path function works on. Returns its registry entry @{ Id; Path; Dir }.
    .DESCRIPTION
        -Family names a registry Id. Without -Family the legacy single family is selected when there is
        no registry, or the only family when the registry lists one; a registry with several families
        needs -Family. -Entry selects a registry entry directly. Throws on an unknown family or a
        broken registry.
    #>
    [CmdletBinding(DefaultParameterSetName = 'ById')]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory, ParameterSetName = 'ById')][string]$RepoRoot,
        [Parameter(ParameterSetName = 'ById')][string]$Family,
        [Parameter(Mandatory, ParameterSetName = 'ByEntry')][hashtable]$Entry
    )
    if ($PSCmdlet.ParameterSetName -eq 'ByEntry') {
        Set-AgentFamilyPaths -Id ([string]$Entry['Id']) -RelativePath ([string]$Entry['Path'])
        return $Entry
    }
    $registry = Get-AgentFamilyRegistry -RepoRoot $RepoRoot
    if (@($registry['Errors']).Count -gt 0) {
        throw ('family registry error: ' + (Format-AgentComposeError -Item @($registry['Errors'])[0]))
    }
    $families = @($registry['Families'])
    $selected = $null
    if (-not $Family) {
        if ($families.Count -ne 1) {
            throw "the family registry lists $($families.Count) families ($(@($families | ForEach-Object { $_['Id'] }) -join ', ')); name one with -Family"
        }
        $selected = $families[0]
    }
    else {
        foreach ($candidate in $families) {
            if (Test-AgentSame $candidate['Id'] $Family) { $selected = $candidate }
        }
        if ($null -eq $selected) {
            throw "unknown family '$Family' (families: $(@($families | ForEach-Object { $_['Id'] }) -join ', '))"
        }
    }
    Set-AgentFamilyPaths -Id ([string]$selected['Id']) -RelativePath ([string]$selected['Path'])
    $selected
}

function Get-AgentFamilyContext {
    <#
    .SYNOPSIS
        The current family context: @{ Id; FamilyRelPath; SoulsRelDir; FragmentsRelDir; ReadmesRelDir; ReadmeFragmentsRelDir }.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param()
    @{
        Id = $script:FamilyId
        FamilyRelPath = $script:FamilyRelPath
        SoulsRelDir = $script:SoulsRelDir
        FragmentsRelDir = $script:FragmentsRelDir
        ReadmesRelDir = $script:ReadmesRelDir
        ReadmeFragmentsRelDir = $script:ReadmeFragmentsRelDir
    }
}

function Get-AgentRosterUnion {
    <#
    .SYNOPSIS
        Loads every registered family (or the -Family selection) and returns the union of their rosters.
    .DESCRIPTION
        Returns @{ Legacy; Families; Ids; Owner; Errors }. Families holds @{ Id; Path; Dir; Data; Roster }
        per loaded family, in registry order (Data is the Get-AgentFamily result, Roster its ids in
        ordinal order). Ids is the ordinal-sorted union; Owner maps each id to its family Id. An id in two
        families, a missing or unloadable family file, a family Id key that differs from the registry,
        and an unknown -Family name are errors. The family context is restored before returning.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string[]]$Family = @()
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $saved = Get-AgentFamilyContext
    $errors = [System.Collections.Generic.List[object]]::new()
    $loaded = [System.Collections.Generic.List[hashtable]]::new()
    $owner = [System.Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
    $registry = Get-AgentFamilyRegistry -RepoRoot $root
    foreach ($e in @($registry['Errors'])) { $errors.Add($e) }

    $wanted = [System.Collections.Generic.List[string]]::new()
    foreach ($item in @(Get-AgentItems $Family)) {
        foreach ($part in ([string]$item).Split(',')) {
            $name = $part.Trim()
            if ($name -and -not $wanted.Contains($name)) { $wanted.Add($name) }
        }
    }
    $known = [string[]]@(foreach ($f in @($registry['Families'])) { [string]$f['Id'] })
    foreach ($name in $wanted) {
        if (-not (Test-AgentInList $known $name)) {
            $errors.Add((New-AgentComposeError $script:RegistryRelPath 1 "unknown family '$name' (families: $($known -join ', '))"))
        }
    }

    try {
        foreach ($entry in @($registry['Families'])) {
            if ($wanted.Count -gt 0 -and -not $wanted.Contains([string]$entry['Id'])) { continue }
            Set-AgentFamilyPaths -Id ([string]$entry['Id']) -RelativePath ([string]$entry['Path'])
            $data = $null
            try {
                $data = Get-AgentFamily -RepoRoot $root
            }
            catch {
                $line = 0
                if ($_.Exception.Data.Contains('Line')) { $line = [int]$_.Exception.Data['Line'] }
                $message = ($_.Exception.Message -replace '\s+', ' ').Trim()
                $errors.Add((New-AgentComposeError ([string]$entry['Path']) $line "cannot load family '$($entry['Id'])': $message"))
                continue
            }
            if (-not $registry['Legacy'] -and $data.ContainsKey('Id') -and -not (Test-AgentSame $data['Id'] $entry['Id'])) {
                $errors.Add((New-AgentComposeError ([string]$entry['Path']) (Get-AgentFamilyLine -RepoRoot $root -Key 'Id') "family Id '$($data['Id'])' differs from the registry Id '$($entry['Id'])'"))
            }
            $ids = [System.Collections.Generic.List[string]]::new()
            foreach ($agent in @(Get-AgentItems $data['Agents'])) {
                $agentId = Get-AgentIdOf $agent
                if (-not $agentId -or $ids.Contains($agentId)) { continue }
                $ids.Add($agentId)
                $previous = $null
                if ($owner.TryGetValue($agentId, [ref]$previous)) {
                    $line = Get-AgentFamilyLine -RepoRoot $root -AgentId $agentId
                    $errors.Add((New-AgentComposeError ([string]$entry['Path']) $line "agent '$agentId' is in two families ($previous and $($entry['Id'])); an id belongs to one family"))
                }
                else {
                    $owner[$agentId] = [string]$entry['Id']
                }
            }
            $ids.Sort([StringComparer]::Ordinal)
            $loaded.Add(@{ Id = [string]$entry['Id']; Path = [string]$entry['Path']; Dir = [string]$entry['Dir']; Data = $data; Roster = $ids.ToArray() })
        }
    }
    finally {
        Set-AgentFamilyPaths -Id $saved['Id'] -RelativePath $saved['FamilyRelPath']
    }
    $union = [string[]]@($owner.Keys)
    [Array]::Sort($union, [StringComparer]::Ordinal)
    @{
        Legacy = [bool]$registry['Legacy']
        Families = $loaded.ToArray()
        Ids = $union
        Owner = $owner
        Errors = $errors.ToArray()
    }
}

# ---------------------------------------------------------------------------------------------
# Family data
# ---------------------------------------------------------------------------------------------

function Get-AgentFamily {
    <#
    .SYNOPSIS
        Loads the current family's family.psd1 and returns it with Agents sorted ordinal by Id.
    .DESCRIPTION
        Throws when the file is missing or cannot be parsed as a data file.
        Use Test-AgentFamilyData for schema errors.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $path = Join-AgentRepoPath $root $script:FamilyRelPath
    if (-not [System.IO.File]::Exists($path)) {
        throw "family data not found: $($script:FamilyRelPath)"
    }
    $data = Import-AgentDataFile -FullPath $path -RelativePath $script:FamilyRelPath
    $items = [object[]]@(Get-AgentItems $data['Agents'])
    if ($items.Length -gt 1) {
        $keys = [string[]]::new($items.Length)
        for ($i = 0; $i -lt $items.Length; $i++) { $keys[$i] = Get-AgentIdOf $items[$i] }
        [Array]::Sort($keys, $items, [StringComparer]::Ordinal)
    }
    $data['Agents'] = $items
    $data
}

function Get-AgentFamilyAgent {
    <#
    .SYNOPSIS
        Returns the family Agents entry whose Id equals Id (ordinal), or $null.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][hashtable]$Family,
        [Parameter(Mandatory)][string]$Id
    )
    foreach ($agent in @(Get-AgentItems $Family['Agents'])) {
        if (Test-AgentSame (Get-AgentIdOf $agent) $Id) { return $agent }
    }
    $null
}

function Resolve-AgentLicenseSource {
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][string]$License)
    if (Test-AgentSame $License 'MIT') { return 'LICENSE' }
    if (Test-AgentSame $License 'Apache-2.0') { return 'build/licenses/Apache-2.0.txt' }
    throw "unsupported agent license '$License'"
}

function Get-AgentFamilyLine {
    <#
    .SYNOPSIS
        Best-effort 1-based line number in family.psd1, for error messages.
    .DESCRIPTION
        -Key finds the line that assigns that top-level key. -AgentId finds the agent's Id line;
        with -Text it finds the first line after it containing '<Text>' (quoted). Returns 1 when
        nothing matches and 0 when the file is missing.
    #>
    [CmdletBinding()]
    [OutputType([int])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$AgentId,
        [string]$Text,
        [string]$Key
    )
    $path = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $script:FamilyRelPath
    if (-not [System.IO.File]::Exists($path)) { return 0 }
    $lines = [System.IO.File]::ReadAllLines($path)
    if ($Key) {
        $keyRegex = [regex]::new('^\s*' + [regex]::Escape($Key) + '\s*=')
        for ($i = 0; $i -lt $lines.Length; $i++) {
            if ($keyRegex.IsMatch($lines[$i])) { return $i + 1 }
        }
        return 1
    }
    $start = 0
    $found = 0
    if ($AgentId) {
        $idRegex = [regex]::new("\bId\s*=\s*'" + [regex]::Escape($AgentId) + "'")
        for ($i = 0; $i -lt $lines.Length; $i++) {
            if ($idRegex.IsMatch($lines[$i])) { $start = $i; $found = $i + 1; break }
        }
        if ($found -eq 0) { return 1 }
    }
    if ($Text) {
        $needle = "'" + $Text + "'"
        for ($i = $start; $i -lt $lines.Length; $i++) {
            if ($lines[$i].Contains($needle)) { return $i + 1 }
        }
    }
    if ($found -gt 0) { return $found }
    1
}

function Test-AgentFamilyData {
    <#
    .SYNOPSIS
        Schema checks for family.psd1 that the composer depends on. Emits error objects.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][hashtable]$Family
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $p = $script:FamilyRelPath
    $errors = [System.Collections.Generic.List[object]]::new()

    $values = $Family['Values']
    if ($values -isnot [hashtable]) {
        $errors.Add((New-AgentComposeError $p (Get-AgentFamilyLine -RepoRoot $root -Key 'Values') 'Values must be a hashtable of strings'))
    }
    else {
        $valueLine = Get-AgentFamilyLine -RepoRoot $root -Key 'Values'
        $keys = [string[]]@($values.Keys)
        [Array]::Sort($keys, [StringComparer]::Ordinal)
        foreach ($key in $keys) {
            $value = $values[$key]
            if (-not $script:ValueKeyRegex.IsMatch($key)) {
                $errors.Add((New-AgentComposeError $p $valueLine "value key '$key' must match ^[A-Za-z][A-Za-z0-9]*$"))
            }
            elseif ($value -isnot [string]) {
                $errors.Add((New-AgentComposeError $p $valueLine "value '$key' must be a string"))
            }
            elseif ($value.Contains("`n") -or $value.Contains("`r")) {
                $errors.Add((New-AgentComposeError $p $valueLine "value '$key' must be a single line"))
            }
            elseif ($value.Contains('{{')) {
                $errors.Add((New-AgentComposeError $p $valueLine "value '$key' must not contain '{{'"))
            }
        }
    }

    $credits = $Family['Credits']
    $agents = @(Get-AgentItems $Family['Agents'])
    $agentsLine = Get-AgentFamilyLine -RepoRoot $root -Key 'Agents'
    if ($agents.Count -eq 0) {
        $errors.Add((New-AgentComposeError $p $agentsLine 'Agents must list at least one agent'))
    }
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($agent in $agents) {
        if ($agent -isnot [hashtable]) {
            $errors.Add((New-AgentComposeError $p $agentsLine 'each Agents entry must be a hashtable'))
            continue
        }
        $id = $agent['Id']
        if ($id -isnot [string] -or -not $script:AgentIdRegex.IsMatch($id)) {
            $errors.Add((New-AgentComposeError $p $agentsLine "agent Id '$id' must match ^[a-z0-9][a-z0-9-]{1,63}$"))
            continue
        }
        $line = Get-AgentFamilyLine -RepoRoot $root -AgentId $id
        if (-not $seen.Add($id)) {
            $errors.Add((New-AgentComposeError $p $line "duplicate agent Id '$id'"))
        }
        foreach ($key in $script:AgentKeys) {
            if (-not $agent.ContainsKey($key)) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id' is missing key $key"))
            }
        }
        $agentKeys = [string[]]@($agent.Keys)
        [Array]::Sort($agentKeys, [StringComparer]::Ordinal)
        foreach ($key in $agentKeys) {
            if (-not (Test-AgentInList $script:AgentKeys $key) -and -not (Test-AgentInList $script:OptionalAgentKeys $key)) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id' has unknown key $key"))
            }
        }
        if ($agent.ContainsKey('License') -and ($agent['License'] -isnot [string] -or -not (Test-AgentInList $script:LicenseValues $agent['License']))) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': License must be 'MIT' or 'Apache-2.0'"))
        }
        if ($agent.ContainsKey('Category') -and ($agent['Category'] -isnot [string] -or -not (Test-AgentInList $script:CategoryValues $agent['Category']))) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': Category must be a supported category"))
        }
        if ($agent.ContainsKey('RequiredTags')) {
            $tags = $agent['RequiredTags']
            if ($tags -isnot [array] -or $tags.Count -eq 0 -or $tags.Count -gt 10) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id': RequiredTags must be an array of 1-10 tags"))
            }
            else {
                $seenTags = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
                foreach ($tag in $tags) {
                    if ($tag -isnot [string] -or $tag.Length -gt 32 -or $tag -cnotmatch '^[a-z0-9]+(?:-[a-z0-9]+)*\z') {
                        $errors.Add((New-AgentComposeError $p $line "agent '$id': RequiredTags entries must be kebab-case, at most 32 characters"))
                    }
                    elseif (-not $seenTags.Add($tag)) {
                        $errors.Add((New-AgentComposeError $p $line "agent '$id': duplicate required tag '$tag'"))
                    }
                }
            }
        }
        if ($agent.ContainsKey('DisplayName') -and
            ($agent['DisplayName'] -isnot [string] -or [string]::IsNullOrWhiteSpace($agent['DisplayName']))) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': DisplayName must be a non-empty string"))
        }
        if ($agent.ContainsKey('SoulCap') -and ($agent['SoulCap'] -isnot [int] -or $agent['SoulCap'] -le 0)) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': SoulCap must be a positive integer"))
        }
        if ($agent.ContainsKey('RoleCap') -and ($agent['RoleCap'] -isnot [int] -or $agent['RoleCap'] -le 0)) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': RoleCap must be a positive integer"))
        }
        foreach ($cellKey in 'Summary', 'Changes', 'Commits') {
            if ($agent.ContainsKey($cellKey) -and ($agent[$cellKey] -isnot [string] -or $agent[$cellKey].Length -eq 0 -or $agent[$cellKey].Contains('|') -or $agent[$cellKey].Contains("`n") -or $agent[$cellKey].Contains('{{'))) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id': $cellKey must be a non-empty single-line string without '|' or '{{' (a roster-table cell)"))
            }
        }
        if ($agent.ContainsKey('Skills')) {
            # A subset of SkillPolicy.Skills: absent means every policy skill, @() means none.
            $policySkills = [string[]]@(if ($Family['SkillPolicy'] -is [hashtable]) {
                    foreach ($skill in @(Get-AgentItems $Family['SkillPolicy']['Skills'])) { if ($skill -is [hashtable] -and $skill['Name'] -is [string]) { $skill['Name'] } }
                })
            $skillList = $agent['Skills']
            if ($null -ne $skillList -and $skillList -isnot [array]) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id': Skills must be an array of SkillPolicy skill names (@() for none)"))
            }
            else {
                $seenSkills = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
                foreach ($skillName in @(Get-AgentItems $skillList)) {
                    if ($skillName -isnot [string] -or -not (Test-AgentInList $policySkills $skillName)) {
                        $errors.Add((New-AgentComposeError $p $line "agent '$id': Skills entry '$skillName' is not a SkillPolicy skill ($(if ($policySkills.Length) { $policySkills -join ', ' } else { 'the family has no SkillPolicy' }))"))
                    }
                    elseif (-not $seenSkills.Add($skillName)) {
                        $errors.Add((New-AgentComposeError $p $line "agent '$id': Skills lists $skillName twice"))
                    }
                }
            }
        }
        if ($agent.ContainsKey('Writer') -and $agent['Writer'] -isnot [bool]) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': Writer must be `$true or `$false"))
        }
        if ($agent.ContainsKey('SubAgents')) {
            $sub = $agent['SubAgents']
            if ($sub -isnot [hashtable] -or $sub['enabled'] -isnot [bool] -or $sub['maxDepth'] -isnot [int] -or
                $sub['maxDepth'] -lt 0 -or $sub['maxDepth'] -gt 8) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id': SubAgents must be @{ enabled = `$true|`$false; maxDepth = 0..8 }"))
            }
        }
        if ($agent.ContainsKey('Effort') -and -not (Test-AgentInList $script:EffortValues $agent['Effort'])) {
            $errors.Add((New-AgentComposeError $p $line "agent '$id': Effort must be 'high' or 'default'"))
        }
        if ($agent.ContainsKey('Fragments')) {
            $fragments = @(Get-AgentItems $agent['Fragments'])
            if ($fragments.Count -eq 0) {
                $errors.Add((New-AgentComposeError $p $line "agent '$id': Fragments must list at least one fragment"))
            }
            $seenFragments = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach ($fragment in $fragments) {
                if ($fragment -isnot [string] -or -not $script:FragmentIdRegex.IsMatch($fragment)) {
                    $errors.Add((New-AgentComposeError $p $line "agent '$id': fragment id '$fragment' must look like NN-name"))
                }
                elseif (-not $seenFragments.Add($fragment)) {
                    $fragmentLine = Get-AgentFamilyLine -RepoRoot $root -AgentId $id -Text $fragment
                    $errors.Add((New-AgentComposeError $p $fragmentLine "agent '$id' lists fragment $fragment twice"))
                }
            }
        }
        if ($agent.ContainsKey('Credits')) {
            foreach ($credit in @(Get-AgentItems $agent['Credits'])) {
                if ($credit -isnot [string] -or $credits -isnot [hashtable] -or -not $credits.ContainsKey($credit)) {
                    $errors.Add((New-AgentComposeError $p $line "agent '$id': credit '$credit' is not a key of the family Credits"))
                }
            }
        }
    }
    if ($Family.ContainsKey('Lead') -and -not $seen.Contains([string]$Family['Lead'])) {
        $errors.Add((New-AgentComposeError $p (Get-AgentFamilyLine -RepoRoot $root -Key 'Lead') "Lead '$($Family['Lead'])' is not in the roster"))
    }
    foreach ($e in @(Test-AgentFamilyOptionalKeys -RepoRoot $root -Family $Family)) { $errors.Add($e) }
    $errors.ToArray()
}

function Test-AgentFamilyOptionalKeys {
    # Shape checks for the optional family keys (see the module header).
    param([string]$RepoRoot, [hashtable]$Family)
    $p = $script:FamilyRelPath
    $errors = [System.Collections.Generic.List[object]]::new()
    $at = { param($key) Get-AgentFamilyLine -RepoRoot $RepoRoot -Key $key }

    if ($Family.ContainsKey('Id')) {
        $id = $Family['Id']
        if ($id -isnot [string] -or -not $script:FamilyIdRegex.IsMatch($id)) {
            $errors.Add((New-AgentComposeError $p (& $at 'Id') "Id '$id' must match ^[a-z][a-z0-9-]{1,31}$"))
        }
        elseif (-not (Test-AgentSame $script:FamilyId $script:LegacyFamilyId) -and -not (Test-AgentSame $id $script:FamilyId)) {
            $errors.Add((New-AgentComposeError $p (& $at 'Id') "Id '$id' differs from the registry Id '$($script:FamilyId)'"))
        }
    }
    if ($Family.ContainsKey('RequiredTag')) {
        $tag = $Family['RequiredTag']
        if ($tag -isnot [string] -or $tag.Length -gt 32 -or -not $script:TagRegex.IsMatch($tag)) {
            $errors.Add((New-AgentComposeError $p (& $at 'RequiredTag') "RequiredTag '$tag' must be a kebab-case tag of at most 32 characters"))
        }
    }
    if ($Family.ContainsKey('Category') -and -not (Test-AgentInList $script:Categories $Family['Category'])) {
        $errors.Add((New-AgentComposeError $p (& $at 'Category') "Category '$($Family['Category'])' must be one of: $($script:Categories -join ', ')"))
    }
    if ($Family.ContainsKey('CreditsSentence')) {
        $sentence = $Family['CreditsSentence']
        if ($sentence -isnot [string] -or $sentence.Contains("`n") -or $sentence.Contains("`r")) {
            $errors.Add((New-AgentComposeError $p (& $at 'CreditsSentence') 'CreditsSentence must be a single-line string (empty for no sentence check)'))
        }
    }
    if ($Family.ContainsKey('CreditsSentenceKeys')) {
        $familyCredits = $Family['Credits']
        $sentenceKeys = @(Get-AgentItems $Family['CreditsSentenceKeys'])
        if ($sentenceKeys.Count -eq 0) {
            $errors.Add((New-AgentComposeError $p (& $at 'CreditsSentenceKeys') 'CreditsSentenceKeys must list at least one Credits key (omit it for every key)'))
        }
        foreach ($key in $sentenceKeys) {
            if ($key -isnot [string] -or $familyCredits -isnot [hashtable] -or -not $familyCredits.ContainsKey($key)) {
                $errors.Add((New-AgentComposeError $p (& $at 'CreditsSentenceKeys') "CreditsSentenceKeys: '$key' is not a key of the family Credits"))
            }
        }
    }
    if ($Family.ContainsKey('ReadmeCaps')) {
        $caps = $Family['ReadmeCaps']
        $good = $caps -is [hashtable] -and $caps.Count -eq 2
        if ($good) {
            foreach ($key in 'Lead', 'Other') {
                if (-not $caps.ContainsKey($key) -or $caps[$key] -isnot [int] -or $caps[$key] -le 0 -or $caps[$key] -gt 65536) { $good = $false }
            }
        }
        if (-not $good) {
            $errors.Add((New-AgentComposeError $p (& $at 'ReadmeCaps') 'ReadmeCaps must be @{ Lead = <bytes>; Other = <bytes> } with sizes 1..65536'))
        }
    }
    if ($Family.ContainsKey('FragmentCaps')) {
        $fragmentCaps = $Family['FragmentCaps']
        if ($fragmentCaps -isnot [hashtable]) {
            $errors.Add((New-AgentComposeError $p (& $at 'FragmentCaps') "FragmentCaps must be @{ '<NN-id>' = <bytes> } with sizes 1..4096"))
        }
        else {
            foreach ($key in @($fragmentCaps.Keys | Sort-Object)) {
                $value = $fragmentCaps[$key]
                if (-not $script:FragmentIdRegex.IsMatch([string]$key) -or $value -isnot [int] -or $value -le 0 -or $value -gt 4096) {
                    $errors.Add((New-AgentComposeError $p (& $at 'FragmentCaps') "FragmentCaps '$key' = '$value': the key is a fragment id (NN-id) and the value 1..4096 bytes"))
                }
            }
        }
    }
    if ($Family.ContainsKey('SkillPolicy')) {
        $line = & $at 'SkillPolicy'
        $policy = $Family['SkillPolicy']
        if ($policy -isnot [hashtable]) {
            $errors.Add((New-AgentComposeError $p $line 'SkillPolicy must be @{ Skills = @(@{ Name; MinVersion }); ExtraRequiredTools = @(...) }'))
        }
        else {
            $policyKeys = [string[]]@($policy.Keys)
            [Array]::Sort($policyKeys, [StringComparer]::Ordinal)
            foreach ($key in $policyKeys) {
                if (-not (Test-AgentInList @('Skills', 'ExtraRequiredTools') $key)) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy has unknown key $key (keys: Skills, ExtraRequiredTools)"))
                }
            }
            $skills = @(Get-AgentItems $policy['Skills'])
            if ($skills.Count -eq 0 -or $skills.Count -gt 16) {
                $errors.Add((New-AgentComposeError $p $line 'SkillPolicy.Skills must list 1-16 skills'))
            }
            $seenSkills = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            $seenFragments = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach ($skill in $skills) {
                $name = if ($skill -is [hashtable]) { $skill['Name'] } else { $null }
                $skillKeys = if ($skill -is [hashtable]) { [string[]]@($skill.Keys) } else { [string[]]@() }
                $extraKeys = @($skillKeys | Where-Object { -not (Test-AgentInList @('Name', 'MinVersion', 'Fragment', 'TopicIndex') $_) })
                if ($skill -isnot [hashtable] -or $name -isnot [string] -or -not $script:SkillNameRegex.IsMatch($name) -or $extraKeys.Count -gt 0) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills entry '$name' must be @{ Name = '<skill>'; MinVersion = 'x.y.z'; Fragment = '<NN-id>'; TopicIndex = '<repo path>' } (MinVersion, Fragment and TopicIndex optional) with a name matching ^[a-z0-9][a-z0-9-]{1,63}$"))
                    continue
                }
                if ($skill.ContainsKey('Fragment') -and ($skill['Fragment'] -isnot [string] -or -not $script:FragmentIdRegex.IsMatch($skill['Fragment']))) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills '$name': Fragment '$($skill['Fragment'])' must be a fragment id (NN-name)"))
                }
                if ($skill.ContainsKey('Fragment') -and $skill['Fragment'] -is [string] -and -not $seenFragments.Add($skill['Fragment'])) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills '$name': Fragment $($skill['Fragment']) is already the reference fragment of another skill"))
                }
                if ($skill.ContainsKey('TopicIndex')) {
                    $topicIndex = $skill['TopicIndex']
                    if ($topicIndex -isnot [string] -or $topicIndex -notmatch '^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$' -or $topicIndex -match '(^|/)\.\.?(/|$)') {
                        $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills '$name': TopicIndex '$topicIndex' must be a repository-relative path with forward slashes"))
                    }
                    elseif ($RepoRoot -and -not [System.IO.File]::Exists((Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $topicIndex))) {
                        $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills '$name': TopicIndex $topicIndex does not exist"))
                    }
                }
                if (-not $seenSkills.Add($name)) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills lists $name twice"))
                }
                if ($skill.ContainsKey('MinVersion') -and ($skill['MinVersion'] -isnot [string] -or -not $script:SemVerCoreRegex.IsMatch($skill['MinVersion']))) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.Skills '$name': MinVersion '$($skill['MinVersion'])' must be x.y.z"))
                }
            }
            $seenTools = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach ($tool in @(Get-AgentItems $policy['ExtraRequiredTools'])) {
                if ($tool -isnot [string] -or -not $script:ToolNameRegex.IsMatch($tool)) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.ExtraRequiredTools entry '$tool' is not a tool name"))
                }
                elseif (-not $seenTools.Add($tool)) {
                    $errors.Add((New-AgentComposeError $p $line "SkillPolicy.ExtraRequiredTools lists $tool twice"))
                }
            }
        }
    }
    if ($Family.ContainsKey('AllowRestrictedMentions')) {
        foreach ($tool in @(Get-AgentItems $Family['AllowRestrictedMentions'])) {
            if ($tool -isnot [string] -or -not $script:ToolNameRegex.IsMatch($tool)) {
                $errors.Add((New-AgentComposeError $p (& $at 'AllowRestrictedMentions') "AllowRestrictedMentions entry '$tool' is not a tool name"))
            }
        }
    }
    if ($Family.ContainsKey('RosterOrder')) {
        $order = $Family['RosterOrder']
        $roster = [string[]]@(foreach ($agent in @(Get-AgentItems $Family['Agents'])) { Get-AgentIdOf $agent })
        if ($order -isnot [array] -or $order.Count -eq 0) {
            $errors.Add((New-AgentComposeError $p (& $at 'RosterOrder') 'RosterOrder must list the roster-table agent ids in table order'))
        }
        else {
            $seenOrder = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach ($id in $order) {
                if ($id -isnot [string] -or -not (Test-AgentInList $roster $id)) {
                    $errors.Add((New-AgentComposeError $p (& $at 'RosterOrder') "RosterOrder entry '$id' is not in the roster"))
                }
                elseif (-not $seenOrder.Add($id)) {
                    $errors.Add((New-AgentComposeError $p (& $at 'RosterOrder') "RosterOrder lists $id twice"))
                }
            }
        }
    }
    if ($Family.ContainsKey('Method')) {
        foreach ($message in @(Get-AgentMethodShapeErrors -Method $Family['Method'] -Family $Family)) {
            $errors.Add((New-AgentComposeError $p (& $at 'Method') $message))
        }
    }
    $errors.ToArray()
}

function Get-AgentMethodShapeErrors {
    # Shape of the optional Method key (the registry of tested rules). Emits one message per problem.
    param($Method, [hashtable]$Family)
    if ($Method -isnot [hashtable]) { 'Method must be @{ Controller = @{...}; Worker = @{...}; Rules = @(...) }'; return }
    $roster = [string[]]@(foreach ($agent in @(Get-AgentItems $Family['Agents'])) { Get-AgentIdOf $agent })
    $isFragmentList = {
        param($value)
        foreach ($item in @(Get-AgentItems $value)) {
            if ($item -isnot [string] -or -not $script:FragmentIdRegex.IsMatch($item)) { return $false }
        }
        $true
    }
    foreach ($key in [string[]]@($Method.Keys)) {
        if (-not (Test-AgentInList @('Controller', 'Worker', 'Rules') $key)) { "Method has unknown key $key (keys: Controller, Worker, Rules)" }
    }
    $controller = $Method['Controller']
    $terms = [string[]]@()
    if ($null -ne $controller) {
        if ($controller -isnot [hashtable]) { 'Method.Controller must be @{ Fragments; Terms; Allow }' }
        else {
            foreach ($key in [string[]]@($controller.Keys)) {
                if (-not (Test-AgentInList @('Fragments', 'Terms', 'Allow') $key)) { "Method.Controller has unknown key $key (keys: Fragments, Terms, Allow)" }
            }
            if (-not (& $isFragmentList $controller['Fragments'])) { 'Method.Controller.Fragments must list fragment ids (NN-name)' }
            $terms = [string[]]@(foreach ($term in @(Get-AgentItems $controller['Terms'])) {
                    if ($term -isnot [string] -or $term.Length -eq 0) { continue }
                    $term
                })
            foreach ($term in @(Get-AgentItems $controller['Terms'])) {
                if ($term -isnot [string] -or $term.Length -eq 0) { "Method.Controller.Terms entry '$term' must be a non-empty regex string"; continue }
                try { [void][regex]::new($term) } catch { "Method.Controller.Terms entry '$term' is not a valid regex" }
            }
            foreach ($allow in @(Get-AgentItems $controller['Allow'])) {
                if ($allow -isnot [hashtable]) { 'Method.Controller.Allow entries must be @{ Agent or Fragment; Term; Why }'; continue }
                $who = @(@('Agent', 'Fragment') | Where-Object { $allow.ContainsKey($_) })
                $extra = @([string[]]@($allow.Keys) | Where-Object { -not (Test-AgentInList @('Agent', 'Fragment', 'Term', 'Why') $_) })
                if ($who.Count -ne 1 -or $extra.Count -gt 0) { 'Method.Controller.Allow entries name exactly one of Agent or Fragment, plus Term and Why'; continue }
                if (-not (Test-AgentInList $terms $allow['Term'])) { "Method.Controller.Allow term '$($allow['Term'])' is not one of Controller.Terms" }
                if ($allow['Why'] -isnot [string] -or [string]::IsNullOrWhiteSpace($allow['Why'])) { "Method.Controller.Allow entry for '$($allow['Term'])' needs a Why" }
                if ($who[0] -eq 'Agent' -and -not (Test-AgentInList $roster $allow['Agent'])) { "Method.Controller.Allow agent '$($allow['Agent'])' is not in the roster" }
                if ($who[0] -eq 'Fragment' -and ($allow['Fragment'] -isnot [string] -or -not $script:FragmentIdRegex.IsMatch($allow['Fragment']))) { "Method.Controller.Allow fragment '$($allow['Fragment'])' is not a fragment id" }
            }
        }
    }
    $worker = $Method['Worker']
    if ($null -ne $worker) {
        if ($worker -isnot [hashtable]) { 'Method.Worker must be @{ Fragments; Exempt }' }
        else {
            foreach ($key in [string[]]@($worker.Keys)) {
                if (-not (Test-AgentInList @('Fragments', 'Exempt') $key)) { "Method.Worker has unknown key $key (keys: Fragments, Exempt)" }
            }
            if (-not (& $isFragmentList $worker['Fragments'])) { 'Method.Worker.Fragments must list fragment ids (NN-name)' }
            foreach ($id in @(Get-AgentItems $worker['Exempt'])) {
                if (-not (Test-AgentInList $roster $id)) { "Method.Worker.Exempt agent '$id' is not in the roster" }
            }
        }
    }
    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($rule in @(Get-AgentItems $Method['Rules'])) {
        if ($rule -isnot [hashtable]) { 'Method.Rules entries must be @{ Id; Fragment or Agent; Anchor }'; continue }
        $id = $rule['Id']
        if ($id -isnot [string] -or $id -cnotmatch '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$') { "Method.Rules Id '$id' must be kebab-case and start with a letter (a fragment id starts with two digits)"; continue }
        if (-not $seen.Add($id)) { "Method.Rules lists $id twice" }
        $extra = @([string[]]@($rule.Keys) | Where-Object { -not (Test-AgentInList @('Id', 'Fragment', 'Agent', 'Anchor') $_) })
        if ($extra.Count -gt 0) { "Method.Rules '$id' has unknown key $($extra -join ', ') (keys: Id, Fragment, Agent, Anchor)" }
        $hasFragment = $rule.ContainsKey('Fragment')
        $hasAgent = $rule.ContainsKey('Agent')
        if ($hasFragment -eq $hasAgent) { "Method.Rules '$id' names exactly one of Fragment or Agent"; continue }
        if ($hasFragment -and ($rule['Fragment'] -isnot [string] -or -not $script:FragmentIdRegex.IsMatch($rule['Fragment']))) { "Method.Rules '$id': Fragment '$($rule['Fragment'])' is not a fragment id" }
        if ($hasAgent -and $rule['Agent'] -isnot [string]) { "Method.Rules '$id': Agent must be an agent id" }
        if ($hasAgent -and -not $rule.ContainsKey('Anchor')) { "Method.Rules '$id': a rule in role text needs an Anchor (the first line of its block)" }
        if ($rule.ContainsKey('Anchor') -and ($rule['Anchor'] -isnot [string] -or [string]::IsNullOrWhiteSpace($rule['Anchor']))) { "Method.Rules '$id': Anchor must be a whole source line" }
    }
}

# ---------------------------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------------------------

function Read-AgentSourceFile {
    <#
    .SYNOPSIS
        Reads a template or fragment as strict UTF-8 and returns its content lines.
    .DESCRIPTION
        Returns @{ Path; Exists; Lines; LineCount; Errors }. Lines holds @{ Text; Line } for every
        line that is not a "%% " comment. Errors cover: invalid UTF-8, BOM, CR, tab, trailing
        whitespace, missing final newline, empty file, and a blank first or last content line.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$RelativePath
    )
    $full = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $RelativePath
    $errors = [System.Collections.Generic.List[object]]::new()
    $lines = [System.Collections.Generic.List[object]]::new()
    if (-not [System.IO.File]::Exists($full)) {
        $errors.Add((New-AgentComposeError $RelativePath 0 'file not found'))
        return @{ Path = $RelativePath; Exists = $false; Lines = @(); LineCount = 0; Errors = $errors.ToArray() }
    }
    $bytes = [System.IO.File]::ReadAllBytes($full)
    $pos = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $errors.Add((New-AgentComposeError $RelativePath 1 'BOM (save as UTF-8 without BOM)'))
        $pos = 3
    }
    $lineNo = 0
    while ($pos -lt $bytes.Length) {
        $lf = [Array]::IndexOf($bytes, [byte]10, $pos)
        $end = if ($lf -lt 0) { $bytes.Length } else { $lf }
        $lineNo++
        $text = ''
        try {
            $text = $script:StrictUtf8.GetString($bytes, $pos, $end - $pos)
        }
        catch {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'invalid UTF-8'))
            $text = $script:LenientUtf8.GetString($bytes, $pos, $end - $pos)
        }
        if ($text.EndsWith("`r", [StringComparison]::Ordinal)) {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'CR line ending (use LF)'))
            $text = $text.Substring(0, $text.Length - 1)
        }
        if ($text.Contains("`r")) {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'CR character'))
            $text = $text.Replace("`r", '')
        }
        if ($text.Contains("`t")) {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'tab character (use spaces)'))
        }
        if ($text.Length -gt 0 -and [char]::IsWhiteSpace($text[$text.Length - 1])) {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'trailing whitespace'))
        }
        if ($lf -lt 0) {
            $errors.Add((New-AgentComposeError $RelativePath $lineNo 'missing final newline'))
            $pos = $bytes.Length
        }
        else {
            $pos = $lf + 1
        }
        if (Test-AgentCommentLine $text) { continue }
        $lines.Add(@{ Text = $text; Line = $lineNo })
    }
    if ($lines.Count -eq 0) {
        $errors.Add((New-AgentComposeError $RelativePath 1 'no content (empty file or comments only)'))
    }
    else {
        if ($lines[0]['Text'].Length -eq 0) {
            $errors.Add((New-AgentComposeError $RelativePath $lines[0]['Line'] 'file starts with a blank line'))
        }
        $last = $lines[$lines.Count - 1]
        if ($last['Text'].Length -eq 0) {
            $errors.Add((New-AgentComposeError $RelativePath $last['Line'] 'file ends with a blank line'))
        }
    }
    @{ Path = $RelativePath; Exists = $true; Lines = $lines.ToArray(); LineCount = $lineNo; Errors = $errors.ToArray() }
}

# ---------------------------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------------------------

function New-AgentComposeCache {
    param([string]$RepoRoot)
    $fragmentIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($id in @(Get-AgentFragmentIds -RepoRoot $RepoRoot)) { [void]$fragmentIds.Add($id) }
    $templateIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($id in @(Get-AgentTemplateIds -RepoRoot $RepoRoot)) { [void]$templateIds.Add($id) }
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $readmeFragmentIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($id in @(Get-AgentMarkdownBaseNames -Directory (Join-AgentRepoPath $root $script:ReadmeFragmentsRelDir))) { [void]$readmeFragmentIds.Add($id) }
    $readmeIds = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($id in @(Get-AgentMarkdownBaseNames -Directory (Join-AgentRepoPath $root $script:ReadmesRelDir))) { [void]$readmeIds.Add($id) }
    @{
        Sources = [System.Collections.Generic.Dictionary[string, object]]::new([StringComparer]::Ordinal)
        FragmentIds = $fragmentIds
        TemplateIds = $templateIds
        ReadmeFragmentIds = $readmeFragmentIds
        ReadmeIds = $readmeIds
        HasReadmes = [System.IO.Directory]::Exists((Join-AgentRepoPath $root $script:ReadmesRelDir))
    }
}

function Get-AgentCachedSource {
    param([hashtable]$State, [string]$RelativePath)
    $sources = $State['Cache']['Sources']
    if (-not $sources.ContainsKey($RelativePath)) {
        $sources[$RelativePath] = Read-AgentSourceFile -RepoRoot $State['Root'] -RelativePath $RelativePath
    }
    $sources[$RelativePath]
}

function Expand-AgentValues {
    param([hashtable]$State, [string]$Text, [string]$Path, [int]$Line)
    $found = $script:ValueRegex.Matches($Text)
    if ($found.Count -eq 0) { return $Text }
    $sb = [System.Text.StringBuilder]::new()
    $pos = 0
    foreach ($match in $found) {
        [void]$sb.Append($Text, $pos, $match.Index - $pos)
        $key = $match.Groups['key'].Value
        $value = $null
        if ($State['ValueMap'].TryGetValue($key, [ref]$value)) {
            [void]$sb.Append($value)
        }
        else {
            $known = [string[]]@($State['ValueMap'].Keys)
            [Array]::Sort($known, [StringComparer]::Ordinal)
            $State['Errors'].Add((New-AgentComposeError $Path $Line ("unknown value $key (family Values: " + ($known -join ', ') + ')')))
        }
        $pos = $match.Index + $match.Length
    }
    [void]$sb.Append($Text, $pos, $Text.Length - $pos)
    $sb.ToString()
}

function Expand-AgentSource {
    param([hashtable]$State, [string]$RelativePath, [string[]]$Stack = @())
    $source = Get-AgentCachedSource -State $State -RelativePath $RelativePath
    foreach ($e in $source['Errors']) { $State['Errors'].Add($e) }
    $kind = if ($State.ContainsKey('Kind')) { [string]$State['Kind'] } else { 'soul' }
    # -Omit (control arms): the lines of a block rule in this source, and the include lines of omitted fragments.
    $dropLines = $null
    $dropRecord = $null
    if ($State.ContainsKey('OmitLines') -and $State['OmitLines'].ContainsKey($RelativePath)) {
        $dropLines = $State['OmitLines'][$RelativePath]['Lines']
        $dropRecord = $State['OmitLines'][$RelativePath]['Record']
    }
    foreach ($entry in $source['Lines']) {
        $text = [string]$entry['Text']
        $lineNo = [int]$entry['Line']
        if ($null -ne $dropLines -and $dropLines.Contains($lineNo)) {
            $dropRecord['Hit'] = $true
            $dropRecord['Lines']++
            $dropRecord['Bytes'] += $script:LenientUtf8.GetByteCount((Expand-AgentValues -State $State -Text $text -Path $RelativePath -Line $lineNo)) + 1
            continue
        }
        $include = $script:IncludeRegex.Match($text)
        if (-not $include.Success) {
            if ($kind -eq 'readme') {
                $directive = $script:DirectiveRegex.Match($text)
                if ($directive.Success) {
                    foreach ($generated in @(Get-AgentReadmeBlock -State $State -Name $directive.Groups['name'].Value -Path $RelativePath -Line $lineNo)) {
                        $State['Lines'].Add([string]$generated)
                        $State['Map'].Add(@{ Source = $RelativePath; Line = $lineNo })
                    }
                    continue
                }
                $figure = $script:TokenFigureRegex.Match($text)
                if ($figure.Success) {
                    $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "hand-written token figure '$($figure.Value)'; write {{= SoulTokens}} (now $($State['ValueMap']['SoulTokens'])) or {{= SoulTokensDelta}} (now $(if ($State['ValueMap'].ContainsKey('SoulTokensDelta')) { $State['ValueMap']['SoulTokensDelta'] } else { 'undefined' })) so the figure follows the composed SOUL"))
                }
            }
            $State['Lines'].Add((Expand-AgentValues -State $State -Text $text -Path $RelativePath -Line $lineNo))
            $State['Map'].Add(@{ Source = $RelativePath; Line = $lineNo })
            continue
        }
        $ref = $include.Groups['ref'].Value
        $refMatch = $script:KindRefRegex.Match($ref)
        if (-not $refMatch.Success) {
            $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "bad include '$ref' (expected $kind/<NN-id>)"))
            continue
        }
        if (-not (Test-AgentSame $refMatch.Groups['kind'].Value $kind)) {
            $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "cross-kind include '$ref': a $kind source may include only $kind/<NN-id> fragments"))
            continue
        }
        $fragmentId = $refMatch.Groups['id'].Value
        $fragmentDir = if ($kind -eq 'readme') { $script:ReadmeFragmentsRelDir } else { $script:FragmentsRelDir }
        $knownIds = if ($kind -eq 'readme') { $State['Cache']['ReadmeFragmentIds'] } else { $State['Cache']['FragmentIds'] }
        $fragmentRel = "$fragmentDir/$fragmentId.md"
        if ($kind -eq 'soul' -and $State.ContainsKey('OmitFragments') -and $State['OmitFragments'].ContainsKey($fragmentId) -and $State['Cache']['FragmentIds'].Contains($fragmentId)) {
            # Measure what the include would have added, in a scratch state, then drop the include line.
            $record = $State['OmitFragments'][$fragmentId]
            $scratch = @{
                Root = $State['Root']; Id = $State['Id']; Cache = $State['Cache']; ValueMap = $State['ValueMap']
                Errors = [System.Collections.Generic.List[object]]::new()
                Lines = [System.Collections.Generic.List[string]]::new()
                Map = [System.Collections.Generic.List[object]]::new()
                Included = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
                IncludedOrder = [System.Collections.Generic.List[string]]::new()
                TopLevel = [System.Collections.Generic.List[object]]::new()
            }
            Expand-AgentSource -State $scratch -RelativePath $fragmentRel -Stack ([string[]](@($Stack) + $fragmentId))
            $record['Hit'] = $true
            $record['From'] = $lineNo
            $record['To'] = $lineNo
            $record['Include'] = $RelativePath
            $record['Covers'] = [string[]](@($fragmentId) + @($scratch['IncludedOrder']))
            $record['Lines'] += $scratch['Lines'].Count
            foreach ($l in $scratch['Lines']) { $record['Bytes'] += $script:LenientUtf8.GetByteCount($l) + 1 }
            continue
        }
        if ($Stack.Count -eq 0) {
            $State['TopLevel'].Add(@{ Id = $fragmentId; Line = $lineNo })
        }
        if (-not $knownIds.Contains($fragmentId)) {
            $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "unknown fragment $fragmentId (no file $fragmentRel)"))
            continue
        }
        if (Test-AgentInList $Stack $fragmentId) {
            $chain = (@($Stack) + $fragmentId) -join ' -> '
            $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "include cycle $chain"))
            continue
        }
        if (-not $State['Included'].Add($fragmentId)) {
            $State['Errors'].Add((New-AgentComposeError $RelativePath $lineNo "double include $fragmentId (agent $($State['Id']) already includes it)"))
            continue
        }
        $State['IncludedOrder'].Add($fragmentId)
        Expand-AgentSource -State $State -RelativePath $fragmentRel -Stack ([string[]](@($Stack) + $fragmentId))
    }
}

function Initialize-AgentOmit {
    # Resolves -Omit ids for one composition (control arms). A fragment id (two digits first) or a whole-fragment
    # Method rule drops that include line; a block rule drops its lines from its source, and when a blank line
    # stands on both sides of the block, the one after it goes too. Sets State.OmitFragments and State.OmitLines
    # and returns one record per id: @{ Id; Rule; Source; From; To; Lines; Bytes; Hit }.
    param([hashtable]$State, [hashtable]$Family, [string[]]$Omit)
    $ids = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in @(Get-AgentItems $Omit)) {
        foreach ($part in ([string]$entry).Split(',')) { $name = $part.Trim(); if ($name -and -not $ids.Contains($name)) { $ids.Add($name) } }
    }
    if ($ids.Count -eq 0) { return }
    $State['OmitFragments'] = @{}
    $State['OmitLines'] = @{}
    $method = $Family['Method']
    $rules = @(if ($method -is [hashtable]) { @(Get-AgentItems $method['Rules']) | Where-Object { $_ -is [hashtable] } })
    $methodLine = Get-AgentFamilyLine -RepoRoot $State['Root'] -Key 'Method'
    foreach ($id in $ids) {
        $record = @{ Id = $id; Rule = ''; Source = ''; From = 0; To = 0; Lines = 0; Bytes = 0; Hit = $false; Include = ''; Covers = [string[]]@() }
        if ($script:FragmentIdRegex.IsMatch($id)) {
            $record['Source'] = "$($script:FragmentsRelDir)/$id.md"
            $State['OmitFragments'][$id] = $record
            $record
            continue
        }
        $rule = @($rules | Where-Object { Test-AgentSame $_['Id'] $id }) | Select-Object -First 1
        if ($null -eq $rule) {
            $State['Errors'].Add((New-AgentComposeError $script:FamilyRelPath $methodLine "-Omit $($id): not a fragment id (NN-name) and not a Method rule id of this family"))
            continue
        }
        $record['Rule'] = $id
        $path = Get-AgentMethodRuleSource -Rule $rule -SoulsDir $script:SoulsRelDir -FragmentsDir $script:FragmentsRelDir
        $record['Source'] = $path
        if (-not $rule.ContainsKey('Anchor')) {
            $State['OmitFragments'][[string]$rule['Fragment']] = $record
            $record
            continue
        }
        $source = Get-AgentCachedSource -State $State -RelativePath $path
        $lines = @($source['Lines'])
        $span = @(Get-AgentMethodSpans -Method @{ Rules = @($rule) } -SourceLines @{ $path = $lines }) | Select-Object -First 1
        if ($null -eq $span -or @($span['Errors']).Count -gt 0 -or $span['Start'] -le 0) {
            foreach ($e in @($span['Errors'])) { $State['Errors'].Add($e) }
            if ($null -eq $span -or @($span['Errors']).Count -eq 0) { $State['Errors'].Add((New-AgentComposeError $path 0 "-Omit $($id): the rule's block was not found")) }
            continue
        }
        $drop = [System.Collections.Generic.HashSet[int]]::new()
        $first = -1
        $last = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            $n = [int]$lines[$i]['Line']
            if ($n -ge $span['Start'] -and $n -le $span['End']) { [void]$drop.Add($n); if ($first -lt 0) { $first = $i }; $last = $i }
        }
        if ($first -gt 0 -and $last + 1 -lt $lines.Count -and $lines[$first - 1]['Text'].Length -eq 0 -and $lines[$last + 1]['Text'].Length -eq 0) {
            [void]$drop.Add([int]$lines[$last + 1]['Line'])
        }
        $record['From'] = $span['Start']
        $record['To'] = $span['End']
        $State['OmitLines'][$path] = @{ Lines = $drop; Record = $record }
        $record
    }
}

function Test-AgentIncludeOrder {
    param([hashtable]$State, [string]$TemplateRel, [string[]]$Listed, [int]$TemplateLineCount)
    $root = $State['Root']
    $id = $State['Id']
    $p = $script:FamilyRelPath
    $top = @($State['TopLevel'])
    $topIds = [string[]]@(foreach ($t in $top) { $t['Id'] })
    $known = $State['Cache']['FragmentIds']

    foreach ($fragmentId in $Listed) {
        if (-not $known.Contains($fragmentId) -and -not (Test-AgentInList $topIds $fragmentId)) {
            $line = Get-AgentFamilyLine -RepoRoot $root -AgentId $id -Text $fragmentId
            $State['Errors'].Add((New-AgentComposeError $p $line "unknown fragment $fragmentId (listed for $id; no file $($script:FragmentsRelDir)/$fragmentId.md)"))
        }
    }
    foreach ($t in $top) {
        if (-not (Test-AgentInList $Listed $t['Id'])) {
            $State['Errors'].Add((New-AgentComposeError $TemplateRel $t['Line'] "fragment $($t['Id']) is not in the family Fragments list for $id (add it to family.psd1 or remove the include)"))
        }
    }
    for ($i = 0; $i -lt $Listed.Count; $i++) {
        $fragmentId = $Listed[$i]
        if (Test-AgentInList $topIds $fragmentId) { continue }
        $line = $TemplateLineCount
        foreach ($t in $top) {
            if ([Array]::IndexOf($Listed, [string]$t['Id']) -gt $i) { $line = $t['Line']; break }
        }
        $State['Errors'].Add((New-AgentComposeError $TemplateRel $line "missing fragment $fragmentId (listed in the family Fragments for $id; add its include line to the template)"))
    }

    $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $templateOrder = [System.Collections.Generic.List[object]]::new()
    foreach ($t in $top) {
        if ((Test-AgentInList $Listed $t['Id']) -and $seen.Add($t['Id'])) { $templateOrder.Add($t) }
    }
    $seen.Clear()
    $familyOrder = [System.Collections.Generic.List[string]]::new()
    foreach ($fragmentId in $Listed) {
        if ((Test-AgentInList $topIds $fragmentId) -and $seen.Add($fragmentId)) { $familyOrder.Add($fragmentId) }
    }
    $count = [Math]::Min($templateOrder.Count, $familyOrder.Count)
    for ($i = 0; $i -lt $count; $i++) {
        if (-not (Test-AgentSame $templateOrder[$i]['Id'] $familyOrder[$i])) {
            $State['Errors'].Add((New-AgentComposeError $TemplateRel $templateOrder[$i]['Line'] "fragment out of order $($templateOrder[$i]['Id']) (the family Fragments order for $id expects $($familyOrder[$i]) here)"))
            break
        }
    }
}

function Test-AgentComposedOutput {
    # The composer's output rules. A README (-Readme) keeps them all except the '## Output' rule.
    param([hashtable]$State, [string]$TemplateRel, [string]$DisplayName, [int]$TemplateLineCount, [switch]$Readme)
    $lines = $State['Lines']
    $map = $State['Map']
    if ($lines.Count -eq 0) { return }

    $expected = "# $DisplayName"
    if (-not (Test-AgentSame $lines[0] $expected)) {
        $State['Errors'].Add((New-AgentComposeError $map[0]['Source'] $map[0]['Line'] "first line must be '$expected'"))
    }

    $outputLine = 0
    for ($i = 0; $i -lt $lines.Count -and -not $Readme; $i++) {
        if ((Test-AgentSame $lines[$i] '## Output') -and (Test-AgentSame $map[$i]['Source'] $TemplateRel)) {
            $outputLine = [int]$map[$i]['Line']
        }
    }
    if ($Readme) { }
    elseif ($outputLine -eq 0) {
        $State['Errors'].Add((New-AgentComposeError $TemplateRel $TemplateLineCount "missing '## Output' section (the role output section is always last)"))
    }
    else {
        foreach ($t in @($State['TopLevel'])) {
            if ($t['Line'] -gt $outputLine) {
                $State['Errors'].Add((New-AgentComposeError $TemplateRel $t['Line'] "include of $($t['Id']) after '## Output' (the role output section is always last)"))
            }
        }
    }

    $blankRun = 0
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $text = $lines[$i]
        $source = $map[$i]['Source']
        $line = $map[$i]['Line']
        if ($text.Length -eq 0) {
            $blankRun++
            if ($blankRun -eq 3) {
                $State['Errors'].Add((New-AgentComposeError $source $line 'output has 3 or more consecutive blank lines'))
            }
        }
        else {
            $blankRun = 0
        }
        if ($text.Contains('{{')) {
            $State['Errors'].Add((New-AgentComposeError $source $line 'stray {{ (only an include line or a {{= Key}} value may use it)'))
        }
        if (Test-AgentCommentLine $text) {
            $State['Errors'].Add((New-AgentComposeError $source $line "comment marker '%% ' in output"))
        }
        if ($text.Contains('<!--')) {
            $State['Errors'].Add((New-AgentComposeError $source $line 'HTML comment (<!--) is forbidden; use a %% comment line'))
        }
    }
}

function Invoke-AgentCompose {
    <#
    .SYNOPSIS
        Composes one agent's SOUL text from its template and the shared fragments.
    .DESCRIPTION
        Returns @{ Id; DisplayName; SoulCap; RoleBytes; RoleCap; Template; Text; Bytes; LineMap; Errors; Fragments;
        Included }. RoleBytes is the role text: the bytes of the template's own output lines (include and comment
        lines excluded, values substituted, one LF each); RoleCap is the agent's optional RoleCap (0 when absent).
        Text is LF-only with exactly one trailing newline ('' when nothing composed).
        LineMap has one @{ Source; Line } per output line (Source is repo-relative).
        Fragments is the template's top-level include order; Included is every fragment
        included, nested ones too, in expansion order. Errors is empty when the text is usable.
        Pass -Family and -Cache when composing several agents (Invoke-AgentFamilyCompose does).
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$Id,
        [hashtable]$Family,
        [hashtable]$Cache,
        [string[]]$Omit = @()
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    if ($null -eq $Family) { $Family = Get-AgentFamily -RepoRoot $root }
    if ($null -eq $Cache) { $Cache = New-AgentComposeCache -RepoRoot $root }

    $valueMap = [System.Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
    $familyValues = $Family['Values']
    if ($familyValues -is [hashtable]) {
        foreach ($key in @($familyValues.Keys)) {
            if ($familyValues[$key] -is [string]) { $valueMap[[string]$key] = [string]$familyValues[$key] }
        }
    }
    $state = @{
        Root = $root
        Id = $Id
        Cache = $Cache
        ValueMap = $valueMap
        Errors = [System.Collections.Generic.List[object]]::new()
        Lines = [System.Collections.Generic.List[string]]::new()
        Map = [System.Collections.Generic.List[object]]::new()
        Included = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        IncludedOrder = [System.Collections.Generic.List[string]]::new()
        TopLevel = [System.Collections.Generic.List[object]]::new()
    }
    $omitRecords = @(Initialize-AgentOmit -State $state -Family $Family -Omit $Omit)

    $templateRel = "$($script:SoulsRelDir)/$Id.md"
    $displayName = ''
    $soulCap = 0
    $agent = Get-AgentFamilyAgent -Family $Family -Id $Id
    if ($null -eq $agent) {
        $state['Errors'].Add((New-AgentComposeError $script:FamilyRelPath (Get-AgentFamilyLine -RepoRoot $root -Key 'Agents') "unknown agent '$Id' (not in the roster)"))
    }
    else {
        if ($agent['DisplayName'] -is [string]) { $displayName = [string]$agent['DisplayName'] }
        if ($agent['SoulCap'] -is [int]) { $soulCap = [int]$agent['SoulCap'] }
        $listed = [string[]]@(foreach ($f in @(Get-AgentItems $agent['Fragments'])) { if (-not ($state.ContainsKey('OmitFragments') -and $state['OmitFragments'].ContainsKey([string]$f))) { [string]$f } })
        if (-not $Cache['TemplateIds'].Contains($Id)) {
            $line = Get-AgentFamilyLine -RepoRoot $root -AgentId $Id
            $state['Errors'].Add((New-AgentComposeError $script:FamilyRelPath $line "missing template $templateRel for agent $Id"))
        }
        else {
            Expand-AgentSource -State $state -RelativePath $templateRel
            $templateLineCount = [int]$Cache['Sources'][$templateRel]['LineCount']
            Test-AgentIncludeOrder -State $state -TemplateRel $templateRel -Listed $listed -TemplateLineCount $templateLineCount
            Test-AgentComposedOutput -State $state -TemplateRel $templateRel -DisplayName $displayName -TemplateLineCount $templateLineCount
            foreach ($record in $omitRecords) {
                if (-not $record['Hit']) {
                    $state['Errors'].Add((New-AgentComposeError $script:FamilyRelPath (Get-AgentFamilyLine -RepoRoot $root -AgentId $Id) "-Omit $($record['Id']): agent $Id does not carry it ($($record['Source'])); a control arm equal to the treatment proves nothing"))
                }
            }
        }
    }

    $text = ''
    if ($state['Lines'].Count -gt 0) { $text = ($state['Lines'] -join "`n") + "`n" }
    $topIds = [string[]]@(foreach ($t in $state['TopLevel']) { [string]$t['Id'] })
    # Role text: the template's own output lines (no include lines, no %% comments), values substituted.
    $roleBytes = 0
    for ($i = 0; $i -lt $state['Lines'].Count; $i++) {
        if (Test-AgentSame $state['Map'][$i]['Source'] $templateRel) { $roleBytes += $script:LenientUtf8.GetByteCount($state['Lines'][$i]) + 1 }
    }
    $roleCap = 0
    if ($null -ne $agent -and $agent['RoleCap'] -is [int]) { $roleCap = [int]$agent['RoleCap'] }
    @{
        Id = $Id
        Kind = 'soul'
        File = 'SOUL.md'
        DisplayName = $displayName
        SoulCap = $soulCap
        RoleBytes = $roleBytes
        RoleCap = $roleCap
        Template = $templateRel
        Text = $text
        Bytes = $script:LenientUtf8.GetByteCount($text)
        LineMap = $state['Map'].ToArray()
        Errors = $state['Errors'].ToArray()
        Fragments = $topIds
        Included = $state['IncludedOrder'].ToArray()
        Omitted = [object[]]@($omitRecords | Where-Object { $_['Hit'] })
    }
}

function Get-AgentReadmeLicense {
    param([hashtable]$Family, [hashtable]$Agent)
    if ($null -ne $Agent -and $Agent['License'] -is [string]) { return [string]$Agent['License'] }
    if ($Family['License'] -is [string]) { return [string]$Family['License'] }
    'MIT'
}

function Get-AgentReadmeBlock {
    # The lines of a generated README block: {{# roster}} (the roster table from RosterOrder and the agents' Summary,
    # Changes and Commits; Delegates from SubAgents; the composing agent's row in bold with "(this one)") or
    # {{# credits}} (one line per Credits entry of the agent, in list order, then a blank line and the licence
    # sentence).
    param([hashtable]$State, [string]$Name, [string]$Path, [int]$Line)
    $family = $State['Family']
    $self = $State['Agent']
    switch ($Name) {
        'roster' {
            $order = @(if ($family['RosterOrder'] -is [array]) { $family['RosterOrder'] })
            if ($order.Count -eq 0) {
                $State['Errors'].Add((New-AgentComposeError $Path $Line '{{# roster}} needs the family key RosterOrder'))
                return
            }
            '| Agent | Role | Delegates | Changes files | Commits |'
            '|---|---|---|---|---|'
            foreach ($id in $order) {
                $agent = Get-AgentFamilyAgent -Family $family -Id ([string]$id)
                if ($null -eq $agent) { $State['Errors'].Add((New-AgentComposeError $Path $Line "{{# roster}}: RosterOrder names '$id', which is not in the roster")); continue }
                $missing = @(@('Summary', 'Changes', 'Commits') | Where-Object { $agent[$_] -isnot [string] -or $agent[$_].Length -eq 0 })
                if ($missing.Count -gt 0) {
                    $State['Errors'].Add((New-AgentComposeError $Path $Line "{{# roster}}: agent '$id' has no $($missing -join ', ') (the roster-table cells)"))
                    continue
                }
                $sub = $agent['SubAgents']
                $delegates = if ($sub -is [hashtable] -and $sub['enabled'] -eq $true) { "yes (depth $($sub['maxDepth']))" } else { 'no' }
                $cell = if (Test-AgentSame $id $State['Id']) { "**$id** (this one)" } else { [string]$id }
                "| $cell | $($agent['Summary']) | $delegates | $($agent['Changes']) | $($agent['Commits']) |"
            }
        }
        'credits' {
            $credits = $family['Credits']
            $keys = @(Get-AgentItems $self['Credits'])
            foreach ($key in $keys) {
                if ($credits -isnot [hashtable] -or -not $credits.ContainsKey([string]$key)) {
                    $State['Errors'].Add((New-AgentComposeError $Path $Line "{{# credits}}: credit '$key' is not a key of the family Credits"))
                    continue
                }
                [string]$credits[[string]$key]
            }
            if ($keys.Count -gt 0) { '' }
            "Licensed under the $(Get-AgentReadmeLicense -Family $family -Agent $self) License; see LICENSE."
        }
        default {
            $State['Errors'].Add((New-AgentComposeError $Path $Line "unknown README block '{{# $Name}}' (blocks: roster, credits)"))
        }
    }
}

function Format-AgentTokenFigure {
    # Bytes / 3.8 rounded to the nearest hundred, with a thousands separator.
    param([int]$Bytes)
    $hundreds = [Math]::Round($Bytes / $script:BytesPerToken / 100.0, [MidpointRounding]::AwayFromZero)
    ([int]($hundreds * 100)).ToString('N0', [System.Globalization.CultureInfo]::InvariantCulture)
}

function Invoke-AgentReadmeCompose {
    <#
    .SYNOPSIS
        Composes one agent's README.md from <dir>/readmes/<id>.md and the shared <dir>/fragments/readme/ blocks.
    .DESCRIPTION
        Includes are {{> readme/<NN-id>}} (a README source may include only README fragments). Values are the
        family Values plus FamilyVersion, Id, DisplayName, License, SoulTokens (the composed SOUL bytes / 3.8,
        to the nearest hundred) and SoulTokensDelta (the same for the growth against the baseline, defined only
        when the agent has a baseline entry and it rounds to at least 100). {{# roster}} and {{# credits}} lines
        are generated blocks. A digit before "tokens" is an error. The output keeps the composer's rules except
        '## Output'. Returns the shape of Invoke-AgentCompose with Kind 'readme' and File 'README.md'.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)][hashtable]$Family,
        [Parameter(Mandatory)][hashtable]$Cache,
        [hashtable]$SoulResult,
        [AllowNull()]$BaselineBytes
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $agent = Get-AgentFamilyAgent -Family $Family -Id $Id
    $valueMap = [System.Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
    if ($Family['Values'] -is [hashtable]) {
        foreach ($key in @($Family['Values'].Keys)) { if ($Family['Values'][$key] -is [string]) { $valueMap[[string]$key] = [string]$Family['Values'][$key] } }
    }
    if ($Family['FamilyVersion'] -is [string]) { $valueMap['FamilyVersion'] = [string]$Family['FamilyVersion'] }
    $valueMap['Id'] = $Id
    $displayName = if ($null -ne $agent -and $agent['DisplayName'] -is [string]) { [string]$agent['DisplayName'] } else { '' }
    $valueMap['DisplayName'] = $displayName
    $valueMap['License'] = Get-AgentReadmeLicense -Family $Family -Agent $agent
    if ($null -ne $SoulResult) {
        $soulBytes = [int]$SoulResult['Bytes']
        $valueMap['SoulTokens'] = Format-AgentTokenFigure -Bytes $soulBytes
        if ($null -ne $BaselineBytes) {
            $growth = $soulBytes - [int]$BaselineBytes
            $hundreds = [Math]::Round($growth / $script:BytesPerToken / 100.0, [MidpointRounding]::AwayFromZero)
            if ($hundreds -ge 1) { $valueMap['SoulTokensDelta'] = Format-AgentTokenFigure -Bytes $growth }
        }
    }
    $state = @{
        Root = $root; Id = $Id; Cache = $Cache; ValueMap = $valueMap; Kind = 'readme'; Family = $Family; Agent = $agent
        Errors = [System.Collections.Generic.List[object]]::new()
        Lines = [System.Collections.Generic.List[string]]::new()
        Map = [System.Collections.Generic.List[object]]::new()
        Included = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        IncludedOrder = [System.Collections.Generic.List[string]]::new()
        TopLevel = [System.Collections.Generic.List[object]]::new()
    }
    $templateRel = "$($script:ReadmesRelDir)/$Id.md"
    if ($null -eq $agent) {
        $state['Errors'].Add((New-AgentComposeError $script:FamilyRelPath (Get-AgentFamilyLine -RepoRoot $root -Key 'Agents') "unknown agent '$Id' (not in the roster)"))
    }
    elseif (-not $Cache['ReadmeIds'].Contains($Id)) {
        $state['Errors'].Add((New-AgentComposeError $script:FamilyRelPath (Get-AgentFamilyLine -RepoRoot $root -AgentId $Id) "agent $Id has no README source $templateRel (a family with a readmes/ folder composes every README)"))
    }
    else {
        Expand-AgentSource -State $state -RelativePath $templateRel
        $lineCount = [int]$Cache['Sources'][$templateRel]['LineCount']
        Test-AgentComposedOutput -State $state -TemplateRel $templateRel -DisplayName $displayName -TemplateLineCount $lineCount -Readme
    }
    $text = ''
    if ($state['Lines'].Count -gt 0) { $text = ($state['Lines'] -join "`n") + "`n" }
    @{
        Id = $Id
        Kind = 'readme'
        File = 'README.md'
        DisplayName = $displayName
        Template = $templateRel
        Text = $text
        Bytes = $script:LenientUtf8.GetByteCount($text)
        LineMap = $state['Map'].ToArray()
        Errors = $state['Errors'].ToArray()
        Fragments = [string[]]@(foreach ($top in $state['TopLevel']) { [string]$top['Id'] })
        Included = $state['IncludedOrder'].ToArray()
    }
}

function Invoke-AgentFamilyCompose {
    <#
    .SYNOPSIS
        Composes every roster agent (or the -Agents selection) and runs the family-wide checks.
    .DESCRIPTION
        Returns @{ Family; Agents; FullRoster; Results; ReadmeResults; Errors; AllErrors }.
        Results holds one Invoke-AgentCompose result per selected agent, in ordinal order; ReadmeResults one
        Invoke-AgentReadmeCompose result per selected agent when the family has a readmes/ folder (else none).
        Errors holds family-wide errors: schema, unknown -Agents ids, templates without a roster
        entry and (full roster only) fragments no agent includes. AllErrors is Errors plus every
        agent's errors, de-duplicated, in a stable order.
        -Agents entries may be comma-separated lists.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string[]]$Agents = @(),
        [hashtable]$Family,
        [string[]]$Omit = @()
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    if ($null -eq $Family) { $Family = Get-AgentFamily -RepoRoot $root }
    $errors = [System.Collections.Generic.List[object]]::new()
    foreach ($e in @(Test-AgentFamilyData -RepoRoot $root -Family $Family)) { $errors.Add($e) }

    $roster = [System.Collections.Generic.List[string]]::new()
    foreach ($agent in @(Get-AgentItems $Family['Agents'])) {
        $agentId = Get-AgentIdOf $agent
        if ($agentId -and -not $roster.Contains($agentId)) { $roster.Add($agentId) }
    }

    $requested = [System.Collections.Generic.List[string]]::new()
    foreach ($entry in @(Get-AgentItems $Agents)) {
        foreach ($part in ([string]$entry).Split(',')) {
            $name = $part.Trim()
            if ($name -and -not $requested.Contains($name)) { $requested.Add($name) }
        }
    }
    $selected = [System.Collections.Generic.List[string]]::new()
    if ($requested.Count -eq 0) {
        $selected.AddRange($roster)
    }
    else {
        foreach ($name in $requested) {
            if (-not $roster.Contains($name)) {
                $errors.Add((New-AgentComposeError $script:FamilyRelPath (Get-AgentFamilyLine -RepoRoot $root -Key 'Agents') "unknown agent '$name' (not in the roster)"))
            }
        }
        foreach ($agentId in $roster) {
            if ($requested.Contains($agentId)) { $selected.Add($agentId) }
        }
    }

    $cache = New-AgentComposeCache -RepoRoot $root
    $templateIds = [string[]]@($cache['TemplateIds'])
    [Array]::Sort($templateIds, [StringComparer]::Ordinal)
    foreach ($templateId in $templateIds) {
        if (-not $roster.Contains($templateId)) {
            $errors.Add((New-AgentComposeError "$($script:SoulsRelDir)/$templateId.md" 1 "template has no roster entry: $templateId (add it to Agents in family.psd1 or delete the template)"))
        }
    }

    $results = [System.Collections.Generic.List[object]]::new()
    foreach ($agentId in $selected) {
        $results.Add((Invoke-AgentCompose -RepoRoot $root -Id $agentId -Family $Family -Cache $cache -Omit $Omit))
    }

    $fullRoster = ($roster.Count -gt 0 -and $selected.Count -eq $roster.Count)
    if ($fullRoster) {
        $used = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($result in $results) {
            foreach ($fragmentId in $result['Included']) { [void]$used.Add($fragmentId) }
            # A fragment left out by -Omit still counts as used.
            foreach ($record in @($result['Omitted'])) { foreach ($fragmentId in @($record['Covers'])) { [void]$used.Add([string]$fragmentId) } }
        }
        $fragmentIds = [string[]]@($cache['FragmentIds'])
        [Array]::Sort($fragmentIds, [StringComparer]::Ordinal)
        foreach ($fragmentId in $fragmentIds) {
            if (-not $used.Contains($fragmentId)) {
                $errors.Add((New-AgentComposeError "$($script:FragmentsRelDir)/$fragmentId.md" 1 "unused fragment $fragmentId (no agent includes it)"))
            }
        }
    }

    # READMEs: composed after the SOULs, from their bytes in memory, when the family has a readmes/ folder.
    $readmeResults = [System.Collections.Generic.List[object]]::new()
    if ($cache['HasReadmes']) {
        $baseline = Get-AgentSoulBaseline -RepoRoot $root
        foreach ($e in @($baseline['Errors'])) { $errors.Add($e) }
        foreach ($result in $results) {
            $base = 0
            $baseValue = if ($baseline['Souls'].TryGetValue([string]$result['Id'], [ref]$base)) { $base } else { $null }
            $readmeResults.Add((Invoke-AgentReadmeCompose -RepoRoot $root -Id ([string]$result['Id']) -Family $Family -Cache $cache -SoulResult $result -BaselineBytes $baseValue))
        }
        $readmeIds = [string[]]@($cache['ReadmeIds'])
        [Array]::Sort($readmeIds, [StringComparer]::Ordinal)
        foreach ($readmeId in $readmeIds) {
            if (-not $roster.Contains($readmeId)) {
                $errors.Add((New-AgentComposeError "$($script:ReadmesRelDir)/$readmeId.md" 1 "README source has no roster entry: $readmeId (add it to Agents in family.psd1 or delete the source)"))
            }
        }
        if ($fullRoster) {
            $usedReadme = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
            foreach ($result in $readmeResults) { foreach ($fragmentId in $result['Included']) { [void]$usedReadme.Add($fragmentId) } }
            $readmeFragmentIds = [string[]]@($cache['ReadmeFragmentIds'])
            [Array]::Sort($readmeFragmentIds, [StringComparer]::Ordinal)
            foreach ($fragmentId in $readmeFragmentIds) {
                if (-not $usedReadme.Contains($fragmentId)) {
                    $errors.Add((New-AgentComposeError "$($script:ReadmeFragmentsRelDir)/$fragmentId.md" 1 "unused README fragment $fragmentId (no README source includes it)"))
                }
            }
        }
    }

    $all = [System.Collections.Generic.List[object]]::new()
    $keys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $ordered = [System.Collections.Generic.List[object]]::new()
    foreach ($e in $errors) { $ordered.Add($e) }
    foreach ($result in $results) { foreach ($e in $result['Errors']) { $ordered.Add($e) } }
    foreach ($result in $readmeResults) { foreach ($e in $result['Errors']) { $ordered.Add($e) } }
    foreach ($e in $ordered) {
        if ($keys.Add((Format-AgentComposeError -Item $e))) { $all.Add($e) }
    }

    @{
        Family = $Family
        Agents = $selected.ToArray()
        FullRoster = $fullRoster
        Results = $results.ToArray()
        ReadmeResults = $readmeResults.ToArray()
        Errors = $errors.ToArray()
        AllErrors = $all.ToArray()
    }
}

# ---------------------------------------------------------------------------------------------
# Method registry (the optional family key Method; docs/plans/2026-11-23-agents-v3-design.md,
# "The Method registry")
# ---------------------------------------------------------------------------------------------

$script:ExcuseHeader = '| Excuse | Reality |'
$script:ExcuseRule = '|---|---|'
$script:ReferenceFallback = 'If the tool is missing or refused, work from what you carry.'

function Get-AgentMethodRuleSource {
    # The repo-relative source file of a rule: its fragment, or the agent's template.
    param([hashtable]$Rule, [string]$SoulsDir, [string]$FragmentsDir)
    if ($Rule.ContainsKey('Fragment')) { return "$FragmentsDir/$($Rule['Fragment']).md" }
    "$SoulsDir/$($Rule['Agent']).md"
}

function Get-AgentMethodSpans {
    <#
    .SYNOPSIS
        Locates every Method rule in its source. Emits @{ Rule; Path; Whole; Start; End; Errors } per rule.
    .DESCRIPTION
        SourceLines maps a repo-relative source path to its content lines (@{ Text; Line }, as Read-AgentSourceFile
        returns them). A whole-fragment rule (Fragment, no Anchor) spans its fragment file. A block rule (Anchor
        with Fragment or Agent) starts at the one line equal to Anchor and ends with the last row of the first
        excuse table at or after it. Start and End are 1-based source line numbers (0 when the span is not
        found); Errors holds error objects (METHOD-EXCUSES).
    #>
    [CmdletBinding()]
    param(
        [AllowNull()]$Method,
        [Parameter(Mandatory)][hashtable]$SourceLines,
        [string]$SoulsDir = $script:SoulsRelDir,
        [string]$FragmentsDir = $script:FragmentsRelDir
    )
    if ($Method -isnot [hashtable]) { return }
    foreach ($rule in @(Get-AgentItems $Method['Rules'])) {
        if ($rule -isnot [hashtable] -or $rule['Id'] -isnot [string]) { continue }
        $path = Get-AgentMethodRuleSource -Rule $rule -SoulsDir $SoulsDir -FragmentsDir $FragmentsDir
        $errors = [System.Collections.Generic.List[object]]::new()
        $span = @{ Rule = [string]$rule['Id']; Path = $path; Whole = $false; Start = 0; End = 0; Errors = $errors }
        if (-not $SourceLines.ContainsKey($path)) {
            $errors.Add((New-AgentComposeError $path 0 "rule '$($rule['Id'])': source $path not found"))
            $span; continue
        }
        $lines = @($SourceLines[$path])
        if ($lines.Count -eq 0) { $span; continue }
        if (-not $rule.ContainsKey('Anchor')) {
            $span['Whole'] = $true
            $span['Start'] = [int]$lines[0]['Line']
            $span['End'] = [int]$lines[$lines.Count - 1]['Line']
            $span; continue
        }
        $anchor = [string]$rule['Anchor']
        $hits = @(for ($i = 0; $i -lt $lines.Count; $i++) { if (Test-AgentSame $lines[$i]['Text'] $anchor) { $i } })
        if ($hits.Count -ne 1) {
            $where = if ($hits.Count -eq 0) { 'matches no line' } else { "matches $($hits.Count) lines ($(@($hits | ForEach-Object { $lines[$_]['Line'] }) -join ', '))" }
            $errors.Add((New-AgentComposeError $path $(if ($hits.Count -gt 0) { [int]$lines[$hits[0]]['Line'] } else { 0 }) "rule '$($rule['Id'])': Anchor '$anchor' $where; it must match exactly one line"))
            $span; continue
        }
        $header = -1
        for ($i = $hits[0]; $i -lt $lines.Count; $i++) {
            if (Test-AgentSame $lines[$i]['Text'] $script:ExcuseHeader) { $header = $i; break }
        }
        if ($header -lt 0) {
            $errors.Add((New-AgentComposeError $path ([int]$lines[$hits[0]]['Line']) "rule '$($rule['Id'])': no excuse table ($($script:ExcuseHeader)) after its Anchor; a block ends with the last row of its table"))
            $span; continue
        }
        $end = $header
        while ($end + 1 -lt $lines.Count -and $lines[$end + 1]['Text'].StartsWith('|', [StringComparison]::Ordinal)) { $end++ }
        $span['Start'] = [int]$lines[$hits[0]]['Line']
        $span['End'] = [int]$lines[$end]['Line']
        $span
    }
}

function Test-AgentExcuseTables {
    # The table rule for one span: exactly one canonical excuse table, 3 to 6 rows, quoted excuse, full stop,
    # at most 200 B a row. Emits error objects.
    param([string]$RuleId, [string]$Path, [object[]]$Lines)
    $headers = @(for ($i = 0; $i -lt $Lines.Count; $i++) { if (Test-AgentSame $Lines[$i]['Text'] $script:ExcuseHeader) { $i } })
    $first = if ($Lines.Count -gt 0) { [int]$Lines[0]['Line'] } else { 0 }
    if ($headers.Count -ne 1) {
        New-AgentComposeError $Path $(if ($headers.Count -gt 1) { [int]$Lines[$headers[1]]['Line'] } else { $first }) "rule '$RuleId' holds $($headers.Count) excuse tables; a registered rule holds exactly one"
        return
    }
    $h = $headers[0]
    if ($h + 1 -ge $Lines.Count -or -not (Test-AgentSame $Lines[$h + 1]['Text'] $script:ExcuseRule)) {
        New-AgentComposeError $Path ([int]$Lines[$h]['Line']) "rule '$RuleId': the excuse table header must be followed by '$($script:ExcuseRule)'"
        return
    }
    $rows = [System.Collections.Generic.List[object]]::new()
    for ($i = $h + 2; $i -lt $Lines.Count -and $Lines[$i]['Text'].StartsWith('|', [StringComparison]::Ordinal); $i++) { $rows.Add($Lines[$i]) }
    if ($rows.Count -lt 3 -or $rows.Count -gt 6) {
        New-AgentComposeError $Path ([int]$Lines[$h]['Line']) "rule '$RuleId': the excuse table has $($rows.Count) rows; it needs 3 to 6"
    }
    foreach ($row in $rows) {
        $text = [string]$row['Text']
        $line = [int]$row['Line']
        $size = $script:LenientUtf8.GetByteCount($text)
        if ($size -gt 200) { New-AgentComposeError $Path $line "rule '$RuleId': excuse row is $size bytes; at most 200" }
        $cells = [regex]::Match($text, '^\|(?<a>[^|]*)\|(?<b>[^|]*)\|$')
        if (-not $cells.Success) { New-AgentComposeError $Path $line "rule '$RuleId': an excuse row has exactly two cells"; continue }
        $excuse = $cells.Groups['a'].Value.Trim()
        $reality = $cells.Groups['b'].Value.Trim()
        if ($excuse.Length -lt 2 -or -not $excuse.StartsWith('"', [StringComparison]::Ordinal) -or -not $excuse.EndsWith('"', [StringComparison]::Ordinal)) {
            New-AgentComposeError $Path $line "rule '$RuleId': the excuse cell must be in double quotes"
        }
        if (-not $reality.EndsWith('.', [StringComparison]::Ordinal)) {
            New-AgentComposeError $Path $line "rule '$RuleId': the reality cell must end with a full stop"
        }
    }
}

function Get-AgentComposedLines {
    # The composed output lines of a compose result (no trailing empty element).
    param([hashtable]$Result)
    $text = [string]$Result['Text']
    if ($text.Length -eq 0) { return , [string[]]@() }
    , [string[]](Split-AgentTextLines -Text $text)['Lines']
}

function Test-AgentMethod {
    <#
    .SYNOPSIS
        METHOD-CONTROLLER, METHOD-EXCUSES and METHOD-REFERENCE for one family. Emits @{ Rule; Path; Line; Message }.
    .DESCRIPTION
        Family is the family data; Results the compose results of the agents checked (Id, Text, LineMap,
        Included); SourceLines maps every template and fragment path of the family to its content lines.
        Negation is the tool lint's negation regex (Get-AgentNegationRegex in build/AgentLint.psm1). SkillTools
        maps a skill name to its tool names. FullRoster says Results covers the whole roster, which the
        "no roster agent carries this rule" check needs. Each check runs only when its data exists: the
        Method key for the first two, a SkillPolicy skill with a Fragment for the third. Findings are
        reported at the source line through the line map, once per line and rule.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Family,
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Results,
        [Parameter(Mandatory)][hashtable]$SourceLines,
        [Parameter(Mandatory)][regex]$Negation,
        [hashtable]$SkillTools = @{},
        [bool]$FullRoster = $true,
        [string]$SoulsDir = $script:SoulsRelDir,
        [string]$FragmentsDir = $script:FragmentsRelDir,
        [string]$FamilyPath = $script:FamilyRelPath,
        [string]$RepoRoot = ''
    )
    # Family-file lines need the repository (the fixtures have no family file: line 0).
    $lineOf = {
        param([string]$AgentId, [string]$Text, [string]$Key)
        if (-not $RepoRoot) { return 0 }
        $lineArgs = @{ RepoRoot = $RepoRoot }
        if ($AgentId) { $lineArgs['AgentId'] = $AgentId }
        if ($Text) { $lineArgs['Text'] = $Text }
        if ($Key) { $lineArgs['Key'] = $Key }
        Get-AgentFamilyLine @lineArgs
    }
    $found = [System.Collections.Generic.List[object]]::new()
    $keys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $add = {
        param([string]$Rule, [string]$Path, [int]$Line, [string]$Message, [string]$Key = '')
        $k = if ($Key) { "$Rule|$Key" } else { "$Rule|$Path|$Line|$Message" }
        if ($keys.Add($k)) { $found.Add(@{ Rule = $Rule; Path = $Path; Line = $Line; Message = $Message }) }
    }
    $fragmentOf = {
        param([string]$Source)
        $prefix = "$FragmentsDir/"
        if ($Source.StartsWith($prefix, [StringComparison]::Ordinal) -and $Source.EndsWith('.md', [StringComparison]::Ordinal)) {
            return $Source.Substring($prefix.Length, $Source.Length - $prefix.Length - 3)
        }
        ''
    }
    $agentsById = @{}
    foreach ($agent in @(Get-AgentItems $Family['Agents'])) { $id = Get-AgentIdOf $agent; if ($id) { $agentsById[$id] = $agent } }
    $method = $Family['Method']

    if ($method -is [hashtable]) {
        # ---- METHOD-CONTROLLER ----
        $controller = if ($method['Controller'] -is [hashtable]) { $method['Controller'] } else { @{} }
        $worker = if ($method['Worker'] -is [hashtable]) { $method['Worker'] } else { @{} }
        $controllerFragments = [string[]]@(Get-AgentItems $controller['Fragments'])
        $terms = @(foreach ($term in @(Get-AgentItems $controller['Terms'])) {
                if ($term -is [string] -and $term.Length -gt 0) { @{ Text = $term; Regex = [regex]::new($term, 'IgnoreCase, CultureInvariant') } }
            })
        $allow = @(Get-AgentItems $controller['Allow'] | Where-Object { $_ -is [hashtable] })
        $workerFragments = [string[]]@(Get-AgentItems $worker['Fragments'])
        $exempt = [string[]]@(Get-AgentItems $worker['Exempt'])
        foreach ($result in $Results) {
            $id = [string]$result['Id']
            $agent = $agentsById[$id]
            if ($null -eq $agent) { continue }
            $sub = $agent['SubAgents']
            $delegates = $sub -is [hashtable] -and $sub['enabled'] -eq $true
            if ($delegates -or (Test-AgentInList $exempt $id)) { continue }
            $included = [string[]]@($result['Included'])
            foreach ($fragmentId in $controllerFragments) {
                if (Test-AgentInList $included $fragmentId) {
                    & $add 'METHOD-CONTROLLER' $FamilyPath (& $lineOf -AgentId $id -Text $fragmentId) "worker '$id' includes the controller fragment $fragmentId (only an agent that delegates may include it)"
                }
            }
            foreach ($fragmentId in $workerFragments) {
                if (-not (Test-AgentInList $included $fragmentId)) {
                    & $add 'METHOD-CONTROLLER' $FamilyPath (& $lineOf -AgentId $id) "worker '$id' lacks the worker fragment $fragmentId (Method.Worker.Fragments)"
                }
            }
            if ($terms.Count -eq 0) { continue }
            $lines = Get-AgentComposedLines -Result $result
            $map = @($result['LineMap'])
            for ($i = 0; $i -lt $lines.Length -and $i -lt $map.Count; $i++) {
                $text = $lines[$i]
                if ($Negation.IsMatch($text)) { continue }
                $source = [string]$map[$i]['Source']
                $fromFragment = & $fragmentOf $source
                foreach ($term in $terms) {
                    if (-not $term['Regex'].IsMatch($text)) { continue }
                    $allowed = @($allow | Where-Object {
                            (Test-AgentSame $_['Term'] $term['Text']) -and
                            ((Test-AgentSame $_['Agent'] $id) -or ($fromFragment -and (Test-AgentSame $_['Fragment'] $fromFragment)))
                        }).Count -gt 0
                    if ($allowed) { continue }
                    $hit = $term['Regex'].Match($text).Value
                    & $add 'METHOD-CONTROLLER' $source ([int]$map[$i]['Line']) "controller term '$hit' ($($term['Text'])) in a worker's text without a negation on the line; reword it, negate it, or list it in Method.Controller.Allow" "$source|$($map[$i]['Line'])|$($term['Text'])"
                }
            }
        }

        # ---- METHOD-EXCUSES ----
        $spans = @(Get-AgentMethodSpans -Method $method -SourceLines $SourceLines -SoulsDir $SoulsDir -FragmentsDir $FragmentsDir)
        $covered = @{}
        foreach ($span in $spans) {
            foreach ($e in @($span['Errors'])) { & $add 'METHOD-EXCUSES' $e['Path'] $e['Line'] $e['Message'] }
            if ($span['Start'] -le 0) { continue }
            if (-not $covered.ContainsKey($span['Path'])) { $covered[$span['Path']] = [System.Collections.Generic.List[object]]::new() }
            $covered[$span['Path']].Add($span)
            $inSpan = @(@($SourceLines[$span['Path']]) | Where-Object { $_['Line'] -ge $span['Start'] -and $_['Line'] -le $span['End'] })
            foreach ($e in @(Test-AgentExcuseTables -RuleId $span['Rule'] -Path $span['Path'] -Lines $inSpan)) { & $add 'METHOD-EXCUSES' $e['Path'] $e['Line'] $e['Message'] }
        }
        foreach ($rule in @(Get-AgentItems $method['Rules'] | Where-Object { $_ -is [hashtable] })) {
            if ($rule.ContainsKey('Agent')) {
                if (-not $agentsById.ContainsKey([string]$rule['Agent'])) {
                    & $add 'METHOD-EXCUSES' $FamilyPath (& $lineOf -Key 'Method') "rule '$($rule['Id'])' names agent '$($rule['Agent'])', which is not in the roster"
                }
            }
            elseif ($FullRoster) {
                $carried = @($Results | Where-Object { Test-AgentInList ([string[]]@($_['Included'])) $rule['Fragment'] }).Count -gt 0
                if (-not $carried) {
                    & $add 'METHOD-EXCUSES' $FamilyPath (& $lineOf -Key 'Method') "rule '$($rule['Id'])': no roster agent includes $($rule['Fragment'])"
                }
            }
        }
        $paths = [string[]]@($SourceLines.Keys)
        [Array]::Sort($paths, [StringComparer]::Ordinal)
        foreach ($path in $paths) {
            foreach ($entry in @($SourceLines[$path])) {
                if (-not (Test-AgentSame $entry['Text'] $script:ExcuseHeader)) { continue }
                $line = [int]$entry['Line']
                $inside = $covered.ContainsKey($path) -and @($covered[$path] | Where-Object { $line -ge $_['Start'] -and $line -le $_['End'] }).Count -gt 0
                if (-not $inside) {
                    & $add 'METHOD-EXCUSES' $path $line 'an excuse table outside every registered rule (Method.Rules); register the rule or drop the table'
                }
            }
        }
    }

    # ---- METHOD-REFERENCE ----
    $policy = $Family['SkillPolicy']
    $referenceSkills = @(if ($policy -is [hashtable]) { @(Get-AgentItems $policy['Skills']) | Where-Object { $_ -is [hashtable] -and $_['Fragment'] -is [string] } })
    foreach ($skill in $referenceSkills) {
        $fragmentId = [string]$skill['Fragment']
        $fragmentPath = "$FragmentsDir/$fragmentId.md"
        if (-not $SourceLines.ContainsKey($fragmentPath)) {
            & $add 'METHOD-REFERENCE' $FamilyPath (& $lineOf -Key 'SkillPolicy') "SkillPolicy skill '$($skill['Name'])' names the fragment $fragmentId, which has no file $fragmentPath"
        }
        elseif (@(@($SourceLines[$fragmentPath]) | Where-Object { ([string]$_['Text']).Contains($script:ReferenceFallback) }).Count -eq 0) {
            & $add 'METHOD-REFERENCE' $fragmentPath 1 "the reference fragment must contain the sentence '$($script:ReferenceFallback)'"
        }
        $tools = [string[]]@(if ($SkillTools.ContainsKey([string]$skill['Name'])) { @($SkillTools[[string]$skill['Name']]) })
        if ($tools.Length -eq 0) { continue }
        $toolRegex = [regex]::new('(?<![\w./\\@:-])(?:' + (($tools | ForEach-Object { [regex]::Escape($_) }) -join '|') + ')(?![\w/\\(@-]|\.[A-Za-z0-9_])', 'CultureInvariant')
        foreach ($result in $Results) {
            $lines = Get-AgentComposedLines -Result $result
            $map = @($result['LineMap'])
            for ($i = 0; $i -lt $lines.Length -and $i -lt $map.Count; $i++) {
                $match = $toolRegex.Match($lines[$i])
                if (-not $match.Success) { continue }
                $source = [string]$map[$i]['Source']
                if (Test-AgentSame $source $fragmentPath) { continue }
                & $add 'METHOD-REFERENCE' $source ([int]$map[$i]['Line']) "the skill tool $($match.Value) may appear only in its reference fragment $fragmentId; point at a topic by id instead" "$source|$($map[$i]['Line'])|$($match.Value)"
            }
        }
    }
    $found.ToArray()
}

function Expand-AgentFixtureSource {
    # In-memory expansion for the method fixtures: include lines {{> soul/<id>}} are replaced by the fragment's
    # lines, recursively. Fills Lines, Map and Included of $State.
    param([hashtable]$State, [string]$Path, [string[]]$Stack = @())
    foreach ($entry in @($State['Sources'][$Path])) {
        $include = $script:IncludeRegex.Match([string]$entry['Text'])
        $ref = if ($include.Success) { $script:FragmentRefRegex.Match($include.Groups['ref'].Value) } else { $null }
        if ($null -eq $ref -or -not $ref.Success) {
            $State['Lines'].Add([string]$entry['Text'])
            $State['Map'].Add(@{ Source = $Path; Line = [int]$entry['Line'] })
            continue
        }
        $fragmentId = $ref.Groups['id'].Value
        if ((Test-AgentInList $Stack $fragmentId) -or (Test-AgentInList $State['Omit'] $fragmentId)) { continue }
        $State['Included'].Add($fragmentId)
        $fragmentPath = "$($State['FragmentsDir'])/$fragmentId.md"
        if ($State['Sources'].ContainsKey($fragmentPath)) {
            Expand-AgentFixtureSource -State $State -Path $fragmentPath -Stack ([string[]](@($Stack) + $fragmentId))
        }
    }
}

function ConvertTo-AgentFixtureLines {
    param($Value)
    $lineNo = 0
    , @(foreach ($text in @(Get-AgentItems $Value)) { $lineNo++; @{ Text = [string]$text; Line = $lineNo } })
}

function Invoke-AgentMethodFixtures {
    <#
    .SYNOPSIS
        Runs tests/agents/fixtures/method/cases.psd1 through Test-AgentMethod and returns every case that did not
        behave as its Expect says (empty when all pass), plus the case count as @{ Count; Failures }.
    .DESCRIPTION
        A case holds Method, SkillPolicy, SkillTools, Agents (each @{ Id; SubAgents; Template = @(lines) }) and
        Fragments (@{ '<NN-id>' = @(lines) }). The file's Base supplies any of them a case leaves out; a case's
        Fragments are merged over the Base fragments, and its Templates (@{ '<agent id>' = @(lines) }) replace
        those agents' templates. Expect 'fail' passes when a finding carries Rule (and, with
        Line, at that line of Path); 'pass' passes when there is no finding.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][regex]$Negation
    )
    $file = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) 'tests/agents/fixtures/method/cases.psd1'
    if (-not [System.IO.File]::Exists($file)) {
        return @{ Count = 0; Failures = @([pscustomobject]@{ Name = '(file)'; Expect = 'present'; Rule = ''; Got = 'missing'; Detail = $file }) }
    }
    $data = Import-PowerShellDataFile -LiteralPath $file
    $base = if ($data['Base'] -is [hashtable]) { $data['Base'] } else { @{} }
    $failures = [System.Collections.Generic.List[object]]::new()
    $count = 0
    foreach ($case in @(Get-AgentItems $data['Cases'])) {
        $count++
        $name = [string]$case['Name']
        try {
            $pick = { param($key) if ($case.ContainsKey($key)) { $case[$key] } else { $base[$key] } }
            $family = @{ Agents = @() }
            foreach ($key in 'Method', 'SkillPolicy') { $value = & $pick $key; if ($null -ne $value) { $family[$key] = $value } }
            $fragments = @{}
            foreach ($source in @($base['Fragments'], $case['Fragments'])) {
                if ($source -is [hashtable]) { foreach ($k in $source.Keys) { $fragments[[string]$k] = $source[$k] } }
            }
            $sources = @{}
            foreach ($k in $fragments.Keys) { $sources["fragments/soul/$k.md"] = ConvertTo-AgentFixtureLines $fragments[$k] }
            $agents = @(Get-AgentItems (& $pick 'Agents'))
            $results = [System.Collections.Generic.List[object]]::new()
            foreach ($agent in $agents) {
                $id = [string]$agent['Id']
                $family['Agents'] += , @{ Id = $id; SubAgents = $agent['SubAgents'] }
                $templatePath = "souls/$id.md"
                $template = $agent['Template']
                if ($case['Templates'] -is [hashtable] -and $case['Templates'].ContainsKey($id)) { $template = $case['Templates'][$id] }
                $sources[$templatePath] = ConvertTo-AgentFixtureLines $template
                $state = @{
                    Sources = $sources; FragmentsDir = 'fragments/soul'; Omit = [string[]]@()
                    Lines = [System.Collections.Generic.List[string]]::new()
                    Map = [System.Collections.Generic.List[object]]::new()
                    Included = [System.Collections.Generic.List[string]]::new()
                }
                Expand-AgentFixtureSource -State $state -Path $templatePath
                $text = if ($state['Lines'].Count -gt 0) { ($state['Lines'] -join "`n") + "`n" } else { '' }
                $results.Add(@{ Id = $id; Text = $text; LineMap = $state['Map'].ToArray(); Included = $state['Included'].ToArray() })
            }
            $skillTools = & $pick 'SkillTools'
            if ($skillTools -isnot [hashtable]) { $skillTools = @{} }
            $shape = @(if ($family.ContainsKey('Method')) { Get-AgentMethodShapeErrors -Method $family['Method'] -Family $family })
            $issues = @($shape | ForEach-Object { @{ Rule = 'METHOD-SHAPE'; Path = 'family'; Line = 0; Message = $_ } })
            $issues += @(Test-AgentMethod -Family $family -Results $results.ToArray() -SourceLines $sources -Negation $Negation -SkillTools $skillTools -SoulsDir 'souls' -FragmentsDir 'fragments/soul' -FamilyPath 'family')
        }
        catch {
            $failures.Add([pscustomobject]@{ Name = $name; Expect = $case['Expect']; Rule = $case['Rule']; Got = 'exception'; Detail = $_.Exception.Message })
            continue
        }
        $rules = @($issues | ForEach-Object { $_['Rule'] } | Select-Object -Unique)
        $want = [string]$case['Rule']
        $ok = if ($case['Expect'] -eq 'pass') { $issues.Count -eq 0 }
        else {
            $hits = @($issues | Where-Object { Test-AgentSame $_['Rule'] $want })
            if ($case.ContainsKey('Path')) { $hits = @($hits | Where-Object { (Test-AgentSame $_['Path'] $case['Path']) -and (-not $case.ContainsKey('Line') -or $_['Line'] -eq $case['Line']) }) }
            $hits.Count -gt 0
        }
        if (-not $ok) {
            $detail = @($issues | Select-Object -First 4 | ForEach-Object { "$($_['Rule']) $($_['Path']):$($_['Line']): $($_['Message'])" }) -join ' | '
            $failures.Add([pscustomobject]@{ Name = $name; Expect = $case['Expect']; Rule = $want; Got = ($rules -join ','); Detail = $detail })
        }
    }
    @{ Count = $count; Failures = $failures.ToArray() }
}

# ---------------------------------------------------------------------------------------------
# Skill use (LINT-SKILL-FRAGMENT, LINT-SKILL-UNUSED, LINT-TOPIC)
# ---------------------------------------------------------------------------------------------

# A topic pointer: the word "topic" or "topics", then one or more backticked ids separated by commas, "and"
# or "or"; an id may be followed by ", section" and a backticked section id.
$script:TopicItemPattern = '`(?<id>[a-z][a-z0-9-]*)`(?:,\s*section\s+`(?<section>[a-z][a-z0-9-]*)`)?'
$script:TopicPointerRegex = [regex]::new('(?<![\w-])[Tt]opics?\s+' + $script:TopicItemPattern + '(?:(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+)' + $script:TopicItemPattern + ')*', 'CultureInvariant')
$script:TopicItemRegex = [regex]::new($script:TopicItemPattern, 'CultureInvariant')

function Test-AgentUsesSkill {
    # True when the agent entry uses the policy skill: no Skills key means every policy skill.
    param($Agent, [string]$Skill)
    if ($Agent -isnot [hashtable] -or -not $Agent.ContainsKey('Skills')) { return $true }
    Test-AgentInList ([string[]]@(Get-AgentItems $Agent['Skills'])) $Skill
}

function Get-AgentTopicPointers {
    <#
    .SYNOPSIS
        The topic pointers on one line: @(@{ Id; Section }), in order (Section is '' when absent).
    #>
    param([string]$Text)
    , @(foreach ($pointer in $script:TopicPointerRegex.Matches($Text)) {
            foreach ($item in $script:TopicItemRegex.Matches($pointer.Value)) {
                @{ Id = $item.Groups['id'].Value; Section = $(if ($item.Groups['section'].Success) { $item.Groups['section'].Value } else { '' }) }
            }
        })
}

function Read-AgentTopicIndex {
    <#
    .SYNOPSIS
        Reads a SkillPolicy skill's TopicIndex (a JSON array of @{ id; usedBy; ... }) and the topics.lock.json beside
        it (its topics[].sections): @{ Path; Ids; UsedBy (id -> string[]); Sections (id -> string[]); Errors }.
    #>
    param([Parameter(Mandatory)][string]$RepoRoot, [Parameter(Mandatory)][string]$RelativePath)
    $errors = [System.Collections.Generic.List[string]]::new()
    $ids = [System.Collections.Generic.List[string]]::new()
    $usedBy = @{}
    $sections = @{}
    $full = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $RelativePath
    try {
        foreach ($entry in @(Get-Content -LiteralPath $full -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable)) {
            if ($entry -isnot [System.Collections.IDictionary] -or $entry['id'] -isnot [string]) { $errors.Add("$RelativePath holds an entry without an id"); continue }
            $ids.Add($entry['id'])
            $usedBy[$entry['id']] = [string[]]@(Get-AgentItems $entry['usedBy'] | Where-Object { $_ -is [string] })
        }
    }
    catch { $errors.Add("cannot read ${RelativePath}: $($_.Exception.Message)") }
    $lockRel = ($RelativePath -replace '[^/\\]+$', '') + 'topics.lock.json'
    $lockFull = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $lockRel
    if ([System.IO.File]::Exists($lockFull)) {
        try {
            $lock = Get-Content -LiteralPath $lockFull -Raw -Encoding utf8 | ConvertFrom-Json -AsHashtable
            foreach ($topic in @(Get-AgentItems $lock['topics'])) {
                if ($topic -is [System.Collections.IDictionary] -and $topic['id'] -is [string]) {
                    $sections[$topic['id']] = [string[]]@(Get-AgentItems $topic['sections'] | Where-Object { $_ -is [string] })
                }
            }
        }
        catch { $errors.Add("cannot read ${lockRel}: $($_.Exception.Message)") }
    }
    else { $errors.Add("$lockRel is missing (run python -B build/craft-reference/generate.py)") }
    @{ Path = $RelativePath; Ids = [string[]]$ids.ToArray(); UsedBy = $usedBy; Sections = $sections; Errors = $errors.ToArray() }
}

function Test-AgentSkillUse {
    <#
    .SYNOPSIS
        LINT-SKILL-FRAGMENT, LINT-SKILL-UNUSED and LINT-TOPIC for one family. Emits @{ Rule; Path; Line; Message; Note }.
    .DESCRIPTION
        Family is the family data; Results the compose results of the agents checked (Id, Text, LineMap,
        Included). TopicIndexes maps a SkillPolicy skill name to its Read-AgentTopicIndex result. FullRoster says
        Results covers the whole roster (LINT-SKILL-UNUSED and the LINT-TOPIC presence rules need it).
          LINT-SKILL-FRAGMENT  an agent includes a skill's Fragment exactly when it uses that skill (its Skills key)
          LINT-SKILL-UNUSED    a SkillPolicy skill that no roster agent uses
          LINT-TOPIC           a pointer ("topic `<id>`", ", section `<id>`") names an id missing from the skill's
                               TopicIndex, or a section missing from topics.lock.json beside it; an agent that does
                               not use the skill carries a pointer. With Release also: an agent that uses the
                               skill names no topic, and the agents naming a topic differ from its usedBy list;
                               without Release those two print as one note each (Note = $true).
        Pointer findings are reported at the source line through the line map, once per line.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][hashtable]$Family,
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Results,
        [hashtable]$TopicIndexes = @{},
        [bool]$FullRoster = $true,
        [bool]$Release = $false,
        [string]$FamilyPath = $script:FamilyRelPath,
        [string]$RepoRoot = ''
    )
    $lineOf = {
        param([string]$AgentId, [string]$Key)
        if (-not $RepoRoot) { return 0 }
        $lineArgs = @{ RepoRoot = $RepoRoot }
        if ($AgentId) { $lineArgs['AgentId'] = $AgentId }
        if ($Key) { $lineArgs['Key'] = $Key }
        Get-AgentFamilyLine @lineArgs
    }
    $found = [System.Collections.Generic.List[object]]::new()
    $keys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $add = {
        param([string]$Rule, [string]$Path, [int]$Line, [string]$Message, [bool]$Note = $false)
        if ($keys.Add("$Rule|$Path|$Line|$Message")) { $found.Add(@{ Rule = $Rule; Path = $Path; Line = $Line; Message = $Message; Note = $Note }) }
    }
    $policy = $Family['SkillPolicy']
    $skills = @(if ($policy -is [hashtable]) { @(Get-AgentItems $policy['Skills']) | Where-Object { $_ -is [hashtable] -and $_['Name'] -is [string] } })
    $agentsById = @{}
    $roster = @(Get-AgentItems $Family['Agents'] | Where-Object { $_ -is [hashtable] })
    foreach ($agent in $roster) { $id = Get-AgentIdOf $agent; if ($id) { $agentsById[$id] = $agent } }

    foreach ($skill in $skills) {
        $name = [string]$skill['Name']
        # ---- LINT-SKILL-UNUSED ----
        if ($FullRoster -and @($roster | Where-Object { Test-AgentUsesSkill $_ $name }).Count -eq 0) {
            & $add 'LINT-SKILL-UNUSED' $FamilyPath (& $lineOf -Key 'SkillPolicy') "SkillPolicy skill '$name' is used by no agent (every agent sets Skills without it); drop it from SkillPolicy"
        }
        # ---- LINT-SKILL-FRAGMENT ----
        $fragmentId = if ($skill['Fragment'] -is [string]) { [string]$skill['Fragment'] } else { '' }
        if ($fragmentId) {
            foreach ($result in $Results) {
                $id = [string]$result['Id']
                $agent = $agentsById[$id]
                if ($null -eq $agent) { continue }
                $uses = Test-AgentUsesSkill $agent $name
                $includes = Test-AgentInList ([string[]]@($result['Included'])) $fragmentId
                if ($uses -and -not $includes) {
                    & $add 'LINT-SKILL-FRAGMENT' $FamilyPath (& $lineOf -AgentId $id) "agent '$id' uses skill '$name' but does not include its reference fragment $fragmentId; add it to Fragments and the template"
                }
                elseif ($includes -and -not $uses) {
                    & $add 'LINT-SKILL-FRAGMENT' $FamilyPath (& $lineOf -AgentId $id) "agent '$id' includes $fragmentId, the reference fragment of skill '$name', but does not use that skill (its Skills key)"
                }
            }
        }
        # ---- LINT-TOPIC ----
        if (-not $TopicIndexes.ContainsKey($name)) { continue }
        $index = $TopicIndexes[$name]
        foreach ($e in @($index['Errors'])) { & $add 'LINT-TOPIC' ([string]$index['Path']) 0 $e }
        $known = [System.Collections.Generic.HashSet[string]]::new([string[]]@($index['Ids']), [StringComparer]::Ordinal)
        $namedBy = @{}
        $silent = [System.Collections.Generic.List[string]]::new()
        foreach ($result in $Results) {
            $id = [string]$result['Id']
            $agent = $agentsById[$id]
            if ($null -eq $agent) { continue }
            $uses = Test-AgentUsesSkill $agent $name
            $lines = Get-AgentComposedLines -Result $result
            $map = @($result['LineMap'])
            $named = 0
            for ($i = 0; $i -lt $lines.Length -and $i -lt $map.Count; $i++) {
                $pointers = Get-AgentTopicPointers -Text $lines[$i]
                if ($pointers.Count -eq 0) { continue }
                $source = [string]$map[$i]['Source']
                $line = [int]$map[$i]['Line']
                if (-not $uses) {
                    & $add 'LINT-TOPIC' $source $line "agent '$id' does not use skill '$name' but this line points at topic '$($pointers[0]['Id'])'"
                    continue
                }
                foreach ($pointer in $pointers) {
                    $topic = [string]$pointer['Id']
                    if (-not $known.Contains($topic)) {
                        & $add 'LINT-TOPIC' $source $line "topic '$topic' is not in $($index['Path'])"
                        continue
                    }
                    $named++
                    if (-not $namedBy.ContainsKey($topic)) { $namedBy[$topic] = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal) }
                    [void]$namedBy[$topic].Add($id)
                    $section = [string]$pointer['Section']
                    if ($section -and -not (Test-AgentInList ([string[]]@($index['Sections'][$topic])) $section)) {
                        & $add 'LINT-TOPIC' $source $line "topic '$topic' has no section '$section' (topics.lock.json: $(@($index['Sections'][$topic]) -join ', '))"
                    }
                }
            }
            if ($uses -and $named -eq 0) { $silent.Add($id) }
        }
        if (-not $FullRoster) { continue }
        $differ = [System.Collections.Generic.List[string]]::new()
        foreach ($topic in @($index['Ids'])) {
            $want = [string[]]@($index['UsedBy'][$topic] | Sort-Object -Culture ([Globalization.CultureInfo]::InvariantCulture))
            $have = [string[]]@(if ($namedBy.ContainsKey($topic)) { @($namedBy[$topic]) | Sort-Object -Culture ([Globalization.CultureInfo]::InvariantCulture) })
            if (($want -join ',') -cne ($have -join ',')) {
                if ($Release) { & $add 'LINT-TOPIC' ([string]$index['Path']) 0 "topic '$topic' is named by [$($have -join ', ')] but its usedBy is [$($want -join ', ')]" }
                else { $differ.Add($topic) }
            }
        }
        if ($Release) {
            foreach ($id in $silent) { & $add 'LINT-TOPIC' $FamilyPath (& $lineOf -AgentId $id) "agent '$id' uses skill '$name' but names no topic" }
        }
        else {
            if ($silent.Count -gt 0) { & $add 'LINT-TOPIC' $FamilyPath 0 "$($silent.Count) agent(s) use skill '$name' but name no topic yet: $($silent -join ', ')" $true }
            if ($differ.Count -gt 0) { & $add 'LINT-TOPIC' ([string]$index['Path']) 0 "$($differ.Count) topic(s) are named by agents other than their usedBy list: $($differ -join ', ')" $true }
        }
    }
    $found.ToArray()
}

function Invoke-AgentSkillUseFixtures {
    <#
    .SYNOPSIS
        Runs tests/agents/fixtures/skills/cases.psd1 through Test-AgentSkillUse and returns @{ Count; Failures }.
    .DESCRIPTION
        A case holds SkillPolicy, Topics (@(@{ id; usedBy; sections })), Release, Agents (each @{ Id; Skills;
        Template = @(lines) }; a missing Skills key means every policy skill, $null or @() none) and Fragments
        (@{ '<NN-id>' = @(lines) }). The file's Base supplies any of them a case leaves out; a case's Fragments are
        merged over the Base ones and its Templates replace single agent templates. Expect 'fail' passes when a
        finding that is not a note carries Rule (and, with Path and Line, at that place); 'note' when a note carries
        Rule; 'pass' when there is no finding apart from notes.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $file = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) 'tests/agents/fixtures/skills/cases.psd1'
    if (-not [System.IO.File]::Exists($file)) {
        return @{ Count = 0; Failures = @([pscustomobject]@{ Name = '(file)'; Expect = 'present'; Rule = ''; Got = 'missing'; Detail = $file }) }
    }
    $data = Import-PowerShellDataFile -LiteralPath $file
    $base = if ($data['Base'] -is [hashtable]) { $data['Base'] } else { @{} }
    $failures = [System.Collections.Generic.List[object]]::new()
    $count = 0
    foreach ($case in @(Get-AgentItems $data['Cases'])) {
        $count++
        $name = [string]$case['Name']
        try {
            $pick = { param($key) if ($case.ContainsKey($key)) { $case[$key] } else { $base[$key] } }
            $family = @{ Agents = @() }
            $policy = & $pick 'SkillPolicy'
            if ($null -ne $policy) { $family['SkillPolicy'] = $policy }
            $fragments = @{}
            foreach ($source in @($base['Fragments'], $case['Fragments'])) {
                if ($source -is [hashtable]) { foreach ($k in $source.Keys) { $fragments[[string]$k] = $source[$k] } }
            }
            $sources = @{}
            foreach ($k in $fragments.Keys) { $sources["fragments/soul/$k.md"] = ConvertTo-AgentFixtureLines $fragments[$k] }
            $results = [System.Collections.Generic.List[object]]::new()
            foreach ($agent in @(Get-AgentItems (& $pick 'Agents'))) {
                $id = [string]$agent['Id']
                $entry = @{ Id = $id }
                if ($agent.ContainsKey('Skills')) { $entry['Skills'] = [string[]]@(Get-AgentItems $agent['Skills']) }
                $family['Agents'] += , $entry
                $templatePath = "souls/$id.md"
                $template = $agent['Template']
                if ($case['Templates'] -is [hashtable] -and $case['Templates'].ContainsKey($id)) { $template = $case['Templates'][$id] }
                $sources[$templatePath] = ConvertTo-AgentFixtureLines $template
                $state = @{
                    Sources = $sources; FragmentsDir = 'fragments/soul'; Omit = [string[]]@()
                    Lines = [System.Collections.Generic.List[string]]::new()
                    Map = [System.Collections.Generic.List[object]]::new()
                    Included = [System.Collections.Generic.List[string]]::new()
                }
                Expand-AgentFixtureSource -State $state -Path $templatePath
                $text = if ($state['Lines'].Count -gt 0) { ($state['Lines'] -join "`n") + "`n" } else { '' }
                $results.Add(@{ Id = $id; Text = $text; LineMap = $state['Map'].ToArray(); Included = $state['Included'].ToArray() })
            }
            $indexes = @{}
            $topics = & $pick 'Topics'
            if ($null -ne $topics -and $policy -is [hashtable]) {
                $usedBy = @{}
                $sections = @{}
                $ids = [System.Collections.Generic.List[string]]::new()
                foreach ($topic in @(Get-AgentItems $topics)) {
                    $ids.Add([string]$topic['id'])
                    $usedBy[[string]$topic['id']] = [string[]]@(Get-AgentItems $topic['usedBy'])
                    $sections[[string]$topic['id']] = [string[]]@(Get-AgentItems $topic['sections'])
                }
                foreach ($skill in @(Get-AgentItems $policy['Skills'])) {
                    if ($skill -is [hashtable] -and $skill['TopicIndex'] -is [string]) {
                        $indexes[[string]$skill['Name']] = @{ Path = [string]$skill['TopicIndex']; Ids = [string[]]$ids.ToArray(); UsedBy = $usedBy; Sections = $sections; Errors = @() }
                    }
                }
            }
            $release = [bool](& $pick 'Release')
            $issues = @(Test-AgentSkillUse -Family $family -Results $results.ToArray() -TopicIndexes $indexes -Release $release -FamilyPath 'family')
        }
        catch {
            $failures.Add([pscustomobject]@{ Name = $name; Expect = $case['Expect']; Rule = $case['Rule']; Got = 'exception'; Detail = $_.Exception.Message })
            continue
        }
        $errorsOnly = @($issues | Where-Object { -not $_['Note'] })
        $want = [string]$case['Rule']
        $ok = switch ([string]$case['Expect']) {
            'pass' { $errorsOnly.Count -eq 0 }
            'note' { $errorsOnly.Count -eq 0 -and @($issues | Where-Object { $_['Note'] -and (Test-AgentSame $_['Rule'] $want) }).Count -gt 0 }
            default {
                $hits = @($errorsOnly | Where-Object { Test-AgentSame $_['Rule'] $want })
                if ($case.ContainsKey('Path')) { $hits = @($hits | Where-Object { (Test-AgentSame $_['Path'] $case['Path']) -and (-not $case.ContainsKey('Line') -or $_['Line'] -eq $case['Line']) }) }
                $hits.Count -gt 0
            }
        }
        if (-not $ok) {
            $detail = @($issues | Select-Object -First 4 | ForEach-Object { "$($_['Rule'])$(if ($_['Note']) { ' (note)' }) $($_['Path']):$($_['Line']): $($_['Message'])" }) -join ' | '
            $failures.Add([pscustomobject]@{ Name = $name; Expect = $case['Expect']; Rule = $want; Got = (@($issues | ForEach-Object { $_['Rule'] } | Select-Object -Unique) -join ','); Detail = $detail })
        }
    }
    @{ Count = $count; Failures = $failures.ToArray() }
}

# ---------------------------------------------------------------------------------------------
# Document counts (DOC-COUNT)
# ---------------------------------------------------------------------------------------------

$script:DocCountNumberWords = $null

function Get-AgentNumberWords {
    # Number words 10..99 ("ten" ... "ninety-nine") mapped to their values.
    if ($null -ne $script:DocCountNumberWords) { return $script:DocCountNumberWords }
    $map = [System.Collections.Generic.Dictionary[string, int]]::new([StringComparer]::OrdinalIgnoreCase)
    $units = @('', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine')
    $teens = @('ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen')
    for ($i = 0; $i -lt 10; $i++) { $map[$teens[$i]] = 10 + $i }
    $tens = @('twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety')
    for ($i = 0; $i -lt $tens.Count; $i++) {
        $map[$tens[$i]] = 20 + 10 * $i
        for ($u = 1; $u -lt 10; $u++) { $map["$($tens[$i])-$($units[$u])"] = 20 + 10 * $i + $u }
    }
    $script:DocCountNumberWords = $map
    $map
}

function Test-AgentDocCounts {
    <#
    .SYNOPSIS
        DOC-COUNT: roster counts stated in the documents of build/agent-src/catalog/doc-counts.psd1.
    .DESCRIPTION
        Union is the Get-AgentRosterUnion result. The accepted values are derived from it (all packages, each
        family's roster, and for a family with RosterOrder its table length and the lead's companions, the table
        without the lead) plus the data file's Allow values. Returns @{ Values; Findings; Errors; Documents }:
        Values maps each accepted number to why; Findings and Errors are error objects (Path; Line; Message).
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][hashtable]$Union
    )
    $root = Resolve-AgentFullPath -Path $RepoRoot
    $rel = 'build/agent-src/catalog/doc-counts.psd1'
    $full = Join-AgentRepoPath $root $rel
    $values = [System.Collections.Generic.SortedDictionary[int, string]]::new()
    $findings = [System.Collections.Generic.List[object]]::new()
    $errors = [System.Collections.Generic.List[object]]::new()
    $documents = [System.Collections.Generic.List[string]]::new()
    $addValue = { param([int]$Value, [string]$Why) if (-not $values.ContainsKey($Value)) { $values[$Value] = $Why } }
    & $addValue @($Union['Ids']).Count 'all packages'
    foreach ($family in @($Union['Families'])) {
        & $addValue @($family['Roster']).Count "the $($family['Id']) roster"
        $data = $family['Data']
        $order = @(if ($data -is [hashtable] -and $data['RosterOrder'] -is [array]) { $data['RosterOrder'] })
        if ($order.Count -gt 0) {
            & $addValue $order.Count "the $($family['Id']) roster table (RosterOrder)"
            if ($data['Lead'] -is [string] -and (Test-AgentInList ([string[]]$order) $data['Lead'])) { & $addValue ($order.Count - 1) "the companions of $($data['Lead'])" }
        }
    }
    if (-not [System.IO.File]::Exists($full)) { return @{ Values = $values; Findings = @(); Errors = @(); Documents = @() } }
    $data = $null
    try { $data = Import-AgentDataFile -FullPath $full -RelativePath $rel }
    catch {
        $errors.Add((New-AgentComposeError $rel 1 "cannot load: $(($_.Exception.Message -replace '\s+', ' ').Trim())"))
        return @{ Values = $values; Findings = @(); Errors = $errors.ToArray(); Documents = @() }
    }
    foreach ($allow in @(Get-AgentItems $data['Allow'])) {
        if ($allow -isnot [hashtable] -or $allow['Value'] -isnot [int] -or $allow['Why'] -isnot [string] -or [string]::IsNullOrWhiteSpace($allow['Why'])) {
            $errors.Add((New-AgentComposeError $rel 1 'each Allow entry is @{ Value = <number>; Why = <reason> }'))
            continue
        }
        & $addValue $allow['Value'] "allowed: $($allow['Why'])"
    }
    $history = [string[]]@(foreach ($entry in @(Get-AgentItems $data['History'])) {
            $phrase = if ($entry -is [hashtable]) { $entry['Phrase'] } else { $entry }
            if ($phrase -isnot [string] -or $phrase.Length -eq 0) { $errors.Add((New-AgentComposeError $rel 1 'each History entry is an exact phrase (or @{ Phrase; Why })')); continue }
            $phrase
        })
    foreach ($pattern in @(Get-AgentItems $data['Documents'])) {
        if ($pattern -isnot [string] -or $pattern.Length -eq 0) { continue }
        if ($pattern.Contains('*')) {
            $dir = if ($pattern.Contains('/')) { $pattern.Substring(0, $pattern.LastIndexOf('/')) } else { '.' }
            $leaf = $pattern.Substring($pattern.LastIndexOf('/') + 1)
            $dirFull = Join-AgentRepoPath $root $dir
            if (-not [System.IO.Directory]::Exists($dirFull)) { continue }
            $names = [string[]]@([System.IO.Directory]::GetFiles($dirFull, $leaf) | ForEach-Object { [System.IO.Path]::GetFileName($_) })
            [Array]::Sort($names, [StringComparer]::Ordinal)
            foreach ($name in $names) { $documents.Add("$dir/$name") }
        }
        elseif ([System.IO.File]::Exists((Join-AgentRepoPath $root $pattern))) { $documents.Add($pattern) }
    }
    $words = Get-AgentNumberWords
    $wordAlternation = (@($words.Keys) | Sort-Object { $_.Length } -Descending) -join '|'
    $regex = [regex]::new("(?<![\w.-])(?<num>\d{2,}|$wordAlternation)(?:\s+(?:development-family|development|agent|Marketplace|Sophon|``?\.sophon-agent``?)){0,2}\s+(?:agents|packages|companions)\b", 'IgnoreCase, CultureInvariant')
    $accepted = @($values.Keys) -join ', '
    foreach ($document in $documents) {
        $lines = [System.IO.File]::ReadAllLines((Join-AgentRepoPath $root $document))
        for ($i = 0; $i -lt $lines.Length; $i++) {
            foreach ($match in $regex.Matches($lines[$i])) {
                $token = $match.Groups['num'].Value
                $value = 0
                if (-not [int]::TryParse($token, [ref]$value)) { $value = $words[$token] }
                if ($value -lt 10 -or $values.ContainsKey($value)) { continue }
                $inHistory = $false
                foreach ($phrase in $history) {
                    $at = $lines[$i].IndexOf($phrase, [StringComparison]::Ordinal)
                    while ($at -ge 0) {
                        if ($match.Index -ge $at -and $match.Index + $match.Length -le $at + $phrase.Length) { $inHistory = $true }
                        $at = $lines[$i].IndexOf($phrase, $at + 1, [StringComparison]::Ordinal)
                    }
                }
                if ($inHistory) { continue }
                $findings.Add((New-AgentComposeError $document ($i + 1) "'$($match.Value)' states $value, which is not a roster count ($accepted); update it, or list the phrase under History in $rel"))
            }
        }
    }
    @{ Values = $values; Findings = $findings.ToArray(); Errors = $errors.ToArray(); Documents = $documents.ToArray() }
}

function Get-AgentAnchorDataLine {
    # The line of the data file that holds Text as a quoted literal; 1 when it cannot be placed.
    param([string[]]$Lines, [string]$Text)
    $quoted = "'" + $Text.Replace("'", "''") + "'"
    for ($i = 0; $i -lt $Lines.Length; $i++) {
        if ($Lines[$i].Contains($quoted, [StringComparison]::Ordinal)) { return $i + 1 }
    }
    1
}

function Test-AgentAnchors {
    <#
    .SYNOPSIS
        ANCHOR-MISSING and ANCHOR-GONE: exact strings each composed SOUL or README must, or must no longer, carry.
    .DESCRIPTION
        Data is the parsed anchor file (tests/agents/fixtures/anchors/<family>.psd1), DataLines its raw lines (to
        place findings), DataPath its repository path. Texts maps an agent id to @{ SOUL = <text>; README = <text> }.
        Family is the family data (Agents with Id and Writer, Lead, FamilyVersion). Selected limits the agents
        checked; an In list may still name any roster agent.

        Anchors: @{ Text; In; File; Except }. In is 'all', 'writers', 'readers', 'lead' or a list of agent ids; File
        is 'SOUL' (default) or 'README'; Except removes agent ids from a named set.
        Removed: @{ Text; Why }: an anchor dropped on purpose; listing the same Text under Anchors is an error.
        Gone: @{ Text; File; Since; Pending; Why }: 2.x wording that must be absent from every agent's File once
        FamilyVersion is at least Since (SemVer core); before that it is counted as pending. Pending = 'M<n>'
        names the milestone that rewrites the text: until then the entry is counted as pending too, and with
        -Release a remaining Pending is an ANCHOR-GONE finding (delete the key in the commit that rewrites it).
        Returns @{ Findings; Errors; Anchors; Checked; Pending }.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][hashtable]$Data,
        [AllowEmptyCollection()][string[]]$DataLines = @(),
        [Parameter(Mandatory)][string]$DataPath,
        [Parameter(Mandatory)][hashtable]$Family,
        [Parameter(Mandatory)][hashtable]$Texts,
        [AllowEmptyCollection()][string[]]$Selected = @(),
        [switch]$Release
    )
    $findings = [System.Collections.Generic.List[object]]::new()
    $errors = [System.Collections.Generic.List[object]]::new()
    $ord = [StringComparison]::Ordinal
    $roster = [string[]]@(foreach ($a in @(Get-AgentItems $Family['Agents'])) { Get-AgentIdOf $a })
    $sets = @{
        all     = $roster
        writers = [string[]]@(foreach ($a in @(Get-AgentItems $Family['Agents'])) { if ($a['Writer'] -eq $true) { Get-AgentIdOf $a } })
        readers = [string[]]@(foreach ($a in @(Get-AgentItems $Family['Agents'])) { if ($a['Writer'] -ne $true) { Get-AgentIdOf $a } })
        lead    = [string[]]@(if ($Family['Lead'] -is [string]) { $Family['Lead'] })
    }
    $check = if ($Selected.Count -gt 0) { $Selected } else { $roster }
    $fileOf = {
        param($Entry, [int]$Line)
        $file = if ($null -eq $Entry['File']) { 'SOUL' } else { [string]$Entry['File'] }
        if (-not (Test-AgentInList @('SOUL', 'README') $file)) { $errors.Add((New-AgentComposeError $DataPath $Line "File '$file' is not SOUL or README")); return $null }
        $file
    }
    $removed = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($entry in @(Get-AgentItems $Data['Removed'])) {
        if ($entry -isnot [hashtable] -or $entry['Text'] -isnot [string] -or $entry['Text'].Length -eq 0 -or $entry['Why'] -isnot [string] -or [string]::IsNullOrWhiteSpace($entry['Why'])) {
            $errors.Add((New-AgentComposeError $DataPath 1 'each Removed entry is @{ Text = <exact string>; Why = <reason> }'))
            continue
        }
        [void]$removed.Add($entry['Text'])
    }
    $anchorCount = 0
    $checked = 0
    foreach ($entry in @(Get-AgentItems $Data['Anchors'])) {
        if ($entry -isnot [hashtable] -or $entry['Text'] -isnot [string] -or $entry['Text'].Length -eq 0) {
            $errors.Add((New-AgentComposeError $DataPath 1 'each Anchors entry is @{ Text = <exact string>; In = <set or agent ids> }'))
            continue
        }
        $text = [string]$entry['Text']
        $line = Get-AgentAnchorDataLine -Lines $DataLines -Text $text
        if ($removed.Contains($text)) { $errors.Add((New-AgentComposeError $DataPath $line "'$text' is listed under both Anchors and Removed")); continue }
        $file = & $fileOf $entry $line
        if ($null -eq $file) { continue }
        $in = $entry['In']
        $targets = $null
        if ($in -is [string] -and $sets.ContainsKey($in)) { $targets = $sets[$in] }
        elseif ($in -is [string] -or $in -is [array]) {
            $targets = [string[]]@($in)
            foreach ($id in $targets) {
                if (-not (Test-AgentInList $roster $id)) { $errors.Add((New-AgentComposeError $DataPath $line "In names '$id', which is neither a set (all, writers, readers, lead) nor a roster agent")) }
            }
        }
        else { $errors.Add((New-AgentComposeError $DataPath $line "'$text' has no In (a set or a list of agent ids)")); continue }
        $except = [string[]]@(Get-AgentItems $entry['Except'])
        foreach ($id in $except) {
            if (-not (Test-AgentInList $targets $id)) { $errors.Add((New-AgentComposeError $DataPath $line "Except names '$id', which In does not include")) }
        }
        $anchorCount++
        foreach ($id in $targets) {
            if ((Test-AgentInList $except $id) -or -not (Test-AgentInList $check $id) -or -not $Texts.ContainsKey($id)) { continue }
            $body = $Texts[$id][$file]
            if ($null -eq $body) { continue }
            $checked++
            if ($body.IndexOf($text, $ord) -lt 0) {
                $findings.Add(@{ Rule = 'ANCHOR-MISSING'; Path = "agents/$id/$file.md"; Line = 0; Message = "lacks the anchor '$text' ($DataPath`:$line); restore it, or move the entry to Removed with a reason" })
            }
        }
    }
    $pending = 0
    $versionMatch = [regex]::Match([string]$Family['FamilyVersion'], '^(\d+)\.(\d+)\.(\d+)')
    $familyVersion = if ($versionMatch.Success) { [version]::new([int]$versionMatch.Groups[1].Value, [int]$versionMatch.Groups[2].Value, [int]$versionMatch.Groups[3].Value) } else { $null }
    foreach ($entry in @(Get-AgentItems $Data['Gone'])) {
        if ($entry -isnot [hashtable] -or $entry['Text'] -isnot [string] -or $entry['Text'].Length -eq 0 -or $entry['Why'] -isnot [string] -or [string]::IsNullOrWhiteSpace($entry['Why'])) {
            $errors.Add((New-AgentComposeError $DataPath 1 'each Gone entry is @{ Text = <exact string>; File = SOUL|README; Since = <x.y.z>; Why = <reason> }'))
            continue
        }
        $text = [string]$entry['Text']
        $line = Get-AgentAnchorDataLine -Lines $DataLines -Text $text
        $file = & $fileOf $entry $line
        if ($null -eq $file) { continue }
        if ($null -ne $entry['Since']) {
            $since = [regex]::Match([string]$entry['Since'], '^(\d+)\.(\d+)\.(\d+)$')
            if (-not $since.Success) { $errors.Add((New-AgentComposeError $DataPath $line "Since '$($entry['Since'])' is not x.y.z")); continue }
            $sinceVersion = [version]::new([int]$since.Groups[1].Value, [int]$since.Groups[2].Value, [int]$since.Groups[3].Value)
            if ($null -eq $familyVersion -or $familyVersion -lt $sinceVersion) { $pending++; continue }
        }
        if ($null -ne $entry['Pending']) {
            $milestone = [string]$entry['Pending']
            if ($milestone -cnotmatch '^M[0-9]+$') { $errors.Add((New-AgentComposeError $DataPath $line "Pending '$milestone' must be a milestone such as 'M5'")); continue }
            if (-not $Release) { $pending++; continue }
            $findings.Add(@{ Rule = 'ANCHOR-GONE'; Path = $DataPath; Line = $line; Message = "'$text' is still Pending $milestone; rewrite the text and delete the key (-Release)" })
            continue
        }
        foreach ($id in $check) {
            if (-not $Texts.ContainsKey($id)) { continue }
            $body = $Texts[$id][$file]
            if ($null -eq $body) { continue }
            $at = $body.IndexOf($text, $ord)
            if ($at -ge 0) {
                $hitLine = 1
                for ($k = 0; $k -lt $at; $k++) { if ($body[$k] -eq "`n") { $hitLine++ } }
                $findings.Add(@{ Rule = 'ANCHOR-GONE'; Path = "agents/$id/$file.md"; Line = $hitLine; Message = "still carries '$text', which $DataPath`:$line lists as gone ($($entry['Why']))" })
            }
        }
    }
    @{ Findings = $findings.ToArray(); Errors = $errors.ToArray(); Anchors = $anchorCount; Checked = $checked; Pending = $pending }
}

# ---------------------------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------------------------

function Format-AgentComposeError {
    <#
    .SYNOPSIS
        Formats an error object as "ERROR <path>:<line>: <message>".
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory, ValueFromPipeline)][hashtable]$Item)
    process { 'ERROR {0}:{1}: {2}' -f $Item['Path'], $Item['Line'], $Item['Message'] }
}

function Compare-AgentSoulText {
    <#
    .SYNOPSIS
        Compares committed SOUL bytes with a compose result.
    .DESCRIPTION
        Returns $null when the bytes are identical; otherwise @{ Line; Committed; Composed; From }
        describing the first differing line (values are display strings). Pass $null for a
        missing file.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [AllowNull()][byte[]]$CommittedBytes,
        [Parameter(Mandatory)][hashtable]$Result
    )
    $text = [string]$Result['Text']
    $composedBytes = $script:LenientUtf8.GetBytes($text)
    if (Test-AgentBytesEqual -Left $CommittedBytes -Right $composedBytes) { return $null }
    $map = @($Result['LineMap'])
    $composed = Split-AgentTextLines -Text $text
    $composedLines = $composed['Lines']

    $from = {
        param([int]$Index)
        if ($Index -ge 0 -and $Index -lt $map.Count) { return '{0}:{1}' -f $map[$Index]['Source'], $map[$Index]['Line'] }
        '(end of composed output)'
    }

    if ($null -eq $CommittedBytes) {
        $first = if ($composedLines.Length -gt 0) { $composedLines[0] } else { $null }
        return @{ Line = 1; Committed = '(missing file)'; Composed = (ConvertTo-AgentVisibleText -Value $first); From = (& $from 0) }
    }
    $committed = Split-AgentTextLines -Text ($script:LenientUtf8.GetString($CommittedBytes))
    $committedLines = $committed['Lines']
    $n = [Math]::Max($committedLines.Length, $composedLines.Length)
    for ($i = 0; $i -lt $n; $i++) {
        $a = if ($i -lt $committedLines.Length) { $committedLines[$i] } else { $null }
        $b = if ($i -lt $composedLines.Length) { $composedLines[$i] } else { $null }
        if (-not (Test-AgentSame $a $b)) {
            return @{
                Line = $i + 1
                Committed = (ConvertTo-AgentVisibleText -Value $a)
                Composed = (ConvertTo-AgentVisibleText -Value $b)
                From = (& $from $i)
            }
        }
    }
    # Every line matches, so only the final newline differs.
    $index = [Math]::Max($composedLines.Length - 1, 0)
    $lastCommitted = if ($committedLines.Length -gt 0) { $committedLines[$committedLines.Length - 1] } else { $null }
    $lastComposed = if ($composedLines.Length -gt 0) { $composedLines[$composedLines.Length - 1] } else { $null }
    $committedNote = if ($committed['EndsWithNewline']) { '' } else { ' (no final newline)' }
    $composedNote = if ($composed['EndsWithNewline']) { '' } else { ' (no final newline)' }
    @{
        Line = $index + 1
        Committed = (ConvertTo-AgentVisibleText -Value $lastCommitted) + $committedNote
        Composed = (ConvertTo-AgentVisibleText -Value $lastComposed) + $composedNote
        From = (& $from $index)
    }
}

function Write-AgentSoulFile {
    <#
    .SYNOPSIS
        Writes Text (UTF-8, no BOM) to Path only when the bytes differ. Returns $true when written.
    #>
    [CmdletBinding()]
    [OutputType([bool])]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][AllowEmptyString()][string]$Text
    )
    $bytes = $script:LenientUtf8.GetBytes($Text)
    if ([System.IO.File]::Exists($Path)) {
        if (Test-AgentBytesEqual -Left ([System.IO.File]::ReadAllBytes($Path)) -Right $bytes) { return $false }
    }
    $directory = [System.IO.Path]::GetDirectoryName($Path)
    if ($directory -and -not [System.IO.Directory]::Exists($directory)) {
        [void][System.IO.Directory]::CreateDirectory($directory)
    }
    [System.IO.File]::WriteAllBytes($Path, $bytes)
    $true
}

function Get-AgentSoulBudget {
    <#
    .SYNOPSIS
        Byte budget figures: @{ Bytes; Cap; Percent; Free; FreePercent; Headroom; Tokens }.
    .DESCRIPTION
        Percent is the share of the cap used and FreePercent the share left (both rounded to 0.01), with
        Free = Cap - Bytes. Tokens = round(bytes / 3.8), an estimate. Headroom is 'over' (over the cap),
        'fail' (less than 5% free: Free * 100 < Cap * 5), 'warn' (less than 8% free) or 'ok'; exactly 5% free
        is not 'fail'. A cap of 0 gives 'ok' and zero percentages (no cap to measure against).
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][int]$Bytes,
        [Parameter(Mandatory)][int]$Cap
    )
    $percent = if ($Cap -gt 0) { [Math]::Round(100.0 * $Bytes / $Cap, 1) } else { 0.0 }
    $free = $Cap - $Bytes
    $freePercent = if ($Cap -gt 0) { [Math]::Round(100.0 * $free / $Cap, 2) } else { 0.0 }
    $headroom = 'ok'
    if ($Cap -gt 0) {
        if ($Bytes -gt $Cap) { $headroom = 'over' }
        elseif ([long]$free * 100 -lt [long]$Cap * 5) { $headroom = 'fail' }
        elseif ([long]$free * 100 -lt [long]$Cap * 8) { $headroom = 'warn' }
    }
    @{
        Bytes = $Bytes
        Cap = $Cap
        Percent = $percent
        Free = $free
        FreePercent = $freePercent
        Headroom = $headroom
        Tokens = [int][Math]::Round($Bytes / $script:BytesPerToken)
    }
}

function Get-AgentSoulBaseline {
    <#
    .SYNOPSIS
        Reads build/agent-src/catalog/soul-baseline.psd1: @{ Tag; Souls; Errors }.
    .DESCRIPTION
        Souls maps an agent id to its composed SOUL bytes at the baseline release. A missing file gives an
        empty map and no error; a file that does not load, or a value that is not a positive integer, is an error.
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param([Parameter(Mandatory)][string]$RepoRoot)
    $rel = 'build/agent-src/catalog/soul-baseline.psd1'
    $full = Join-AgentRepoPath (Resolve-AgentFullPath -Path $RepoRoot) $rel
    $souls = [System.Collections.Generic.Dictionary[string, int]]::new([StringComparer]::Ordinal)
    $errors = [System.Collections.Generic.List[object]]::new()
    if (-not [System.IO.File]::Exists($full)) { return @{ Tag = ''; Souls = $souls; Errors = @() } }
    $data = $null
    try { $data = Import-AgentDataFile -FullPath $full -RelativePath $rel }
    catch {
        $errors.Add((New-AgentComposeError $rel 1 "cannot load the SOUL baseline: $(($_.Exception.Message -replace '\s+', ' ').Trim())"))
        return @{ Tag = ''; Souls = $souls; Errors = $errors.ToArray() }
    }
    $tag = if ($data['Tag'] -is [string]) { [string]$data['Tag'] } else { '' }
    $map = $data['Souls']
    if ($map -isnot [hashtable]) {
        $errors.Add((New-AgentComposeError $rel 1 'Souls must be a hashtable of agent id = bytes'))
    }
    else {
        foreach ($key in @($map.Keys)) {
            if ($map[$key] -isnot [int] -or $map[$key] -le 0) {
                $errors.Add((New-AgentComposeError $rel 1 "Souls '$key' must be a positive integer"))
                continue
            }
            $souls[[string]$key] = [int]$map[$key]
        }
    }
    @{ Tag = $tag; Souls = $souls; Errors = $errors.ToArray() }
}

function Format-AgentBudgetTable {
    <#
    .SYNOPSIS
        Formats compose results as the headroom table: agent, bytes, cap, % used, % free, ~tokens.
    #>
    [CmdletBinding()]
    [OutputType([string])]
    param([Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Results)
    $inv = [System.Globalization.CultureInfo]::InvariantCulture
    $format = '{0,-24} {1,7} {2,7} {3,7} {4,7} {5,8}'
    $format -f 'agent', 'bytes', 'cap', '% used', '% free', "`u{2248}tokens"
    foreach ($result in $Results) {
        $budget = Get-AgentSoulBudget -Bytes $result['Bytes'] -Cap $result['SoulCap']
        $percent = $budget['Percent'].ToString('0.0', $inv) + '%'
        $freePercent = $budget['FreePercent'].ToString('0.0', $inv) + '%'
        $row = $format -f $result['Id'], $budget['Bytes'], $budget['Cap'], $percent, $freePercent, $budget['Tokens']
        switch ($budget['Headroom']) {
            'over' { $row += '  OVER CAP' }
            'fail' { $row += '  under 5% free' }
            'warn' { $row += '  under 8% free' }
        }
        $row
    }
    "`u{2248}tokens = bytes/3.8 (estimate)"
}

function Get-AgentFragmentUsage {
    <#
    .SYNOPSIS
        For each fragment id, the agents that include it. Emits @{ Id; Agents } (nested includes
        are listed as "<agent> (nested)").
    #>
    [CmdletBinding()]
    [OutputType([hashtable])]
    param(
        [Parameter(Mandatory)][AllowEmptyCollection()][object[]]$Results,
        [string[]]$FragmentIds = @()
    )
    $ids = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($fragmentId in $FragmentIds) { [void]$ids.Add($fragmentId) }
    foreach ($result in $Results) { foreach ($fragmentId in $result['Included']) { [void]$ids.Add($fragmentId) } }
    $sorted = [string[]]@($ids)
    [Array]::Sort($sorted, [StringComparer]::Ordinal)
    foreach ($fragmentId in $sorted) {
        $users = [System.Collections.Generic.List[string]]::new()
        foreach ($result in $Results) {
            if (Test-AgentInList @($result['Fragments']) $fragmentId) { $users.Add([string]$result['Id']) }
            elseif (Test-AgentInList @($result['Included']) $fragmentId) { $users.Add("$($result['Id']) (nested)") }
        }
        @{ Id = $fragmentId; Agents = $users.ToArray() }
    }
}

Export-ModuleMember -Function @(
    'Resolve-AgentFullPath'
    'ConvertTo-AgentRepoPath'
    'Get-AgentSoulPath'
    'Get-AgentTemplatePath'
    'Get-AgentFragmentPath'
    'Get-AgentFragmentIds'
    'Get-AgentTemplateIds'
    'Get-AgentFamilyRegistry'
    'Set-AgentFamilyContext'
    'Get-AgentFamilyContext'
    'Get-AgentRosterUnion'
    'Get-AgentFamily'
    'Get-AgentFamilyAgent'
    'Resolve-AgentLicenseSource'
    'Get-AgentFamilyLine'
    'Test-AgentFamilyData'
    'Read-AgentSourceFile'
    'Invoke-AgentCompose'
    'Invoke-AgentFamilyCompose'
    'Invoke-AgentReadmeCompose'
    'Format-AgentComposeError'
    'Get-AgentMethodSpans'
    'Test-AgentMethod'
    'Invoke-AgentMethodFixtures'
    'Get-AgentTopicPointers'
    'Read-AgentTopicIndex'
    'Test-AgentSkillUse'
    'Invoke-AgentSkillUseFixtures'
    'Test-AgentDocCounts'
    'Test-AgentAnchors'
    'Compare-AgentSoulText'
    'Write-AgentSoulFile'
    'Get-AgentSoulBudget'
    'Get-AgentSoulBaseline'
    'Format-AgentBudgetTable'
    'Get-AgentFragmentUsage'
)
