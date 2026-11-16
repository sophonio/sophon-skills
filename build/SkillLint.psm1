#Requires -Version 7.0

<#
.SYNOPSIS
    Repo-wide checks for the skills in skills/, run by build/Build-MarketplacePackages.ps1 on every skill.
.DESCRIPTION
    The build script validates the marketplace publishing contract (fields). This module checks what the
    package meets after that: the Sophon runtime, the providers, the marketplace zip inspector and the
    Sophon installer. Data lives in build/catalog/sandbox-python.psd1 (the entrypoint import scan),
    build/catalog/marketplace-rules.psd1 (reserved names, zip limits, permissions, schema subset, folder rule)
    and, shared with the agent lint, build/agent-src/catalog/sophon-tools.psd1 (built-in tool names) and
    build/agent-src/catalog/scan-rules.psd1 (P2 injection literals).

    Every message starts with a stable rule id:

      SKILL-JSON        manifest.json cannot be parsed
      SKILL-TYPE        an explicit manifest type other than skill
      SKILL-RESERVED    a reserved package name (System tier; the Official tier is a warning)
      SKILL-PERMISSIONS the permissions block breaks a marketplace rule
      SKILL-TOOLNAME    a tool name breaks the pattern or the length cap
      SKILL-TOOLDUP     a tool name declared twice in one manifest
      SKILL-COLLISION   a tool name equal to a built-in tool or another skill's tool
      SKILL-WIRE        two tool names equal after '.' -> '_' (the provider wire form)
      SKILL-SCHEMA      a parameter schema outside the supported subset
      SKILL-TOOLPARAM   a parameter named 'tool' (overwritten by the runtime)
      SKILL-INJECTION   a P2 injection literal in a description
      SKILL-IMPORT      an entrypoint line that makes Sophon pip-install something
      SKILL-FUTURE      a __future__ import in the entrypoint
      SKILL-FOLDER      a file or folder outside the folder rule
      SKILL-DOTFILE     a dotfile or dot-folder in the package
      SKILL-SYMLINK     a symlink or reparse point in the skill folder
      SKILL-LOCK        vendor/ does not match vendor.lock.json
      SKILL-NOTICE      a vendored LICENSE that THIRD_PARTY_NOTICES.md does not credit
      SKILL-ZIP         the built archive breaks a zip rule
      SKILL-BUDGET      (warning) a tool description or tool count over budget

    Pure PowerShell 7 with no Windows-only APIs, so it runs in CI on Linux too.
#>

Set-StrictMode -Version Latest

$script:JsonKind = [System.Text.Json.JsonValueKind]
$script:Ordinal = [System.StringComparer]::Ordinal
$script:OrdinalIgnoreCase = [System.StringComparer]::OrdinalIgnoreCase
$script:StrictUtf8 = [System.Text.UTF8Encoding]::new($false, $true)

# What the build script leaves out of every .sophon-skill (CLAUDE.md "Package shape").
$script:ExcludeDirNames = @('__pycache__', 'dist')
$script:ExcludeFileNames = @('.DS_Store', 'Thumbs.db')

# ---------------------------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------------------------

function New-OrdinalSet {
    param([AllowNull()][object[]]$Items, [switch]$IgnoreCase)
    $comparer = if ($IgnoreCase) { $script:OrdinalIgnoreCase } else { $script:Ordinal }
    $set = [System.Collections.Generic.HashSet[string]]::new($comparer)
    foreach ($item in @($Items)) { if ($null -ne $item) { [void]$set.Add([string]$item) } }
    return , $set
}

function Read-JsonElement {
    # Parses a JSON file strictly (no comments, no trailing commas) and returns @{ Root; Error }. The root is a
    # cloned JsonElement, so the document can be disposed here.
    param([Parameter(Mandatory)][string]$Path)
    try {
        $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
        $doc = [System.Text.Json.JsonDocument]::Parse($text, [System.Text.Json.JsonDocumentOptions]::new())
        try { return @{ Root = $doc.RootElement.Clone(); Error = $null } }
        finally { $doc.Dispose() }
    } catch {
        $message = if ($_.Exception.InnerException) { $_.Exception.InnerException.Message } else { $_.Exception.Message }
        return @{ Root = $null; Error = $message }
    }
}

function Get-JsonMember {
    # The named member of a JSON object, or $null when the element is not an object or lacks it.
    param($Element, [Parameter(Mandatory)][string]$Name)
    if ($null -eq $Element -or $Element.ValueKind -ne $script:JsonKind::Object) { return $null }
    $value = [System.Text.Json.JsonElement]::new()
    if ($Element.TryGetProperty($Name, [ref]$value)) { return $value }
    return $null
}

function Get-JsonString {
    # The string value of a member, or $null when it is absent or not a string.
    param($Element, [Parameter(Mandatory)][string]$Name)
    $value = Get-JsonMember $Element $Name
    if ($null -ne $value -and $value.ValueKind -eq $script:JsonKind::String) { return $value.GetString() }
    return $null
}

function Get-JsonItems {
    # The elements of a JSON array member (an empty array when absent or not an array), without unwrapping.
    param($Element, [Parameter(Mandatory)][string]$Name)
    $value = Get-JsonMember $Element $Name
    if ($null -eq $value -or $value.ValueKind -ne $script:JsonKind::Array) { return , @() }
    return , @($value.EnumerateArray())
}

function Get-FileSha256 {
    param([Parameter(Mandatory)][byte[]]$Bytes)
    return [System.Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData($Bytes)).ToLowerInvariant()
}

