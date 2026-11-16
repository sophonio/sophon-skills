#Requires -Version 7.0

<#
.SYNOPSIS
    Builds Sophon Marketplace upload artifacts (.sophon-skill packages) from this repo's
    open-source skill sources.
.DESCRIPTION
    Discovers skill folders under skills/<skill>/ — any immediate subdirectory of skills/ that
    contains a manifest.json. For each discovered skill, validates manifest.json against the
    marketplace publishing contract (name/version/author/license/description/runtime/entrypoint/
    tools/tags/category/README/LICENSE), then — only if that skill validates clean — zips the
    folder CONTENTS (no wrapping folder) into <OutputDir>/<name>-<version>.sophon-skill.

    Each skill then goes through the repo-wide checks in build/SkillLint.psm1 (entrypoint import scan,
    tool-name and wire-name collisions across every skill and the built-in catalogue, the parameter
    schema subset, reserved names and permissions, the folder rule, the vendor lock, description
    injection literals). A skill that passes is zipped and the archive is checked against the Sophon
    installer's and the marketplace's zip rules; with -ValidateOnly the archive goes to a temporary
    folder and is deleted afterwards.

    Validation collects ALL errors per skill (does not stop at the first). Skills that fail
    validation are skipped for packaging but the run continues to build every other skill.

    A SHA256 hash (lowercase hex) is printed for every artifact produced, for verifying manual
    uploads to the marketplace. A summary table is printed at the end, followed by any warnings.

    Exit code is 1 if ANY skill failed validation, 0 otherwise (packages that did validate are
    still written to disk even when the overall run exits 1).

    NOTE: Sophon plugins (.sophon-plugin, .NET gRPC) are a separate, compiled packaging path and
    are NOT handled here — this script packages skills only.
.PARAMETER RepoRoot
    Repository root. Defaults to one level up from this script's directory (build/..).
.PARAMETER OutputDir
    Directory to write .sophon-skill artifacts into. Defaults to <RepoRoot>/dist. Existing
    artifacts with the same name are overwritten silently.
.PARAMETER Skills
    Optional list of skill folder names (under skills/) to build. Empty (default) means every
    directory under skills/ that contains a manifest.json.
.PARAMETER ValidateOnly
    Validate every skill and print the summary, but do NOT produce .sophon-skill archives in
    -OutputDir (each archive is built in a temporary folder for the zip checks, then deleted). Used
    by CI to fail a PR on any manifest/contract violation without writing build output. Exit code is
    still 1 if any skill failed validation.
.EXAMPLE
    pwsh -File build/Build-MarketplacePackages.ps1

    Validates and packages every skill under skills/ into dist/.
.EXAMPLE
    pwsh -File build/Build-MarketplacePackages.ps1 -ValidateOnly

    Validates every skill and fails (exit 1) on any contract violation, without writing artifacts.
.EXAMPLE
    pwsh -File build/Build-MarketplacePackages.ps1 -Skills jira,confluence

    Validates and packages only the jira and confluence skills.
#>

[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')),
    [string]$OutputDir = (Join-Path $RepoRoot 'dist'),
    [string[]]$Skills = @(),
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

Import-Module (Join-Path $PSScriptRoot 'SkillLint.psm1') -Force

$ValidRuntimes    = @('python', 'csharp', 'sandbox')
$ValidRiskLevels  = @('none', 'low', 'medium', 'high', 'critical')
$ValidCategories  = @('utility', 'productivity', 'communication', 'data', 'development', 'integration', 'ai', 'automation', 'other')

# --- integration / credentials contract -------------------------------------------------------
# These mirror what the Sophon runtime actually consumes, NOT the marketplace publishing contract
# (the marketplace stores both blocks verbatim in RawJson and never parses them). Sources:
#   ValidFieldTypes             <- Sophon.Dashboard connections.tsx FieldDefinition.type union
#   ValidAuthTypes              <- Sophon.Core/Credentials/IConnectionService.cs ServiceDefinition
#   ValidIntegrationCategories  <- connections.tsx category grouping (an unlisted category renders
#                                  in no group, making the connection card unreachable)
#   ValidCredentialAccess       <- Sophon.Skills/CredentialAccess.cs
$ValidFieldTypes            = @('text', 'secret', 'url', 'email', 'number', 'select')
$ValidAuthTypes             = @('custom', 'oauth2', 'static_token')
$ValidIntegrationCategories = @('cloud', 'developer', 'integration', 'messaging')
$ValidCredentialAccess      = @('injected', 'proxy', 'none')
# "proxy" parses but delivers nothing brokered — the broker described in the Sophon security docs
# does not exist, so a skill that reads credentials from `params` must declare "injected".
$DeliveringCredentialAccess = @('injected')
# SandboxedTool overwrites params["tool"] unconditionally, so it can never carry a credential (nor a
# tool argument: SkillLint reports a parameter named `tool` as SKILL-TOOLPARAM).
$ReservedParamKeys          = @('tool')
$MaxReadmeBytes   = 65536
$MaxDescriptionLength = 2000
$MaxTagCount      = 10
$MaxTagLength     = 32

function Get-JsonProperty {
    # Safe property access on a ConvertFrom-Json object under Set-StrictMode:
    # returns $null instead of throwing when the property is absent.
    param(
        [Parameter(Mandatory)] [AllowNull()] $InputObject,
        [Parameter(Mandatory)] [string]$Name
    )
    if ($null -eq $InputObject) { return $null }
    $prop = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $prop) { return $null }
    return $prop.Value
}

