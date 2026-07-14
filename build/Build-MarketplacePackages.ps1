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
    Validate every skill and print the summary, but do NOT produce .sophon-skill archives. Used by
    CI to fail a PR on any manifest/contract violation without writing build output. Exit code is
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

$ValidRuntimes    = @('python', 'csharp', 'sandbox')
$ValidRiskLevels  = @('none', 'low', 'medium', 'high', 'critical')
$ValidCategories  = @('utility', 'productivity', 'communication', 'data', 'development', 'integration', 'ai', 'automation', 'other')
$ExcludeDirNames  = @('__pycache__', 'dist')
$ExcludeFileNames = @('.DS_Store', 'Thumbs.db')
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
}

function Test-ZipExclusion {
    # $RelativePath uses forward slashes already.
    param([Parameter(Mandatory)] [string]$RelativePath)

    $segments = $RelativePath.Split('/')
    if ($segments.Length -gt 1) {
        for ($i = 0; $i -lt ($segments.Length - 1); $i++) {
            if ($ExcludeDirNames -contains $segments[$i]) { return $true }
        }
    }
    $leaf = $segments[$segments.Length - 1]
    if ($ExcludeFileNames -contains $leaf) { return $true }
    if ($leaf -like '*.pyc') { return $true }
    return $false
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
    $files = Get-ChildItem -LiteralPath $skillDirFull -Recurse -File -Force

    $archive = [System.IO.Compression.ZipFile]::Open($OutputPath, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($skillDirFull.Length).TrimStart('\', '/').Replace('\', '/')
            if (Test-ZipExclusion -RelativePath $relativePath) { continue }
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $relativePath, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally {
        $archive.Dispose()
    }
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
    }

    foreach ($w in $warnings) {
        $allWarnings.Add("[$folderName] $w")
    }

    $version = Get-JsonProperty $manifest 'version'
    $artifactName = if ([string]::IsNullOrWhiteSpace($version)) { '' } else { "$folderName-$version.sophon-skill" }
    $artifactPath = if ($artifactName -ne '') { Join-Path $OutputDir $artifactName } else { '' }

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

    New-SkillArchive -SkillDir $skillDir -OutputPath $artifactPath
    $hash = (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash.ToLowerInvariant()

    $results.Add([pscustomobject]@{
        Skill    = $folderName
        Version  = $version
        Artifact = $artifactName
        SHA256   = $hash
        Status   = 'OK'
    })
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