function Get-RelativePackagePath {
    param([Parameter(Mandatory)][string]$Root, [Parameter(Mandatory)][string]$FullName)
    return $FullName.Substring($Root.Length).TrimStart('\', '/').Replace('\', '/')
}

function ConvertTo-CanonicalEntryPath {
    # Mirrors PackageArchive.NormalizeEntryPath (sophon) and ZipEntryPaths.Normalize (marketplace): '\' -> '/',
    # then null for an empty, rooted, drive-qualified or '.'/'..' path. A directory keeps its trailing '/'.
    param([AllowEmptyString()][string]$Name)
    if ([string]::IsNullOrEmpty($Name)) { return $null }
    $normalized = $Name.Replace('\', '/')
    if ($normalized.StartsWith('/') -or [System.IO.Path]::IsPathRooted($normalized)) { return $null }
    if ($normalized.Length -ge 2 -and [char]::IsAsciiLetter($normalized[0]) -and $normalized[1] -eq ':') { return $null }
    $segments = @($normalized.Split('/', [System.StringSplitOptions]::RemoveEmptyEntries))
    foreach ($segment in $segments) { if ($segment -eq '.' -or $segment -eq '..') { return $null } }
    $joined = $segments -join '/'
    if ($normalized.EndsWith('/')) { return "$joined/" }
    return $joined
}

# ---------------------------------------------------------------------------------------------------------------
# Package contents
# ---------------------------------------------------------------------------------------------------------------

function Test-SkillPackageExclusion {
    <#
    .SYNOPSIS
        True when the build leaves this skill-relative path (forward slashes) out of the .sophon-skill.
    #>
    param([Parameter(Mandatory)][string]$RelativePath)

    $segments = $RelativePath.Split('/')
    for ($i = 0; $i -lt ($segments.Length - 1); $i++) {
        if ($script:ExcludeDirNames -contains $segments[$i]) { return $true }
    }
    $leaf = $segments[$segments.Length - 1]
    if ($script:ExcludeFileNames -contains $leaf) { return $true }
    if ($leaf -like '*.pyc') { return $true }
    return $false
}

function Get-SkillPackageFiles {
    <#
    .SYNOPSIS
        The skill-relative paths (forward slashes, ordinal order) of every file the .sophon-skill holds.
    #>
    param([Parameter(Mandatory)][string]$SkillDir)

    $root = (Resolve-Path -LiteralPath $SkillDir).Path
    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($file in (Get-ChildItem -LiteralPath $root -Recurse -File -Force)) {
        $relative = Get-RelativePackagePath $root $file.FullName
        if (-not (Test-SkillPackageExclusion -RelativePath $relative)) { $paths.Add($relative) }
    }
    $paths.Sort($script:Ordinal)
    return , $paths
}

# ---------------------------------------------------------------------------------------------------------------
# Context: catalogues plus every skill's tool names, loaded once per build
# ---------------------------------------------------------------------------------------------------------------

function New-SkillLintContext {
    <#
    .SYNOPSIS
        Loads the catalogues and the tool names of every skills/*/manifest.json under -SkillsRoot.
    .PARAMETER SkillsRoot
        The folder whose immediate subfolders are skills (skills/ in this repo, a fixture folder in tests).
    .PARAMETER BuildRoot
        The folder holding catalog/ and agent-src/catalog/. Defaults to this module's folder (build/).
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SkillsRoot,
        [string]$BuildRoot = $PSScriptRoot
    )

    $python = Import-PowerShellDataFile -LiteralPath (Join-Path $BuildRoot 'catalog/sandbox-python.psd1')
    $rules = Import-PowerShellDataFile -LiteralPath (Join-Path $BuildRoot 'catalog/marketplace-rules.psd1')
    $tools = Import-PowerShellDataFile -LiteralPath (Join-Path $BuildRoot 'agent-src/catalog/sophon-tools.psd1')
    $scan = Import-PowerShellDataFile -LiteralPath (Join-Path $BuildRoot 'agent-src/catalog/scan-rules.psd1')

    $importToPip = [System.Collections.Generic.Dictionary[string, string]]::new($script:Ordinal)
    foreach ($key in $python.ImportToPip.Keys) { $importToPip[[string]$key] = [string]$python.ImportToPip[$key] }

    # Built-in tools: Allowed plus the exact Restricted names (a '.*' entry is a prefix, not a tool).
    $builtIn = New-OrdinalSet $tools.Allowed
    foreach ($entry in $tools.Restricted) {
        if (-not $entry.EndsWith('.*', [System.StringComparison]::Ordinal)) { [void]$builtIn.Add($entry) }
    }
    $denied = New-OrdinalSet @($tools.Denied.Keys)

    # P2 literals, compiled the way AgentLint.psm1 Get-ScanRules does (SuspiciousPatterns.Scan word ends).
    $literals = [System.Collections.Generic.List[object]]::new()
    foreach ($tier in 'High', 'Medium') {
        foreach ($literal in $scan.P2[$tier]) {
            $first = $literal[0]; $last = $literal[$literal.Length - 1]
            $pre = if ([char]::IsLetterOrDigit($first) -or $first -eq '_') { '(?<![\p{L}\p{Nd}_])' } else { '' }
            $post = if ([char]::IsLetterOrDigit($last) -or $last -eq '_') { '(?![\p{L}\p{Nd}_])' } else { '' }
            $literals.Add([pscustomobject]@{
                    Tier    = $tier
                    Literal = $literal
                    Regex   = [regex]::new($pre + [regex]::Escape($literal) + $post, [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
                })
        }
    }

    # Every owner of every name and wire name: 'built-in' or the skill folder name.
    $owners = [System.Collections.Generic.Dictionary[string, System.Collections.Generic.List[string]]]::new($script:Ordinal)
    $wireOwners = [System.Collections.Generic.Dictionary[string, System.Collections.Generic.List[object]]]::new($script:Ordinal)
    $addOwner = {
        param([string]$Name, [string]$Owner)
        if (-not $owners.ContainsKey($Name)) { $owners[$Name] = [System.Collections.Generic.List[string]]::new() }
        if (-not $owners[$Name].Contains($Owner)) { $owners[$Name].Add($Owner) }
        $wire = $Name.Replace('.', '_')
        if (-not $wireOwners.ContainsKey($wire)) { $wireOwners[$wire] = [System.Collections.Generic.List[object]]::new() }
        $wireOwners[$wire].Add([pscustomobject]@{ Name = $Name; Owner = $Owner })
    }
    foreach ($name in $builtIn) { & $addOwner $name 'built-in' }

    $root = [System.IO.Path]::GetFullPath($SkillsRoot)
    if (Test-Path -LiteralPath $root -PathType Container) {
        foreach ($dir in (Get-ChildItem -LiteralPath $root -Directory | Sort-Object Name)) {
            $manifestPath = Join-Path $dir.FullName 'manifest.json'
            if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { continue }
            $parsed = Read-JsonElement $manifestPath
            if ($null -eq $parsed.Root) { continue }
            $seen = New-OrdinalSet
            foreach ($tool in (Get-JsonItems $parsed.Root 'tools')) {
                $name = Get-JsonString $tool 'name'
                if ([string]::IsNullOrEmpty($name) -or -not $seen.Add($name)) { continue }
                & $addOwner $name $dir.Name
            }
        }
    }

    return [pscustomobject]@{
        SkillsRoot     = $root
        Python         = [pscustomobject]@{
            ImportRegex = [regex]::new($python.ImportPattern)
            Stdlib      = New-OrdinalSet $python.StdlibModules
            Forbidden   = New-OrdinalSet $python.ForbiddenModules
            ImportToPip = $importToPip
        }
        Rules          = $rules
        SystemNames    = New-OrdinalSet $rules.ReservedNames.System -IgnoreCase
        OfficialNames  = New-OrdinalSet $rules.ReservedNames.Official -IgnoreCase
        BuiltInTools   = $builtIn
        DeniedTools    = $denied
        ToolOwners     = $owners
        WireOwners     = $wireOwners
        InjectionRules = $literals
    }
}

# ---------------------------------------------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------------------------------------------

function Test-SkillManifestMirror {
    # The manifest rules the marketplace applies beyond the field contract: type, reserved names, permissions.
    param($Manifest, $Context, $Errors, $Warnings)

    $type = Get-JsonMember $Manifest 'type'
    if ($null -ne $type -and $type.ValueKind -ne $script:JsonKind::Null) {
        $allowed = @($Context.Rules.ManifestTypes)
        if ($type.ValueKind -ne $script:JsonKind::String -or $allowed -cnotcontains $type.GetString()) {
            $Errors.Add("SKILL-TYPE: type must be omitted or one of: $($allowed -join ', ') (the marketplace rejects any other explicit type as manifest.unknown_type)")
        }
    }

    $name = Get-JsonString $Manifest 'name'
    if (-not [string]::IsNullOrEmpty($name)) {
        if ($Context.SystemNames.Contains($name)) {
            $Errors.Add("SKILL-RESERVED: name '$name' is a System-tier reserved package name; nobody can publish it (ReservedPackageNames.cs)")
        } else {
            $prefix = @($Context.Rules.ReservedNames.OfficialPrefixes | Where-Object { $name.StartsWith($_, [System.StringComparison]::OrdinalIgnoreCase) }) | Select-Object -First 1
            if ($Context.OfficialNames.Contains($name) -or $prefix) {
                $Warnings.Add("SKILL-RESERVED: name '$name' is an Official-tier reserved name; only a SuperAdmin smk_ key or JWT can publish a new package under it (never an slk_ key)")
            }
        }
    }

    $permissions = Get-JsonMember $Manifest 'permissions'
    if ($null -eq $permissions -or $permissions.ValueKind -ne $script:JsonKind::Object) { return }
    $memory = Get-JsonMember $permissions 'maxMemoryMb'
    $memoryValue = 0
    if ($null -ne $memory -and $memory.ValueKind -eq $script:JsonKind::Number -and $memory.TryGetInt32([ref]$memoryValue) -and
        $memoryValue -gt $Context.Rules.Permissions.MaxMemoryMb) {
        $Errors.Add("SKILL-PERMISSIONS: permissions.maxMemoryMb $memoryValue exceeds $($Context.Rules.Permissions.MaxMemoryMb)")
    }
    foreach ($entry in (Get-JsonItems $permissions 'network')) {
        if ($entry.ValueKind -ne $script:JsonKind::String) { continue }
        $value = $entry.GetString()
        if ([string]::IsNullOrWhiteSpace($value) -or $value.Contains('://') -or $value.Contains('/') -or $value.Contains(' ') -or
            $value -cnotmatch $Context.Rules.Permissions.HostnamePattern) {
            $Errors.Add("SKILL-PERMISSIONS: permissions.network entry '$value' must be a bare hostname (no scheme or path)")
        }
    }
    foreach ($entry in (Get-JsonItems $permissions 'filesystem')) {
        if ($entry.ValueKind -ne $script:JsonKind::String) { continue }
        $value = $entry.GetString()
        if ([string]::IsNullOrWhiteSpace($value) -or $null -eq (ConvertTo-CanonicalEntryPath $value)) {
            $Errors.Add("SKILL-PERMISSIONS: permissions.filesystem entry '$value' must be a relative path inside the package")
        }
    }
}

function Test-SkillToolNames {
    param($Manifest, [string]$FolderName, $Context, $Errors, $Warnings)

    $pattern = $Context.Rules.ToolName.Pattern
    $maxLength = $Context.Rules.ToolName.MaxLength
    $seen = New-OrdinalSet
    $seenWire = [System.Collections.Generic.Dictionary[string, string]]::new($script:Ordinal)

    foreach ($tool in (Get-JsonItems $Manifest 'tools')) {
        $name = Get-JsonString $tool 'name'
        if ([string]::IsNullOrEmpty($name)) { continue }   # the field contract reports a missing name

        if ($name -cnotmatch $pattern -or $name.Length -gt $maxLength) {
            $Errors.Add("SKILL-TOOLNAME: tool name '$name' must match $pattern and be at most $maxLength characters")
        }
        if (-not $seen.Add($name)) {
            $Errors.Add("SKILL-TOOLDUP: tool name '$name' is declared more than once (Sophon refuses the manifest)")
            continue
        }
        $wire = $name.Replace('.', '_')
        if ($seenWire.ContainsKey($wire)) {
            $Errors.Add("SKILL-WIRE: tools '$($seenWire[$wire])' and '$name' are both '$wire' on the provider wire; every LLM call fails while both are loaded")
        } else {
            $seenWire[$wire] = $name
        }

        if ($Context.DeniedTools.Contains($name)) {
            $Warnings.Add("SKILL-COLLISION: tool '$name' is on the agent lint's Denied list (sophon-tools.psd1); agents in this repo may name it only in a negated statement")
        }

        if ($Context.ToolOwners.ContainsKey($name)) {
            foreach ($owner in $Context.ToolOwners[$name]) {
                if ($owner -ceq $FolderName) { continue }
                $what = if ($owner -ceq 'built-in') { 'the built-in tool' } else { "skills/$owner's tool" }
                $Errors.Add("SKILL-COLLISION: tool '$name' clashes with $what of the same name; Sophon fails the install with TOOL_NAME_CONFLICT and skips the whole skill at startup")
            }
        }
        if ($Context.WireOwners.ContainsKey($wire)) {
            foreach ($other in $Context.WireOwners[$wire]) {
                if ($other.Name -ceq $name -or $other.Owner -ceq $FolderName) { continue }
                $what = if ($other.Owner -ceq 'built-in') { "the built-in tool '$($other.Name)'" } else { "skills/$($other.Owner)'s tool '$($other.Name)'" }
                $Errors.Add("SKILL-WIRE: tool '$name' and $what are both '$wire' on the provider wire; every LLM call fails while both are loaded")
            }
        }
    }
}

function Test-SchemaNode {
    # One node of a parameter schema: keywords, a single string type, string-only enums, items on arrays.
    param($Node, [string]$Label, [string]$Path, $Context, $Errors)

    if ($Node.ValueKind -ne $script:JsonKind::Object) {
        $Errors.Add("SKILL-SCHEMA: $Label ${Path}: a schema must be a JSON object")
        return
    }
    foreach ($keyword in $Context.Rules.Schema.ForbiddenKeywords) {
        if ($null -ne (Get-JsonMember $Node $keyword)) {
            $Errors.Add("SKILL-SCHEMA: $Label ${Path}: '$keyword' is not supported (ToolParameterValidator ignores it and the Gemini cleaner strips it); use one type and describe the alternatives")
        }
    }

    $typeNode = Get-JsonMember $Node 'type'
    $type = $null
    if ($null -eq $typeNode) {
        $Errors.Add("SKILL-SCHEMA: $Label ${Path}: has no 'type'")
    } elseif ($typeNode.ValueKind -ne $script:JsonKind::String) {
        $Errors.Add("SKILL-SCHEMA: $Label ${Path}: 'type' must be one string, not $($typeNode.ValueKind.ToString().ToLowerInvariant()) (Gemini accepts a single type)")
    } else {
        $type = $typeNode.GetString()
        if (@($Context.Rules.Schema.Types) -cnotcontains $type) {
            $Errors.Add("SKILL-SCHEMA: $Label ${Path}: type '$type' is not one of: $($Context.Rules.Schema.Types -join ', ')")
        }
    }

    $enum = Get-JsonMember $Node 'enum'
    if ($null -ne $enum) {
        $values = if ($enum.ValueKind -eq $script:JsonKind::Array) { @($enum.EnumerateArray()) } else { @() }
        $nonString = @($values | Where-Object { $_.ValueKind -ne $script:JsonKind::String })
        if ($enum.ValueKind -ne $script:JsonKind::Array -or $nonString.Count -gt 0 -or ($null -ne $type -and $type -cne 'string')) {
            $Errors.Add("SKILL-SCHEMA: $Label ${Path}: enum must be an array of strings on a type 'string' node (the Gemini cleaner turns other values into strings, which ToolParameterValidator then rejects); use minimum/maximum or list the values in the description")
        }
    }

    if ($type -ceq 'array') {
        $items = Get-JsonMember $Node 'items'
        if ($null -eq $items -or $items.ValueKind -ne $script:JsonKind::Object) {
            $Errors.Add("SKILL-SCHEMA: $Label ${Path}: an array needs an 'items' schema object")
        } else {
            Test-SchemaNode $items $Label "$Path.items" $Context $Errors
        }
    }
    if ($type -ceq 'object') {
        $properties = Get-JsonMember $Node 'properties'
        if ($null -ne $properties) {
            if ($properties.ValueKind -ne $script:JsonKind::Object) {
                $Errors.Add("SKILL-SCHEMA: $Label ${Path}: 'properties' must be an object")
            } else {
                foreach ($property in $properties.EnumerateObject()) {
                    Test-SchemaNode $property.Value $Label "$Path.properties.$($property.Name)" $Context $Errors
                }
            }
        }
        $required = Get-JsonMember $Node 'required'
        if ($null -ne $required) {
            if ($required.ValueKind -ne $script:JsonKind::Array) {
                $Errors.Add("SKILL-SCHEMA: $Label ${Path}: 'required' must be an array of property names")
            } else {
                foreach ($entry in $required.EnumerateArray()) {
                    if ($entry.ValueKind -ne $script:JsonKind::String -or
                        $null -eq $properties -or $properties.ValueKind -ne $script:JsonKind::Object -or
                        $null -eq (Get-JsonMember $properties $entry.GetString())) {
                        $Errors.Add("SKILL-SCHEMA: $Label ${Path}: required entry $($entry.GetRawText()) is not a declared property")
                    }
                }
            }
        }
    }
}

function Test-SkillToolSchemas {
    param($Manifest, $Context, $Errors)

    $reserved = @($Context.Rules.ReservedParameterNames)
    $tools = Get-JsonItems $Manifest 'tools'
    for ($i = 0; $i -lt $tools.Count; $i++) {
        $tool = $tools[$i]
        $name = Get-JsonString $tool 'name'
        $label = if ([string]::IsNullOrEmpty($name)) { "tools[$i]" } else { "tool '$name'" }

        $parameters = Get-JsonMember $tool 'parameters'
        if ($null -eq $parameters -or $parameters.ValueKind -ne $script:JsonKind::Object -or
            (Get-JsonString $parameters 'type') -cne 'object') {
            $Errors.Add("SKILL-SCHEMA: $label parameters must be a JSON object schema with type 'object'")
            continue
        }
        Test-SchemaNode $parameters $label 'parameters' $Context $Errors

        $properties = Get-JsonMember $parameters 'properties'
        foreach ($key in $reserved) {
            if ($null -ne (Get-JsonMember $properties $key)) {
                $Errors.Add("SKILL-TOOLPARAM: $label declares a parameter named '$key'; SandboxedTool overwrites params['$key'] with the tool name on every call, so rename it")
            }
        }
    }
}

function Find-InjectionLiteral {
    # The P2 High and Medium literals in one text, matched as SuspiciousPatterns.Scan does.
    param([AllowEmptyString()][string]$Text, $Context)
    if ([string]::IsNullOrEmpty($Text)) { return @() }
    $normalized = [regex]::Replace($Text, '\p{Cc}', ' ').ToLowerInvariant()
    return @($Context.InjectionRules | Where-Object { $_.Regex.IsMatch($normalized) })
}

function Test-SkillDescriptions {
    # The install preview card lists the skill and every tool description, and that card is a tool result,
    # so Sophon's injection guard scans it (ToolResultIngestion.cs:76-79). Also the budget warnings.
    param($Manifest, $Context, $Errors, $Warnings)

    $texts = [System.Collections.Generic.List[object]]::new()
    $texts.Add(@('description', (Get-JsonString $Manifest 'description')))
    $tools = Get-JsonItems $Manifest 'tools'
    foreach ($tool in $tools) {
        $name = Get-JsonString $tool 'name'
        $description = Get-JsonString $tool 'description'
        $texts.Add(@("tool '$name' description", $description))
        if ($null -ne $description -and $description.Length -gt $Context.Rules.Budget.MaxToolDescriptionChars) {
            $Warnings.Add("SKILL-BUDGET: tool '$name' description is $($description.Length) characters (budget $($Context.Rules.Budget.MaxToolDescriptionChars))")
        }
    }
    if ($tools.Count -gt $Context.Rules.Budget.MaxToolsPerSkill) {
        $Warnings.Add("SKILL-BUDGET: $($tools.Count) tools; the chat, subagent and coding profiles hold at most $($Context.Rules.Budget.MaxToolsPerSkill) core plus pinned tools, so agents reach the rest through tools.search")
    }

    foreach ($pair in $texts) {
        foreach ($hit in (Find-InjectionLiteral $pair[1] $Context)) {
            $Errors.Add("SKILL-INJECTION: $($pair[0]) contains the $($hit.Tier) injection literal '$($hit.Literal)' (SuspiciousPatterns.cs); the install preview card is scanned as a tool result, so rephrase")
        }
    }
}

function Test-SkillRequirementsEmpty {
    # Mirrors SandboxedTool.GetPythonPackages: requirements[] plus the non-comment lines of requirements.txt.
    param([string]$SkillDir, $Manifest)
    foreach ($entry in (Get-JsonItems $Manifest 'requirements')) {
        if ($entry.ValueKind -eq $script:JsonKind::String -and -not [string]::IsNullOrWhiteSpace($entry.GetString())) { return $false }
    }
    $file = Join-Path $SkillDir 'requirements.txt'
    if (Test-Path -LiteralPath $file -PathType Leaf) {
        foreach ($line in [System.IO.File]::ReadAllLines($file)) {
            $trimmed = $line.Trim()
            if ($trimmed.Length -gt 0 -and -not $trimmed.StartsWith('#')) { return $false }
        }
    }
    return $true
}

function Test-SkillEntrypointImports {
    <#
    .SYNOPSIS
        Replays PythonImportResolver on the entrypoint (build/catalog/sandbox-python.psd1).
    #>
    param([string]$SkillDir, $Manifest, $Context, $Errors)

    $language = Get-JsonString $Manifest 'language'
    if ([string]::IsNullOrEmpty($language)) { $language = 'python' }   # SkillManifestParser's default
    if ($language -ne 'python') { return }

    $entrypoint = Get-JsonString $Manifest 'entrypoint'
    if ([string]::IsNullOrWhiteSpace($entrypoint)) { return }
    $path = Join-Path $SkillDir $entrypoint
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return }   # the field contract reports it

    $scanned = Test-SkillRequirementsEmpty $SkillDir $Manifest
    $lines = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8).Split("`n")
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $trimmed = $lines[$i].TrimStart()
        if ($trimmed.Length -eq 0 -or $trimmed[0] -eq '#') { continue }
        $match = $Context.Python.ImportRegex.Match($trimmed)
        if (-not $match.Success) { continue }
        $module = $match.Groups[1].Value
        $where = "${entrypoint}:$($i + 1)"
        if ($Context.Python.Forbidden.Contains($module)) {
            $Errors.Add("SKILL-FUTURE: ${where}: Sophon prepends 'import json, os' and a params line to the entrypoint, so a __future__ import is no longer first and the script fails with SyntaxError")
            continue
        }
        if ($scanned -and -not $Context.Python.Stdlib.Contains($module)) {
            $pip = if ($Context.Python.ImportToPip.ContainsKey($module)) { $Context.Python.ImportToPip[$module] } else { $module }
            $text = $trimmed.TrimEnd()
            if ($text.Length -gt 60) { $text = $text.Substring(0, 60) + '...' }
            $Errors.Add("SKILL-IMPORT: ${where}: '$text' makes Sophon pip-install '$pip' before every call (PythonImportResolver scans every line, docstrings included, when requirements is empty); reword the line, declare the package in requirements, or load the module with importlib")
        }
    }
}

function Test-SkillFolderLayout {
    <#
    .SYNOPSIS
        A flat skill root, plus an optional flat lib/ (.py and .json) and a vendor/ next to vendor.lock.json.
        No dotfiles, no symlinks. Paths the build leaves out (__pycache__/, dist/, *.pyc, ...) are ignored.
    #>
    param([string]$SkillDir, $Context, $Errors)

    $folders = $Context.Rules.Folders
    $root = (Resolve-Path -LiteralPath $SkillDir).Path
    $hasLock = Test-Path -LiteralPath (Join-Path $root $folders.VendorLock) -PathType Leaf

    foreach ($item in (Get-ChildItem -LiteralPath $root -Recurse -Force)) {
        $relative = Get-RelativePackagePath $root $item.FullName
        $segments = @($relative.Split('/'))
        $isDir = $item.PSIsContainer
        if (@($segments | Where-Object { $script:ExcludeDirNames -contains $_ }).Count -gt 0) { continue }
        if (-not $isDir -and (Test-SkillPackageExclusion -RelativePath $relative)) { continue }

        if ($null -ne $item.LinkType -or (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)) {
            $Errors.Add("SKILL-SYMLINK: $relative is a symlink or reparse point; package real files only")
            continue
        }
        if ($item.Name.StartsWith('.')) {
            $Errors.Add("SKILL-DOTFILE: $relative is a dotfile; it would ship in the package (the installer also writes .sophon-origin.json there)")
            continue
        }

        $top = $segments[0]
        if ($segments.Count -eq 1) {
            if (-not $isDir) { continue }
            if ($top -ceq $folders.LibDir) { continue }
            if ($top -ceq $folders.VendorDir) {
                if (-not $hasLock) {
                    $Errors.Add("SKILL-FOLDER: $top/ is allowed only next to $($folders.VendorLock)")
                }
                continue
            }
            $Errors.Add("SKILL-FOLDER: $relative/ is not allowed; a skill is flat apart from $($folders.LibDir)/ and a locked $($folders.VendorDir)/")
            continue
        }
        if ($top -ceq $folders.LibDir) {
            if ($isDir) {
                $Errors.Add("SKILL-FOLDER: $relative/ is not allowed; $($folders.LibDir)/ is flat")
            } elseif ($segments.Count -eq 2 -and @($folders.LibExtensions) -notcontains [System.IO.Path]::GetExtension($item.Name).ToLowerInvariant()) {
                $Errors.Add("SKILL-FOLDER: $relative is not allowed; $($folders.LibDir)/ holds $($folders.LibExtensions -join ' and ') files only")
            }
        }
        # vendor/** is checked against the lock; anything under a refused top folder was reported once above.
    }
}

function Test-SkillVendorLock {
    <#
    .SYNOPSIS
        vendor/ matches vendor.lock.json byte for byte, every upstream LICENSE is credited in
        THIRD_PARTY_NOTICES.md, and nothing vendored trips the moderator review flags.
    #>
    param([string]$SkillDir, $Context, $Errors, $Warnings)

    $folders = $Context.Rules.Folders
    $root = (Resolve-Path -LiteralPath $SkillDir).Path
    $lockPath = Join-Path $root $folders.VendorLock
    if (-not (Test-Path -LiteralPath $lockPath -PathType Leaf)) { return }
    $lockName = $folders.VendorLock

    $parsed = Read-JsonElement $lockPath
    if ($null -eq $parsed.Root) {
        $Errors.Add("SKILL-LOCK: $lockName is not valid JSON: $($parsed.Error)")
        return
    }
    $lock = $parsed.Root
    if ($lock.ValueKind -ne $script:JsonKind::Object) {
        $Errors.Add("SKILL-LOCK: $lockName must be a JSON object")
        return
    }

    $schema = Get-JsonMember $lock 'schemaVersion'
    $schemaValue = 0
    if ($null -eq $schema -or $schema.ValueKind -ne $script:JsonKind::Number -or -not $schema.TryGetInt32([ref]$schemaValue) -or
        $schemaValue -ne $folders.LockSchema) {
        $Errors.Add("SKILL-LOCK: $lockName schemaVersion must be $($folders.LockSchema)")
    }
    $upstream = Get-JsonMember $lock 'upstream'
    foreach ($key in 'repo', 'tag', 'commit', 'version') {
        if ([string]::IsNullOrWhiteSpace((Get-JsonString $upstream $key))) {
            $Errors.Add("SKILL-LOCK: $lockName upstream.$key is missing or empty")
        }
    }
    $commit = Get-JsonString $upstream 'commit'
    if (-not [string]::IsNullOrEmpty($commit) -and $commit -cnotmatch '^[0-9a-f]{40}$') {
        $Errors.Add("SKILL-LOCK: $lockName upstream.commit '$commit' must be a full 40-character lower-case commit id")
    }

    $vendorPrefix = "$($folders.VendorDir)/"
    $locked = New-OrdinalSet
    $lockedFolded = New-OrdinalSet -IgnoreCase
    $previous = $null
    foreach ($entry in (Get-JsonItems $lock 'files')) {
        $path = Get-JsonString $entry 'path'
        $sha = Get-JsonString $entry 'sha256'
        $bytesNode = Get-JsonMember $entry 'bytes'
        $expectedBytes = [long]-1
        if ([string]::IsNullOrEmpty($path)) {
            $Errors.Add("SKILL-LOCK: $lockName files[] entry has no path")
            continue
        }
        if (-not $path.StartsWith($vendorPrefix, [System.StringComparison]::Ordinal) -or
            (ConvertTo-CanonicalEntryPath $path) -cne $path -or $path.EndsWith('/')) {
            $Errors.Add("SKILL-LOCK: $lockName path '$path' must be a canonical forward-slash path under $vendorPrefix")
            continue
        }
        if ($null -ne $previous -and [string]::CompareOrdinal($previous, $path) -ge 0) {
            $Errors.Add("SKILL-LOCK: $lockName files[] must be sorted ordinal by path with no duplicates ('$path' follows '$previous')")
        }
        $previous = $path
        if (-not $lockedFolded.Add($path)) {
            $Errors.Add("SKILL-LOCK: $lockName path '$path' differs from another only by case; the installer rejects case-insensitive duplicates")
        }
        [void]$locked.Add($path)
        if ([string]::IsNullOrEmpty($sha) -or $sha -cnotmatch '^[0-9a-f]{64}$') {
            $Errors.Add("SKILL-LOCK: $lockName '$path' sha256 must be 64 lower-case hex characters")
        }
        if ($null -eq $bytesNode -or $bytesNode.ValueKind -ne $script:JsonKind::Number -or -not $bytesNode.TryGetInt64([ref]$expectedBytes) -or $expectedBytes -lt 0) {
            $Errors.Add("SKILL-LOCK: $lockName '$path' bytes must be a non-negative integer")
        }
        if (Test-SkillPackageExclusion -RelativePath $path) {
            $Errors.Add("SKILL-LOCK: '$path' is locked but the build leaves it out of the package (excluded name)")
        }
        $extension = [System.IO.Path]::GetExtension($path).ToLowerInvariant()
        if (@($Context.Rules.Vendor.DeniedExtensions) -contains $extension) {
            $Errors.Add("SKILL-LOCK: '$path' has a script or native-binary extension ($extension); the marketplace flags the package for moderators, so leave it out of the vendored set")
        }

        $full = Join-Path $root $path
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            $Errors.Add("SKILL-LOCK: '$path' is in $lockName but missing on disk")
            continue
        }
        $bytes = [System.IO.File]::ReadAllBytes($full)
        if ($expectedBytes -ge 0 -and $bytes.LongLength -ne $expectedBytes) {
            $Errors.Add("SKILL-LOCK: '$path' is $($bytes.LongLength) bytes, $lockName says $expectedBytes")
        }
        if (-not [string]::IsNullOrEmpty($sha) -and (Get-FileSha256 $bytes) -cne $sha) {
            $Errors.Add("SKILL-LOCK: '$path' sha256 does not match $lockName (vendored files are byte-identical upstream files; re-sync instead of editing)")
        }
        if ([Array]::IndexOf[byte]($bytes, [byte]0) -ge 0) {
            $Errors.Add("SKILL-LOCK: '$path' contains a NUL byte; the marketplace treats it as binary")
        } else {
            try { [void]$script:StrictUtf8.GetString($bytes) }
            catch { $Errors.Add("SKILL-LOCK: '$path' is not valid UTF-8; the marketplace treats it as binary") }
        }
        if ($bytes.LongLength -gt $Context.Rules.Vendor.PreviewCapBytes) {
            $Warnings.Add("SKILL-LOCK: '$path' is $($bytes.LongLength) bytes, over the $($Context.Rules.Vendor.PreviewCapBytes)-byte moderator preview cap; a reviewer sees it truncated")
        }
    }
    if ($locked.Count -eq 0) {
        $Errors.Add("SKILL-LOCK: $lockName files[] is missing or empty")
    }

    $vendorDir = Join-Path $root $folders.VendorDir
    if (Test-Path -LiteralPath $vendorDir -PathType Container) {
        foreach ($file in (Get-ChildItem -LiteralPath $vendorDir -Recurse -File -Force)) {
            $relative = Get-RelativePackagePath $root $file.FullName
            if (Test-SkillPackageExclusion -RelativePath $relative) { continue }
            if (-not $locked.Contains($relative)) {
                $Errors.Add("SKILL-LOCK: '$relative' is under $vendorPrefix but not in $lockName")
            }
        }
    } else {
        $Errors.Add("SKILL-LOCK: $lockName exists but $vendorPrefix does not")
    }

    foreach ($entry in (Get-JsonItems $lock 'generated')) {
        $path = Get-JsonString $entry 'path'
        $sha = Get-JsonString $entry 'sha256'
        if ([string]::IsNullOrEmpty($path) -or $path.StartsWith($vendorPrefix, [System.StringComparison]::Ordinal) -or
            (ConvertTo-CanonicalEntryPath $path) -cne $path) {
            $Errors.Add("SKILL-LOCK: $lockName generated[] path '$path' must be a canonical path outside $vendorPrefix")
            continue
        }
        $full = Join-Path $root $path
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) {
            $Errors.Add("SKILL-LOCK: generated file '$path' is in $lockName but missing on disk")
        } elseif ((Get-FileSha256 ([System.IO.File]::ReadAllBytes($full))) -cne $sha) {
            $Errors.Add("SKILL-LOCK: generated file '$path' sha256 does not match $lockName; re-run the generator and the sync")
        }
    }

    # One folder per upstream project, each with its LICENSE, each credited in THIRD_PARTY_NOTICES.md.
    if (-not (Test-Path -LiteralPath $vendorDir -PathType Container)) { return }
    $noticesPath = Join-Path $root $folders.Notices
    $notices = if (Test-Path -LiteralPath $noticesPath -PathType Leaf) { [System.IO.File]::ReadAllText($noticesPath) } else { $null }
    if ($null -eq $notices) {
        $Errors.Add("SKILL-NOTICE: $($folders.Notices) is required next to a vendored tree")
    }
    foreach ($file in (Get-ChildItem -LiteralPath $vendorDir -File -Force)) {
        $Errors.Add("SKILL-FOLDER: $vendorPrefix$($file.Name) is not allowed; $vendorPrefix holds one folder per upstream project")
    }
    foreach ($project in (Get-ChildItem -LiteralPath $vendorDir -Directory -Force)) {
        $license = Join-Path $project.FullName 'LICENSE'
        $where = "$vendorPrefix$($project.Name)/LICENSE"
        if (-not (Test-Path -LiteralPath $license -PathType Leaf)) {
            $Errors.Add("SKILL-NOTICE: $where is missing; vendor the upstream LICENSE with the code")
            continue
        }
        $copyright = @([System.IO.File]::ReadAllLines($license) | Where-Object { $_ -match '^\s*Copyright\b' }) | Select-Object -First 1
        if ($null -eq $copyright) {
            $Errors.Add("SKILL-NOTICE: $where has no Copyright line")
        } elseif ($null -ne $notices -and -not $notices.Contains($copyright.Trim(), [System.StringComparison]::Ordinal)) {
            $Errors.Add("SKILL-NOTICE: $($folders.Notices) does not contain '$($copyright.Trim())' from $where")
        }
    }
}

# ---------------------------------------------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------------------------------------------

function Invoke-SkillLint {
    <#
    .SYNOPSIS
        Runs every source check on one skill folder, adding to the caller's error and warning lists.
    .PARAMETER FolderName
        The skill's folder name under the skills root; collisions with this owner are not reported.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SkillDir,
        [Parameter(Mandatory)][string]$FolderName,
        [Parameter(Mandatory)]$Context,
        [Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.Generic.List[string]]$Errors,
        [Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.Generic.List[string]]$Warnings
    )

    $SkillDir = (Resolve-Path -LiteralPath $SkillDir).Path
    $manifestPath = Join-Path $SkillDir 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { return }
    $parsed = Read-JsonElement $manifestPath
    if ($null -eq $parsed.Root -or $parsed.Root.ValueKind -ne $script:JsonKind::Object) {
        $Errors.Add("SKILL-JSON: manifest.json cannot be read as a JSON object: $($parsed.Error)")
        return
    }
    $manifest = $parsed.Root

    Test-SkillManifestMirror $manifest $Context $Errors $Warnings
    Test-SkillToolNames $manifest $FolderName $Context $Errors $Warnings
    Test-SkillToolSchemas $manifest $Context $Errors
    Test-SkillDescriptions $manifest $Context $Errors $Warnings
    Test-SkillEntrypointImports $SkillDir $manifest $Context $Errors
    Test-SkillFolderLayout $SkillDir $Context $Errors
    Test-SkillVendorLock $SkillDir $Context $Errors $Warnings
}

function Test-SkillArchive {
    <#
    .SYNOPSIS
        Replays the zip checks of the Sophon installer (PackageArchive.cs) and the marketplace (ZipInspector.cs)
        on a built .sophon-skill, and, with -ExpectedEntries, checks it holds exactly those files.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ArchivePath,
        [Parameter(Mandatory)]$Context,
        [Parameter(Mandatory)][AllowEmptyCollection()][System.Collections.Generic.List[string]]$Errors,
        [AllowNull()][string[]]$ExpectedEntries
    )

    $ArchivePath = (Resolve-Path -LiteralPath $ArchivePath).Path
    $zip = $Context.Rules.Zip
    $size = (Get-Item -LiteralPath $ArchivePath).Length
    if ($size -gt $zip.MaxPackageBytes) {
        $Errors.Add("SKILL-ZIP: the package is $size bytes, over the $($zip.MaxPackageBytes)-byte upload cap")
    }

    try {
        $archive = [System.IO.Compression.ZipFile]::OpenRead($ArchivePath)
    } catch {
        $Errors.Add("SKILL-ZIP: not a readable zip archive: $($_.Exception.Message)")
        return
    }
    try {
        if ($archive.Entries.Count -gt $zip.MaxEntries) {
            $Errors.Add("SKILL-ZIP: $($archive.Entries.Count) entries, over the installer's $($zip.MaxEntries)-entry cap")
        }
        $seen = New-OrdinalSet -IgnoreCase
        $files = New-OrdinalSet
        [long]$totalUncompressed = 0
        [long]$totalCompressed = 0
        foreach ($entry in $archive.Entries) {
            $name = $entry.FullName
            $canonical = ConvertTo-CanonicalEntryPath $name
            if ($null -eq $canonical) {
                $Errors.Add("SKILL-ZIP: entry '$name' has an unsafe path (empty, rooted, drive-qualified or '..')")
                continue
            }
            if ($name -cne $canonical) {
                $Errors.Add("SKILL-ZIP: entry '$name' is not a canonical forward-slash name")
            }
            if ((($entry.ExternalAttributes -shr 16) -band $zip.SymlinkModeMask) -eq $zip.SymlinkMode) {
                $Errors.Add("SKILL-ZIP: entry '$canonical' is a symlink entry; the installer rejects the package")
            }
            if ([string]::IsNullOrEmpty($entry.Name)) { continue }   # directory pseudo-entry
            if (-not $seen.Add($canonical)) {
                $Errors.Add("SKILL-ZIP: entry '$canonical' duplicates another entry ignoring case")
            }
            [void]$files.Add($canonical)
            if ($entry.Length -gt $zip.MaxEntryUncompressedBytes) {
                $Errors.Add("SKILL-ZIP: entry '$canonical' is $($entry.Length) bytes uncompressed, over the $($zip.MaxEntryUncompressedBytes)-byte cap")
            }
            $totalUncompressed += $entry.Length
            $totalCompressed += $entry.CompressedLength
        }
        if ($totalUncompressed -gt $zip.MaxTotalUncompressedBytes) {
            $Errors.Add("SKILL-ZIP: $totalUncompressed bytes uncompressed in total, over the $($zip.MaxTotalUncompressedBytes)-byte cap")
        }
        if ($totalUncompressed -gt 0) {
            $ratio = if ($totalCompressed -eq 0) { [double]::PositiveInfinity } else { [double]$totalUncompressed / $totalCompressed }
            if ($ratio -gt $zip.MaxCompressionRatio) {
                $Errors.Add("SKILL-ZIP: compression ratio $($ratio.ToString('F1', [cultureinfo]::InvariantCulture)):1 exceeds $($zip.MaxCompressionRatio):1")
            }
        }
        if (-not $files.Contains('manifest.json')) {
            $Errors.Add('SKILL-ZIP: manifest.json is not at the archive root')
        }
        if ($null -ne $ExpectedEntries) {
            $expected = New-OrdinalSet $ExpectedEntries
            foreach ($path in $expected) {
                if (-not $files.Contains($path)) { $Errors.Add("SKILL-ZIP: '$path' is missing from the archive") }
            }
            foreach ($path in $files) {
                if (-not $expected.Contains($path)) { $Errors.Add("SKILL-ZIP: '$path' is in the archive but not in the skill folder") }
            }
        }
    } finally {
        $archive.Dispose()
    }
}

Export-ModuleMember -Function @(
    'New-SkillLintContext', 'Invoke-SkillLint', 'Test-SkillArchive', 'Test-SkillPackageExclusion',
    'Get-SkillPackageFiles', 'Find-InjectionLiteral'
)
