#Requires -Version 7.0

<#
.SYNOPSIS
    Uploads built .sophon-skill artifacts to the Sophon Marketplace via POST /api/v1/publish.
.DESCRIPTION
    Iterates every .sophon-skill (and .sophon-plugin) artifact under -ArtifactDir (default dist/)
    and uploads each as a multipart/form-data POST to <MarketplaceUrl>/api/v1/publish, using an
    smk_-prefixed publisher API key as a Bearer token. Prints the marketplace's response
    (name / version / status / sha256) per artifact.

    Publishing is a deliberate manual action — new versions land in `pendingReview` and require
    super-admin approval before going live. Versions must be strictly-increasing SemVer: bump the
    manifest `version` before re-publishing any change, or the upload is rejected (409). Run
    Build-MarketplacePackages.ps1 first to produce the artifacts.
.PARAMETER ArtifactDir
    Directory containing the .sophon-skill/.sophon-plugin artifacts. Defaults to <RepoRoot>/dist.
.PARAMETER MarketplaceUrl
    Base URL of the marketplace. Defaults to $env:SOPHON_MARKETPLACE_URL, then to the production
    marketplace (https://marketplace.sophon.buildersoft.io). The script appends /api/v1/publish.
.PARAMETER ApiKey
    Publisher API key (smk_...). Defaults to $env:SOPHON_MARKETPLACE_API_KEY. Never hard-code this;
    supply it via the environment / a CI secret.
.PARAMETER Skills
    Optional list of artifact base names (skill names) to publish; matches <name>-*.sophon-skill.
    Empty (default) publishes every artifact found under -ArtifactDir.
.PARAMETER DryRun
    List the artifacts that would be uploaded and the target endpoint, but do not upload anything.
    Does not require an API key.
.EXAMPLE
    $env:SOPHON_MARKETPLACE_API_KEY = 'smk_...'
    pwsh -File build/Publish-MarketplacePackages.ps1

    Publishes every artifact in dist/ to the production marketplace.
.EXAMPLE
    pwsh -File build/Publish-MarketplacePackages.ps1 -DryRun

    Shows what would be published, without uploading.
.EXAMPLE
    pwsh -File build/Publish-MarketplacePackages.ps1 -MarketplaceUrl http://localhost:5100 -Skills jira

    Publishes only the jira artifact to a local marketplace instance.
#>

[CmdletBinding()]
param(
    [string]$ArtifactDir = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')) 'dist'),
    [string]$MarketplaceUrl = $(if ($env:SOPHON_MARKETPLACE_URL) { $env:SOPHON_MARKETPLACE_URL } else { 'https://marketplace.sophon.buildersoft.io' }),
    [string]$ApiKey = $env:SOPHON_MARKETPLACE_API_KEY,
    [string[]]$Skills = @(),
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ArtifactDir -PathType Container)) {
    throw "Artifact directory not found: $ArtifactDir. Run build/Build-MarketplacePackages.ps1 first."
}

$publishUrl = $MarketplaceUrl.TrimEnd('/') + '/api/v1/publish'

$artifacts = @(Get-ChildItem -LiteralPath $ArtifactDir -File |
    Where-Object { $_.Name -like '*.sophon-skill' -or $_.Name -like '*.sophon-plugin' })

if ($Skills.Count -gt 0) {
    $artifacts = @($artifacts | Where-Object {
        $baseName = $_.Name
        $Skills | Where-Object { $baseName -like "$_-*" }
    })
}

if ($artifacts.Count -eq 0) {
    Write-Output "No artifacts to publish in $ArtifactDir (looked for *.sophon-skill / *.sophon-plugin)."
    exit 0
}

Write-Output "Target: $publishUrl"
Write-Output "Artifacts ($($artifacts.Count)):"
foreach ($a in $artifacts) { Write-Output "  - $($a.Name)" }
Write-Output ''

if ($DryRun) {
    Write-Output 'DryRun: nothing uploaded.'
    exit 0
}

if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    throw 'No API key. Set $env:SOPHON_MARKETPLACE_API_KEY (an smk_... publisher key) or pass -ApiKey.'
}
if (-not $ApiKey.StartsWith('smk_')) {
    Write-Warning "API key does not start with 'smk_' — is this a publisher key?"
}

$headers = @{ Authorization = "Bearer $ApiKey" }
$anyFailed = $false

foreach ($a in $artifacts) {
    Write-Output "Publishing $($a.Name) ..."
    try {
        # PowerShell 7 -Form sends a FileInfo value as a file part; the field name must be 'package'.
        $resp = Invoke-RestMethod -Method Post -Uri $publishUrl -Headers $headers `
            -Form @{ package = Get-Item -LiteralPath $a.FullName } -StatusCodeVariable 'status'
        Write-Output "  $status  name=$($resp.name) version=$($resp.version) status=$($resp.status) sha256=$($resp.sha256)"
    } catch {
        $anyFailed = $true
        $status = $null
        try { $status = $_.Exception.Response.StatusCode.value__ } catch { }
        $body = ''
        if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $body = $_.ErrorDetails.Message }
        Write-Warning "  FAILED ($status) $($a.Name): $($_.Exception.Message) $body"
    }
}

if ($anyFailed) {
    Write-Output ''
    Write-Output 'One or more uploads failed. See warnings above. (409 = version not strictly greater / duplicate content; 403 = not the owner; 422 = manifest/zip validation.)'
    exit 1
}

exit 0