function Get-JsonArray {
    # Reads an array property WITHOUT the pipeline's single-element unwrapping. This matters:
    # every credentials[] in this repo has length 1, and many integration.fields[] do too, so
    # returning them through the pipeline would silently hand back a scalar.
    param(
        [Parameter(Mandatory)] [AllowNull()] $InputObject,
        [Parameter(Mandatory)] [string]$Name
    )
    if ($null -eq $InputObject) { return , @() }
    $prop = $InputObject.PSObject.Properties[$Name]
    if ($null -eq $prop -or $null -eq $prop.Value) { return , @() }
    return , @($prop.Value)
}

function Test-JsonHasProperty {
    param(
        [Parameter(Mandatory)] [AllowNull()] $InputObject,
        [Parameter(Mandatory)] [string]$Name
    )
    if ($null -eq $InputObject) { return $false }
    return $null -ne $InputObject.PSObject.Properties[$Name]
}

function Get-PythonModuleScopeParamKeys {
    # Deliberately a line scanner, not a Python parser. Repo convention is that credentials are
    # read at module scope and tool arguments inside handler functions (see skills/todoist/main.py).
    # A line counts as module scope when the most recent column-0 statement did not open a
    # def/class block.
    param([Parameter(Mandatory)] [string]$Path)

    $keys = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $keys }

    $inBlock = $false
    foreach ($line in (Get-Content -LiteralPath $Path -Encoding utf8)) {
        if ($line -match '^(async\s+def|def|class)\s') { $inBlock = $true }
        elseif ($line -match '^\S') { $inBlock = $false }
        if ($inBlock) { continue }

        foreach ($m in [regex]::Matches($line, 'params\s*\.\s*get\(\s*["'']([^"'']+)["'']')) {
            [void]$keys.Add($m.Groups[1].Value)
        }
        foreach ($m in [regex]::Matches($line, 'params\s*\[\s*["'']([^"'']+)["'']\s*\]')) {
            [void]$keys.Add($m.Groups[1].Value)
        }
    }
    return $keys
}

function Test-SkillIntegration {
    # Validates the `integration` + `credentials` blocks against what the Sophon runtime consumes.
    # These blocks were previously unvalidated and undocumented, which is how every skill in the
    # catalogue ended up declaring an access mode that silently withheld its credentials.
    param(
        [Parameter(Mandatory)] [string]$SkillDir,
        [Parameter(Mandatory)] [string]$FolderName,
        [Parameter(Mandatory)] $Manifest,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Errors,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Warnings
    )

    $integration = Get-JsonProperty $Manifest 'integration'
    $credentials = Get-JsonArray $Manifest 'credentials'
    $hasIntegration = $null -ne $integration
    $hasCredentials = $credentials.Count -gt 0

    # Both or neither: an integration with no credential entry is never gated, and a credential
    # with no integration block has no connection form to collect it.
    if ($hasIntegration -and -not $hasCredentials) {
        $Errors.Add('integration block is present but credentials[] is missing or empty')
        return
    }
    if ($hasCredentials -and -not $hasIntegration) {
        $Errors.Add('credentials[] is present but the integration block is missing')
        return
    }
    if (-not $hasIntegration) { return }

    $service = Get-JsonProperty $integration 'service'
    if ([string]::IsNullOrWhiteSpace($service)) {
        $Errors.Add('integration.service is missing or empty')
    } elseif ($service -cnotmatch '^[a-z0-9][a-z0-9-]{1,63}$') {
        $Errors.Add("integration.service '$service' does not match ^[a-z0-9][a-z0-9-]{1,63}`$")
    }

    $authType = Get-JsonProperty $integration 'authType'
    if ([string]::IsNullOrWhiteSpace($authType)) {
        $Errors.Add('integration.authType is missing')
    } elseif ($ValidAuthTypes -cnotcontains $authType) {
        $Errors.Add("integration.authType '$authType' is not one of: $($ValidAuthTypes -join ', ')")
    } elseif ($authType -ceq 'oauth2') {
        foreach ($required in @('authorizeUrl', 'tokenUrl')) {
            if ([string]::IsNullOrWhiteSpace((Get-JsonProperty $integration $required))) {
                $Errors.Add("integration.authType is 'oauth2' but integration.$required is missing")
            }
        }
    }

    $intCategory = Get-JsonProperty $integration 'category'
    if ([string]::IsNullOrWhiteSpace($intCategory)) {
        $Errors.Add('integration.category is missing')
    } elseif ($ValidIntegrationCategories -cnotcontains $intCategory) {
        $Errors.Add("integration.category '$intCategory' is not one of: $($ValidIntegrationCategories -join ', ') " +
            '(note this is the connections-page grouping, not the top-level marketplace category)')
    }

    # --- fields ---
    $fields = Get-JsonArray $integration 'fields'
    if ($fields.Count -eq 0) {
        $Errors.Add('integration.fields[] is missing or empty')
    }

    $fieldKeys = [System.Collections.Generic.List[string]]::new()
    foreach ($field in $fields) {
        $key = Get-JsonProperty $field 'key'
        if ([string]::IsNullOrWhiteSpace($key)) {
            $Errors.Add('integration.fields[] entry is missing key')
            continue
        }
        if ($key -cnotmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
            $Errors.Add("integration.fields[].key '$key' is not a valid identifier")
        }
        if ($fieldKeys -ccontains $key) {
            $Errors.Add("integration.fields[].key '$key' is declared more than once")
        }
        if ($ReservedParamKeys -ccontains $key) {
            $Errors.Add("integration.fields[].key '$key' is reserved by the runtime and would be overwritten")
        }
        $fieldKeys.Add($key)

        if ([string]::IsNullOrWhiteSpace((Get-JsonProperty $field 'label'))) {
            $Errors.Add("integration.fields[].key '$key' is missing label")
        }

        $type = Get-JsonProperty $field 'type'
        if ([string]::IsNullOrWhiteSpace($type)) {
            $Errors.Add("integration.fields[].key '$key' is missing type")
        } elseif ($ValidFieldTypes -cnotcontains $type) {
            $Errors.Add("integration.fields[].key '$key' has type '$type'; must be one of: $($ValidFieldTypes -join ', ')")
        } elseif ($type -ceq 'select' -and (Get-JsonArray $field 'options').Count -eq 0) {
            $Errors.Add("integration.fields[].key '$key' has type 'select' but declares no options[]")
        }
    }

    # --- credentials ---
    foreach ($cred in $credentials) {
        $credService = Get-JsonProperty $cred 'service'
        if ([string]::IsNullOrWhiteSpace($credService)) {
            $Errors.Add('credentials[].service is missing or empty')
        } elseif ($credService -cne $service) {
            $Errors.Add("credentials[].service '$credService' does not equal integration.service '$service'; " +
                'the runtime looks the stored credential up by this exact string')
        }

        $access = Get-JsonProperty $cred 'access'
        if ([string]::IsNullOrWhiteSpace($access)) {
            $Errors.Add('credentials[].access is missing')
        } elseif ($ValidCredentialAccess -cnotcontains $access) {
            $Errors.Add("credentials[].access '$access' is not one of: $($ValidCredentialAccess -join ', ')")
        }
    }

    # --- entrypoint cross-check ---
    $entrypoint = Get-JsonProperty $Manifest 'entrypoint'
    if ([string]::IsNullOrWhiteSpace($entrypoint)) { return }
    $entrypointPath = Join-Path $SkillDir $entrypoint
    if (-not (Test-Path -LiteralPath $entrypointPath -PathType Leaf)) { return }

    $toolParamNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($tool in (Get-JsonArray $Manifest 'tools')) {
        $props = Get-JsonProperty (Get-JsonProperty $tool 'parameters') 'properties'
        if ($null -eq $props) { continue }
        foreach ($p in $props.PSObject.Properties) { [void]$toolParamNames.Add($p.Name) }
    }

    $moduleKeys = Get-PythonModuleScopeParamKeys $entrypointPath
    $credentialReads = @($moduleKeys | Where-Object {
            $ReservedParamKeys -cnotcontains $_ -and -not $toolParamNames.Contains($_)
        })

    foreach ($read in $credentialReads) {
        if ($fieldKeys -cnotcontains $read) {
            $Errors.Add("$entrypoint reads params['$read'] at module scope but integration.fields[] does not declare it; " +
                'the runtime delivers credential fields under their exact manifest key')
        }
    }

    # The rule that would have caught this whole bug class: a skill that reads its credentials out
    # of `params` only works when the manifest asks for them to be delivered.
    if ($credentialReads.Count -gt 0) {
        foreach ($cred in $credentials) {
            $access = Get-JsonProperty $cred 'access'
            if (-not [string]::IsNullOrWhiteSpace($access) -and $DeliveringCredentialAccess -cnotcontains $access) {
                $Errors.Add("$entrypoint reads credential fields from params at module scope, but " +
                    "credentials[].access is '$access'; only $($DeliveringCredentialAccess -join '/') delivers them")
            }
        }
    }

    $entrypointText = Get-Content -LiteralPath $entrypointPath -Raw -Encoding utf8
    foreach ($key in $fieldKeys) {
        if ($entrypointText -notmatch [regex]::Escape("`"$key`"") -and
            $entrypointText -notmatch [regex]::Escape("'$key'")) {
            $Warnings.Add("integration.fields[].key '$key' is never read by $entrypoint (dead field on the connection form)")
        }
    }

    foreach ($field in $fields) {
        $key = Get-JsonProperty $field 'key'
        if ([string]::IsNullOrWhiteSpace($key)) { continue }
        $required = Get-JsonProperty $field 'required'
        if ($required -eq $true -and $toolParamNames.Contains($key)) {
            $Warnings.Add("integration.fields[].key '$key' is required but a tool declares a parameter of the same name; " +
                'a caller-supplied argument shadows the stored value for non-secret fields')
        }
    }
}

function Test-SkillManifest {
    # Validates one skill's manifest + supporting files. Mutates the caller-supplied
    # $Errors/$Warnings lists so the caller can decide whether to package the skill.
    param(
        [Parameter(Mandatory)] [string]$SkillDir,
        [Parameter(Mandatory)] [string]$FolderName,
        [Parameter(Mandatory)] $Manifest,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Errors,
        [Parameter(Mandatory)] [AllowEmptyCollection()] [System.Collections.Generic.List[string]]$Warnings
    )

    $name = Get-JsonProperty $Manifest 'name'
    if ([string]::IsNullOrWhiteSpace($name)) {
        $Errors.Add('name is missing or empty')
    } else {
        if ($name -cnotmatch '^[a-z0-9][a-z0-9-]{1,63}$') {
            $Errors.Add("name '$name' does not match required pattern ^[a-z0-9][a-z0-9-]{1,63}`$")
        }
        if ($name -cne $FolderName) {
            $Errors.Add("name '$name' does not match folder name '$FolderName'")
        }
    }

    $version = Get-JsonProperty $Manifest 'version'
    if ([string]::IsNullOrWhiteSpace($version)) {
        $Errors.Add('version is missing or empty')
    } elseif ($version -cnotmatch '^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$') {
        $Errors.Add("version '$version' does not match required semver pattern")
    }

    $author = Get-JsonProperty $Manifest 'author'
    if ([string]::IsNullOrWhiteSpace($author)) {
        $Errors.Add('author is missing or empty')
    }

    $license = Get-JsonProperty $Manifest 'license'
    if ([string]::IsNullOrWhiteSpace($license)) {
        $Errors.Add('license is missing or empty')
    }

    $description = Get-JsonProperty $Manifest 'description'
    if ($null -eq $description) {
        $Errors.Add('description is missing')
    } elseif ($description -isnot [string]) {
        $Errors.Add("description must be a string (actual type: $($description.GetType().Name))")
    } elseif ($description.Length -gt $MaxDescriptionLength) {
        $Errors.Add("description exceeds $MaxDescriptionLength characters (actual: $($description.Length))")
    }

    $runtime = Get-JsonProperty $Manifest 'runtime'
    if ([string]::IsNullOrWhiteSpace($runtime)) {
        $Errors.Add('runtime is missing or empty')
    } elseif ($ValidRuntimes -cnotcontains $runtime) {
        $Errors.Add("runtime '$runtime' is not one of: $($ValidRuntimes -join ', ')")
    }

    $entrypoint = Get-JsonProperty $Manifest 'entrypoint'
    if ([string]::IsNullOrWhiteSpace($entrypoint)) {
        $Errors.Add('entrypoint is missing or empty')
    } else {
        $entrypointPath = Join-Path $SkillDir $entrypoint
        if (-not (Test-Path -LiteralPath $entrypointPath -PathType Leaf)) {
            $Errors.Add("entrypoint file '$entrypoint' does not exist in the skill folder")
        } elseif (Test-ZipExclusion -RelativePath ($entrypoint -replace '\\', '/')) {
            $Errors.Add("entrypoint '$entrypoint' would be excluded from the package")
        }
    }

    $tools = Get-JsonProperty $Manifest 'tools'
    $toolsArray = @($tools | Where-Object { $null -ne $_ })
    if ($null -eq $tools -or $toolsArray.Count -eq 0) {
        $Errors.Add('tools is missing or empty')
    } else {
        for ($i = 0; $i -lt $toolsArray.Count; $i++) {
            $tool = $toolsArray[$i]
            $toolName = Get-JsonProperty $tool 'name'
            $toolDescription = Get-JsonProperty $tool 'description'
            $toolRisk = Get-JsonProperty $tool 'riskLevel'
            $label = if ([string]::IsNullOrWhiteSpace($toolName)) { "tools[$i]" } else { "tool '$toolName'" }

            if ([string]::IsNullOrWhiteSpace($toolName)) {
                $Errors.Add("$label is missing a name")
            }
            if ([string]::IsNullOrWhiteSpace($toolDescription)) {
                $Errors.Add("$label has a missing or empty description")
            }
            if ([string]::IsNullOrWhiteSpace($toolRisk)) {
                $Errors.Add("$label is missing riskLevel")
            } elseif ($ValidRiskLevels -cnotcontains $toolRisk) {
                $Errors.Add("$label has invalid riskLevel '$toolRisk' (must be one of: $($ValidRiskLevels -join ', '), case-sensitive)")
            }
        }
    }

    # NOTE: intentionally not using Get-JsonProperty here — its `return $prop.Value` sends the
    # value through the pipeline, which silently unwraps a single-element JSON array (e.g.
    # ["gmail"]) into a bare string, making it indistinguishable from a genuine scalar
    # ("tags": "gmail"). Reading the property value directly (no function return in between)
    # preserves the real type so the array-vs-scalar check below is accurate.
    $tagsProp = $Manifest.PSObject.Properties['tags']
    $tags = $null
    if ($null -ne $tagsProp) { $tags = $tagsProp.Value }
    if ($null -eq $tags) {
        $Warnings.Add('tags is missing (skill will have no marketplace search tags)')
    } elseif ($tags -is [string] -or $tags -isnot [System.Collections.IEnumerable]) {
        $Errors.Add('tags must be an array')
    } else {
        $tagsArray = @($tags)
        if ($tagsArray.Count -gt $MaxTagCount) {
            $Errors.Add("tags has $($tagsArray.Count) items, maximum is $MaxTagCount")
        }
        foreach ($tag in $tagsArray) {
            if ($tag -isnot [string]) {
                $Errors.Add("tag '$tag' must be a string")
            } elseif ($tag.Length -gt $MaxTagLength) {
                $Errors.Add("tag '$tag' exceeds $MaxTagLength characters")
            }
        }
    }

    $category = Get-JsonProperty $Manifest 'category'
    if ([string]::IsNullOrWhiteSpace($category)) {
        $Warnings.Add("category is missing (marketplace will default to 'other')")
    } elseif ($ValidCategories -cnotcontains $category) {
        $Warnings.Add("category '$category' is not a recognized category (marketplace will default to 'other')")
    }

    $readmePath = Join-Path $SkillDir 'README.md'
    if (-not (Test-Path -LiteralPath $readmePath -PathType Leaf)) {
        $Errors.Add('README.md does not exist')
    } else {
        $readmeSize = (Get-Item -LiteralPath $readmePath).Length
        if ($readmeSize -gt $MaxReadmeBytes) {
            $Errors.Add("README.md exceeds $MaxReadmeBytes bytes (actual: $readmeSize)")
        }
    }

    $licensePath = Join-Path $SkillDir 'LICENSE'
    if (-not (Test-Path -LiteralPath $licensePath -PathType Leaf)) {
        $Errors.Add('LICENSE does not exist')
    }

    Test-SkillIntegration -SkillDir $SkillDir -FolderName $FolderName -Manifest $Manifest `
        -Errors $Errors -Warnings $Warnings
}

function Test-ZipExclusion {
    # $RelativePath uses forward slashes already. The exclusion list (__pycache__/, dist/, .DS_Store,
    # Thumbs.db, *.pyc) lives in SkillLint.psm1 so the folder rule and the vendor lock see the same set.
    param([Parameter(Mandatory)] [string]$RelativePath)
    return Test-SkillPackageExclusion -RelativePath $RelativePath
}

function New-SkillArchive {
    param(
        [Parameter(Mandatory)] [string]$SkillDir,
        [Parameter(Mandatory)] [string]$OutputPath
    )

    if (Test-Path -LiteralPath $OutputPath) {
        Remove-Item -LiteralPath $OutputPath -Force
    }

    $skillDirFull = (Resolve-Path -LiteralPath $SkillDir).Path
    # Forward-slash relative paths in ordinal order, already filtered by Test-ZipExclusion.
    $relativePaths = Get-SkillPackageFiles -SkillDir $skillDirFull

    $archive = [System.IO.Compression.ZipFile]::Open($OutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($relativePath in $relativePaths) {
            $sourcePath = Join-Path $skillDirFull $relativePath
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $sourcePath, $relativePath, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally {
        $archive.Dispose()
    }
    return , $relativePaths
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$skillsDir = Join-Path $RepoRoot 'skills'

if (-not (Test-Path -LiteralPath $skillsDir -PathType Container)) {
    throw "Skills directory not found: $skillsDir"
}

if (-not $ValidateOnly -and -not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Catalogues plus every skill's tool names (for the cross-skill collision checks), loaded once. It always
# reads every skills/*/manifest.json, also when -Skills limits what is built.
$lintContext = New-SkillLintContext -SkillsRoot $skillsDir

# -ValidateOnly still builds each archive for the zip checks, in a scratch folder removed at the end.
$scratchDir = Join-Path ([System.IO.Path]::GetTempPath()) ("sophon-skill-validate-" + [guid]::NewGuid().ToString('N'))

# Resolve the set of skill folder names to process (each an immediate subdir of skills/ with a
# manifest.json). With an explicit -Skills list, unknown names are still processed so the
# "does not exist" error below fires.
$skillNames = [System.Collections.Generic.List[string]]::new()
if ($Skills.Count -gt 0) {
    foreach ($name in $Skills) { $skillNames.Add($name) }
} else {
    Get-ChildItem -LiteralPath $skillsDir -Directory |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json') -PathType Leaf } |
        ForEach-Object { $skillNames.Add($_.Name) }
}

$results = [System.Collections.Generic.List[object]]::new()
$allWarnings = [System.Collections.Generic.List[string]]::new()
$anyFailed = $false

try {
    foreach ($folderName in $skillNames) {
        $skillDir = Join-Path $skillsDir $folderName
        $manifestPath = Join-Path $skillDir 'manifest.json'

        $errors = [System.Collections.Generic.List[string]]::new()
        $warnings = [System.Collections.Generic.List[string]]::new()
        $manifest = $null

        if (-not (Test-Path -LiteralPath $skillDir -PathType Container)) {
            $errors.Add("skill folder does not exist under skills/: $skillDir")
        } elseif (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
            $errors.Add('manifest.json does not exist')
        } else {
            $rawManifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding utf8
            try {
                $manifest = $rawManifest | ConvertFrom-Json
            } catch {
                $errors.Add("manifest.json is not valid JSON: $($_.Exception.Message)")
            }
            # Bare `null`, a scalar, or an array all parse fine but are not skill manifests;
            # without this guard, Test-SkillManifest's Mandatory $Manifest binding would throw
            # and abort the whole run instead of failing just this skill.
            if ($errors.Count -eq 0 -and ($null -eq $manifest -or $manifest -isnot [System.Management.Automation.PSCustomObject])) {
                $errors.Add('manifest.json is not a JSON object')
                $manifest = $null
            }
        }

        if ($errors.Count -eq 0) {
            Test-SkillManifest -SkillDir $skillDir -FolderName $folderName -Manifest $manifest -Errors $errors -Warnings $warnings
            Invoke-SkillLint -SkillDir $skillDir -FolderName $folderName -Context $lintContext -Errors $errors -Warnings $warnings
        }

        $version = Get-JsonProperty $manifest 'version'
        $artifactName = if ([string]::IsNullOrWhiteSpace($version)) { '' } else { "$folderName-$version.sophon-skill" }
        $artifactPath = if ($artifactName -ne '') { Join-Path $OutputDir $artifactName } else { '' }

        # Zip mirror: build the archive (to the scratch folder under -ValidateOnly) and replay the installer's
        # and the marketplace's zip checks on it. A failing archive is deleted so it can never be published.
        if ($errors.Count -eq 0) {
            $archivePath = $artifactPath
            if ($ValidateOnly) {
                New-Item -ItemType Directory -Path $scratchDir -Force | Out-Null
                $archivePath = Join-Path $scratchDir $artifactName
            }
            $packaged = New-SkillArchive -SkillDir $skillDir -OutputPath $archivePath
            Test-SkillArchive -ArchivePath $archivePath -Context $lintContext -Errors $errors -ExpectedEntries $packaged
            if ($ValidateOnly -or $errors.Count -gt 0) {
                Remove-Item -LiteralPath $archivePath -Force
            }
        }

        foreach ($w in $warnings) {
            $allWarnings.Add("[$folderName] $w")
        }

        if ($errors.Count -gt 0) {
            $anyFailed = $true
            $results.Add([pscustomobject]@{
                Skill    = $folderName
                Version  = if ([string]::IsNullOrWhiteSpace($version)) { '-' } else { $version }
                Artifact = '-'
                SHA256   = '-'
                Status   = 'FAILED: ' + ($errors -join '; ')
            })
            continue
        }

        if ($ValidateOnly) {
            $results.Add([pscustomobject]@{
                Skill    = $folderName
                Version  = $version
                Artifact = '(validate-only)'
                SHA256   = '-'
                Status   = 'OK'
            })
            continue
        }

        $hash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()

        $results.Add([pscustomobject]@{
            Skill    = $folderName
            Version  = $version
            Artifact = $artifactName
            SHA256   = $hash
            Status   = 'OK'
        })
    }
} finally {
    # The scratch folder exists only under -ValidateOnly; remove it even when a check throws.
    if (Test-Path -LiteralPath $scratchDir) {
        Remove-Item -LiteralPath $scratchDir -Recurse -Force
    }
}

Write-Output ''
$heading = if ($ValidateOnly) { '=== Marketplace Package Validation Summary ===' } else { '=== Marketplace Package Build Summary ===' }
Write-Output $heading
# Manually padded columns (not Format-Table -AutoSize) so the 64-char SHA256 column never gets
# squeezed by host-window-width detection under non-interactive/redirected hosts.
$rowFormat = '{0,-16} {1,-10} {2,-34} {3,-64} {4}'
Write-Output ($rowFormat -f 'Skill', 'Version', 'Artifact', 'SHA256', 'Status')
foreach ($r in $results) {
    Write-Output ($rowFormat -f $r.Skill, $r.Version, $r.Artifact, $r.SHA256, $r.Status)
}

if ($allWarnings.Count -gt 0) {
    Write-Output '=== Warnings ==='
    foreach ($w in $allWarnings) {
        Write-Output "WARN: $w"
    }
}

if ($anyFailed) {
    Write-Output 'One or more skills failed validation. See Status column / errors above.'
    exit 1
}

exit 0
