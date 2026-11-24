#Requires -Version 7.0

<#
.SYNOPSIS
    End-to-end tests for the Buildersoft agent family packages in agents/ (sections A-L).
.DESCRIPTION
    The roster is the union of every family in build/agent-src/families.psd1 (an id belongs to one family).
    Sections (docs/plans/2026-11-15-agents-v2-design.md section 7.5):
      A-I  build/Test-AgentSources.ps1 on the real tree (every family): layout, composer -Check, tool-name lint,
           preflight, budgets (with the headroom table), manifests, TOOLS.md, attribution, credits.
      B    plus every tests/agents/fixtures/compose/<case> through Compose-AgentSouls.ps1 -RepoRoot <case> -Check (or the
           arguments in its ARGS file, one per line, {OUT} a fresh folder), compared with its EXPECT file (OK, 'OK: <text>'
           for exit 0 with that text, else the text of an exit 1), and two -OutDir builds of the real tree that must be
           byte-identical.
      C D F G plus the lint, scan, manifest and toolsmd fixture suites (Invoke-AgentLintFixtures in AgentLint.psm1).
      D    plus a temporary copy with one fragment given a second heading and one stripped of its heading,
           which Test-AgentSources must fail with FRAGMENT-HEADING.
      E    plus the headroom boundaries (Get-AgentSoulBudget) and a temporary copy with a lowered developer cap and
           RoleCap: under 5% free warns daily and fails with -Release, 5-8% free only warns, BUDGET-ROLE.
      J    'sophon --version' matches every family's SophonCli; 'sophon dev validate --json' per agent gives ok,
           projectType agent, no errors and no warnings.
      K    build/Build-AgentPackages.ps1 into a temporary folder: a decoy package is removed, one package per
           roster agent, a
           well-formed SHA256SUMS with recomputed hashes, zip entries equal to the sources, a byte-identical
           repeat build, a subset build, and failure cases (unknown agent, roster mismatch, name mismatch,
           SOUL drift, a lint error).
      L    families, on a temporary copy holding the development family plus the media fixture family
           (tests/agents/fixtures/families/media): both compose and pass the source checks side by side, an id
           in two families fails, the legacy registry-less fallback, SkillPolicy (skill-tool mentions and pins,
           requires.skills, ExtraRequiredTools, MAN-SKILL-VERSION), the per-agent Skills key (absent, all, none, schema),
           AllowRestrictedMentions, and the development
           family still failing LINT-SKILL and MAN-REQUIRES as before. Needs no Sophon CLI.
      M    the Method registry: tests/agents/fixtures/method/cases.psd1 (Invoke-AgentMethodFixtures) for METHOD-CONTROLLER,
           METHOD-EXCUSES and METHOD-REFERENCE, tests/agents/fixtures/skills/cases.psd1 (Invoke-AgentSkillUseFixtures)
           for LINT-SKILL-FRAGMENT, LINT-SKILL-UNUSED and LINT-TOPIC, then the development family's own Method key (and a copy without its
           exemption or its test-integrity rule);
           in-memory anchor cases (ANCHOR-MISSING, ANCHOR-GONE, data errors); a smoke run of Compare-AgentSouls.ps1;
           the scenario lint of the instruction tests on tests/agents/fixtures/evals/cases.psd1
           (Invoke-AgentEvalLintFixtures in tests/agents/evals/AgentEvals.psm1), the transcript scorer on two
           stream-json fixtures and on in-memory ones (PRS-EV1, PRS-EV2, a cut argsPreview), the runner's exec
           line, package choice, SOUL hash and run-error rule, tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly on the real scenario files
           (and -Release failing while a row is Pending), every eval fixture and patch as a git workspace, and
           -Prepare on two scenarios.
      N    documents: DOC-COUNT from the repository pass of Test-AgentSources, plus a temporary copy with planted counts:
           number words and digits, qualifiers, a History phrase, and -Release turning the warning into an error.

    -SourceOnly skips J and K (no Sophon CLI needed). Prints PASS, FAIL or SKIP per section and exits 1 on any
    failure. Temporary folders live under the system temp folder and are removed at the end.
.PARAMETER RepoRoot
    Repository root. Defaults to two folders above this script.
.PARAMETER SourceOnly
    Run sections A-I, L, M and N only.
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Test-AgentPackages.ps1 -SourceOnly
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = (Join-Path $PSScriptRoot '../..'),
    [switch]$SourceOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = [IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($RepoRoot))
$ordinal = [StringComparer]::Ordinal
$ord = [StringComparison]::Ordinal
$utf8Strict = [Text.UTF8Encoding]::new($false, $true)
$pwsh = [Environment]::ProcessPath
if (-not $pwsh -or [IO.Path]::GetFileNameWithoutExtension($pwsh) -ne 'pwsh') { $pwsh = 'pwsh' }

$sectionTitles = [ordered]@{
    A = 'Roster and layout'
    B = 'Composer'
    C = 'Tool-name lint'
    D = 'Preflight'
    E = 'Budgets'
    F = 'Manifest'
    G = 'TOOLS.md'
    H = 'Attribution'
    I = 'Credits'
    J = 'Sophon CLI validation'
    K = 'Reproducible build'
    L = 'Families'
    M = 'Method registry'
    N = 'Documents'
}
$items = @{}
$skipped = @{}
foreach ($key in $sectionTitles.Keys) { $items[$key] = [System.Collections.Generic.List[object]]::new() }

function Add-Pass([string]$Section, [string]$Message) { $items[$Section].Add([pscustomobject]@{ Ok = $true; Text = $Message }) }
function Add-Fail([string]$Section, [string]$Message) { $items[$Section].Add([pscustomobject]@{ Ok = $false; Text = $Message }) }
function Add-Note([string]$Section, [string]$Message) { $items[$Section].Add([pscustomobject]@{ Ok = $null; Text = $Message }) }
function Test-Check([string]$Section, [bool]$Condition, [string]$Message) {
    if ($Condition) { Add-Pass $Section $Message } else { Add-Fail $Section $Message }
    return $Condition
}

function Invoke-Native {
    # Runs a native command with stderr merged into the output; never throws on stderr or a non-zero exit.
    param([string]$FilePath, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $lines = @(& $FilePath @Arguments 2>&1 | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
    } catch {
        $lines = @("could not start ${FilePath}: $($_.Exception.Message)")
        $code = -1
    } finally {
        $ErrorActionPreference = $previous
    }
    return [pscustomobject]@{ Code = $code; Lines = $lines; Text = ($lines -join "`n") }
}

function Invoke-NativeJson {
    param([string]$FilePath, [string[]]$Arguments)
    $errFile = [IO.Path]::GetTempFileName()
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $stdout = @(& $FilePath @Arguments 2>$errFile | ForEach-Object { "$_" })
        $code = $LASTEXITCODE
        $stderr = [IO.File]::ReadAllText($errFile).Trim()
    } finally {
        $ErrorActionPreference = $previous
        Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
    }
    $text = ($stdout -join "`n").Trim()
    $json = $null
    try { $json = $text | ConvertFrom-Json -ErrorAction Stop } catch { $json = $null }
    return [pscustomobject]@{ Code = $code; Text = $text; Json = $json; Stderr = $stderr }
}

function Get-Field($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    if ($Object -is [System.Collections.IDictionary]) { if ($Object.Contains($Name)) { return $Object[$Name] }; return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Format-CliIssue($Issue) {
    $message = [string](Get-Field $Issue 'message')
    $where = @(@((Get-Field $Issue 'file'), (Get-Field $Issue 'field')) | Where-Object { $_ }) -join ' '
    if ($where) { return "$message ($where)" }
    return $message
}

function Test-BytesEqual([byte[]]$Left, [byte[]]$Right) {
    if ($null -eq $Left -or $null -eq $Right) { return $false }
    return $Left.Length -eq $Right.Length -and [System.Linq.Enumerable]::SequenceEqual($Left, $Right)
}

function Get-Tail([string[]]$Lines, [int]$Count = 6) {
    $kept = @($Lines | Where-Object { "$_".Trim() })
    if ($kept.Count -le $Count) { return ($kept -join ' / ') }
    return ($kept[($kept.Count - $Count)..($kept.Count - 1)] -join ' / ')
}

function Invoke-Builder([string]$Root, [string[]]$Extra) {
    $builder = Join-Path $Root 'build/Build-AgentPackages.ps1'
    return Invoke-Native $pwsh (@('-NoProfile', '-NonInteractive', '-File', $builder, '-RepoRoot', $Root) + $Extra)
}

function New-RepoCopy([string]$Destination) {
    # Everything the builder reads: agents/, build/, the root LICENSE and the skill manifests (tool catalogue).
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'LICENSE') -Destination $Destination
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'agents') -Destination $Destination -Recurse
    Copy-Item -LiteralPath (Join-Path $RepoRoot 'build') -Destination $Destination -Recurse
    $skills = Join-Path $RepoRoot 'skills'
    if (Test-Path -LiteralPath $skills -PathType Container) {
        foreach ($dir in @(Get-ChildItem -LiteralPath $skills -Directory)) {
            $manifest = Join-Path $dir.FullName 'manifest.json'
            if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) { continue }
            $target = Join-Path $Destination "skills/$($dir.Name)"
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            Copy-Item -LiteralPath $manifest -Destination $target
        }
    }
}

function Write-Utf8([string]$Path, [string]$Text) {
    [IO.File]::WriteAllText($Path, $Text, [Text.UTF8Encoding]::new($false))
}

function Edit-AgentReadme([string]$Root, [string]$Id, [string]$Old, [string]$New) {
    # A development README is generated: change agents/<id>/README.md and its source the same way, so a case fails
    # on the rule it plants and not on README drift.
    foreach ($path in @((Join-Path $Root "agents/$Id/README.md"), (Join-Path $Root "build/agent-src/readmes/$Id.md"))) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
        $text = [IO.File]::ReadAllText($path)
        if (-not $text.Contains($Old)) { throw "Edit-AgentReadme: '$Old' not found in $path" }
        Write-Utf8 $path ($text.Replace($Old, $New))
    }
}

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('sophon-agent-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$unexpected = $null

try {
    # ---- Families ------------------------------------------------------------------------------------------
    # The roster is the union of the family rosters; $family is the first family (development), whose lead
    # the K drift case edits.
    $family = $null
    $families = @()
    $roster = [string[]]@()
    try {
        Import-Module (Join-Path $RepoRoot 'build/AgentFamily.psm1') -Force
        $union = Get-AgentRosterUnion -RepoRoot $RepoRoot
        foreach ($e in @($union['Errors'])) { Add-Fail 'A' "agent families: $(Format-AgentComposeError -Item $e)" }
        $families = @($union['Families'])
        $roster = [string[]]@($union['Ids'])
        if ($families.Count -gt 0) { $family = $families[0]['Data'] }
    } catch {
        Add-Fail 'A' "the agent families do not load: $($_.Exception.Message)"
    }
    $familyVersion = if ($null -ne $family -and $family.Contains('FamilyVersion')) { [string]$family['FamilyVersion'] } else { '2.0.0' }
    Write-Host "Repo: $RepoRoot"
    Write-Host "Families: $(@($families | ForEach-Object { "$($_['Id']) ($(@($_['Roster']).Count))" }) -join ', ')"
    Write-Host "Roster ($($roster.Count)): $($roster -join ', ')"
    if ($SourceOnly) { Write-Host 'CLI CHECKS NOT RUN (-SourceOnly)' -ForegroundColor Red }

    # ---- A-I: Test-AgentSources on the real tree -----------------------------------------------------------
    Write-Host 'Running build/Test-AgentSources.ps1 ...'
    $sources = Join-Path $RepoRoot 'build/Test-AgentSources.ps1'
    if (-not (Test-Path -LiteralPath $sources -PathType Leaf)) {
        Add-Fail 'A' 'build/Test-AgentSources.ps1 is missing'
    } else {
        $run = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $sources, '-RepoRoot', $RepoRoot)
        $current = $null
        $captured = @{}
        $errorCounts = @{}
        foreach ($key in 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'M', 'N') { $captured[$key] = [System.Collections.Generic.List[string]]::new(); $errorCounts[$key] = 0 }
        foreach ($line in $run.Lines) {
            $heading = [regex]::Match($line, '^== ([A-IMN])\. ')
            if ($heading.Success) { $current = $heading.Groups[1].Value; continue }
            if ($line -clike '== Summary*') { $current = $null; continue }
            if ($null -eq $current -or -not $line.Trim()) { continue }
            if ($line -clike 'ERROR *') {
                Add-Fail $current ('Test-AgentSources: ' + $line.Substring(6))
                $errorCounts[$current]++
            } else {
                $captured[$current].Add($line)
            }
        }
        foreach ($key in $captured.Keys) {
            if ($errorCounts[$key] -eq 0) {
                Add-Pass $key "Test-AgentSources section ${key}: 0 errors"
                if ($key -eq 'E') { foreach ($line in $captured[$key]) { Add-Note $key $line.Trim() } }
            } else {
                foreach ($line in $captured[$key]) { Add-Note $key $line.Trim() }
            }
        }
        $reported = 0
        foreach ($key in $errorCounts.Keys) { $reported += $errorCounts[$key] }
        if ($run.Code -ne 0 -and $reported -eq 0) {
            Add-Fail 'A' "Test-AgentSources.ps1 exited $($run.Code) without an ERROR line: $(Get-Tail $run.Lines)"
        }
        if ($run.Code -eq 0 -and $reported -gt 0) {
            Add-Fail 'A' "Test-AgentSources.ps1 exited 0 although it printed $reported ERROR line(s)"
        }
    }

    # ---- B: composer fixtures and a reproducible compose ---------------------------------------------------
    $composer = Join-Path $RepoRoot 'build/Compose-AgentSouls.ps1'
    $fixtureRoot = Join-Path $RepoRoot 'tests/agents/fixtures/compose'
    if (-not (Test-Path -LiteralPath $composer -PathType Leaf)) {
        Add-Fail 'B' 'build/Compose-AgentSouls.ps1 is missing'
    } else {
        $caseList = [System.Collections.Generic.List[object]]::new()
        if (Test-Path -LiteralPath $fixtureRoot -PathType Container) {
            foreach ($dir in @(Get-ChildItem -LiteralPath $fixtureRoot -Directory)) { $caseList.Add($dir) }
        }
        $caseList.Sort([Comparison[object]] { param($x, $y) [string]::CompareOrdinal($x.Name, $y.Name) })
        $cases = $caseList.ToArray()
        Write-Host "Running $($cases.Count) composer fixture(s) ..."
        if ($cases.Count -eq 0) { Add-Fail 'B' 'no composer fixtures under tests/agents/fixtures/compose' }
        $okCases = 0
        foreach ($case in $cases) {
            $expectPath = Join-Path $case.FullName 'EXPECT'
            if (-not (Test-Path -LiteralPath $expectPath -PathType Leaf)) { Add-Fail 'B' "compose fixture $($case.Name): no EXPECT file"; continue }
            $expect = ([IO.File]::ReadAllText($expectPath, $utf8Strict)).TrimEnd("`n")
            # ARGS (optional): the composer arguments, one per line, instead of -Check; {OUT} is a fresh folder.
            $composeArgs = @('-Check')
            $argsPath = Join-Path $case.FullName 'ARGS'
            if (Test-Path -LiteralPath $argsPath -PathType Leaf) {
                $caseOut = Join-Path $tempRoot "compose-case-$($case.Name)"
                $composeArgs = @(([IO.File]::ReadAllText($argsPath, $utf8Strict)).TrimEnd("`n").Split("`n") | Where-Object { $_ } | ForEach-Object { $_.Replace('{OUT}', $caseOut) })
            }
            $result = Invoke-Native $pwsh (@('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $case.FullName) + $composeArgs)
            if ([string]::Equals($expect, 'OK', $ord)) {
                $good = $result.Code -eq 0
                $want = 'exit 0'
            } elseif ($expect.StartsWith('OK: ', $ord)) {
                $good = $result.Code -eq 0 -and $result.Text.Contains($expect.Substring(4), $ord)
                $want = "exit 0 with '$($expect.Substring(4))'"
            } else {
                $good = $result.Code -eq 1 -and $result.Text.Contains($expect, $ord)
                $want = "exit 1 with '$expect'"
            }
            if ($good) { $okCases++ }
            else { Add-Fail 'B' "compose fixture $($case.Name): expected $want, got exit $($result.Code): $(Get-Tail $result.Lines 3)" }
        }
        if ($cases.Count -gt 0 -and $okCases -eq $cases.Count) { Add-Pass 'B' "$okCases composer fixture(s) behave as their EXPECT files say" }

        Write-Host 'Composing the real tree twice with -OutDir ...'
        $outA = Join-Path $tempRoot 'compose-a'
        $outB = Join-Path $tempRoot 'compose-b'
        $runA = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $RepoRoot, '-OutDir', $outA)
        $runB = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $RepoRoot, '-OutDir', $outB)
        if ($runA.Code -ne 0 -or $runB.Code -ne 0) {
            Add-Fail 'B' "-OutDir compose exited $($runA.Code) and $($runB.Code): $(Get-Tail $runA.Lines 3)"
        } else {
            $same = 0
            foreach ($id in $roster) {
                $fileA = Join-Path $outA "$id/SOUL.md"
                $fileB = Join-Path $outB "$id/SOUL.md"
                if (-not (Test-Path -LiteralPath $fileA -PathType Leaf) -or -not (Test-Path -LiteralPath $fileB -PathType Leaf)) {
                    Add-Fail 'B' "-OutDir compose wrote no $id/SOUL.md"
                } elseif (-not (Test-BytesEqual ([IO.File]::ReadAllBytes($fileA)) ([IO.File]::ReadAllBytes($fileB)))) {
                    Add-Fail 'B' "two -OutDir composes of $id/SOUL.md differ"
                } else { $same++ }
            }
            if ($roster.Count -gt 0 -and $same -eq $roster.Count) { Add-Pass 'B' "two -OutDir composes are byte-identical ($same SOUL files)" }
            # Generated READMEs: a family with a readmes/ folder gets one per agent, equal to the committed file.
            $readmeSame = 0
            $readmeOut = @($roster | Where-Object { Test-Path -LiteralPath (Join-Path $outA "$_/README.md") -PathType Leaf })
            foreach ($id in $readmeOut) {
                $bytesA = [IO.File]::ReadAllBytes((Join-Path $outA "$id/README.md"))
                $fileB = Join-Path $outB "$id/README.md"
                $committedReadme = Join-Path $RepoRoot "agents/$id/README.md"
                if (-not (Test-Path -LiteralPath $fileB -PathType Leaf) -or -not (Test-BytesEqual $bytesA ([IO.File]::ReadAllBytes($fileB)))) { Add-Fail 'B' "two -OutDir composes of $id/README.md differ" }
                elseif (-not (Test-BytesEqual $bytesA ([IO.File]::ReadAllBytes($committedReadme)))) { Add-Fail 'B' "the composed $id/README.md differs from agents/$id/README.md" }
                else { $readmeSame++ }
            }
            $wantReadmes = @($families | Where-Object { Test-Path -LiteralPath (Join-Path $RepoRoot "$($_['Dir'])/readmes") -PathType Container } | ForEach-Object { @($_['Roster']) }).Count
            $null = Test-Check 'B' ($readmeOut.Count -eq $wantReadmes -and $readmeSame -eq $wantReadmes) "the -OutDir compose writes one README per agent of a family with a readmes/ folder ($readmeSame of $wantReadmes), each equal to agents/<id>/README.md; other families keep a hand-written README"
        }
    }

    # ---- A: optional per-agent metadata schema -------------------------------------------------------------
    Import-Module (Join-Path $RepoRoot 'build/AgentFamily.psm1') -Force
    $schemaFamily = Get-AgentFamily -RepoRoot $RepoRoot
    $schemaAgent = $schemaFamily['Agents'][0]
    $schemaAgent['License'] = 'Apache-2.0'
    $schemaAgent['Category'] = 'productivity'
    $schemaAgent['RequiredTags'] = @('productivity')
    $schemaErrors = @(Test-AgentFamilyData -RepoRoot $RepoRoot -Family $schemaFamily)
    $null = Test-Check 'A' ($schemaErrors.Count -eq 0) 'valid per-agent metadata overrides pass the family schema'
    foreach ($case in @(
            @{ Key = 'License'; Value = 'GPL-3.0' },
            @{ Key = 'Category'; Value = 'unknown' },
            @{ Key = 'RequiredTags'; Value = @() },
            @{ Key = 'RequiredTags'; Value = @('Bad Tag') },
            @{ Key = 'RequiredTags'; Value = @("productivity`n") },
            @{ Key = 'RequiredTags'; Value = @('valid', 'valid') },
            @{ Key = 'RequiredTags'; Value = 'productivity' },
            @{ Key = 'LicenseSource'; Value = '../LICENSE' },
            @{ Key = 'UnknownKey'; Value = 'value' })) {
        $badFamily = Get-AgentFamily -RepoRoot $RepoRoot
        $badFamily['Agents'][0][$case.Key] = $case.Value
        $errors = @(Test-AgentFamilyData -RepoRoot $RepoRoot -Family $badFamily)
        $null = Test-Check 'A' ($errors.Count -gt 0) "family schema rejects invalid $($case.Key)"
    }

    # Synthetic canonical bytes exercise resolution independently of the real license text.
    try {
        $licenseCase = Join-Path $tempRoot 'case-license-overrides'
        New-RepoCopy $licenseCase
        $familyPath = Join-Path $licenseCase 'build/agent-src/family.psd1'
        $familyText = [IO.File]::ReadAllText($familyPath)
        $familyText = $familyText.Replace("Id = 'code-reviewer'", "Id = 'code-reviewer'`n      License = 'Apache-2.0'`n      Category = 'productivity'`n      RequiredTags = @('productivity')")
        Write-Utf8 $familyPath $familyText
        $manifestPath = Join-Path $licenseCase 'agents/code-reviewer/manifest.json'
        $manifestText = [IO.File]::ReadAllText($manifestPath).Replace('"license": "MIT"', '"license": "Apache-2.0"').Replace('"category": "development"', '"category": "productivity"').Replace('"development"', '"productivity"')
        Write-Utf8 $manifestPath $manifestText
        $readmePath = Join-Path $licenseCase 'agents/code-reviewer/README.md'
        $readmeText = [IO.File]::ReadAllText($readmePath).Replace('Licensed under the MIT License; see LICENSE.', 'Licensed under the Apache-2.0 License; see LICENSE.')
        Write-Utf8 $readmePath $readmeText
        # The README is generated from its source, so the source takes the same edit.
        $readmeSource = Join-Path $licenseCase 'build/agent-src/readmes/code-reviewer.md'
        if (Test-Path -LiteralPath $readmeSource -PathType Leaf) { Write-Utf8 $readmeSource ([IO.File]::ReadAllText($readmeSource).Replace('Licensed under the MIT License; see LICENSE.', 'Licensed under the Apache-2.0 License; see LICENSE.')) }
        $canonicalPath = Join-Path $licenseCase 'build/licenses/Apache-2.0.txt'
        New-Item -ItemType Directory -Path (Split-Path $canonicalPath) -Force | Out-Null
        Write-Utf8 $canonicalPath "synthetic canonical bytes`n"
        $packageLicense = Join-Path $licenseCase 'agents/code-reviewer/LICENSE'
        Write-Utf8 $packageLicense "synthetic canonical bytes`n"
        $sourceArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $licenseCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $licenseCase, '-Agents', 'code-reviewer')
        $result = Invoke-Native $pwsh $sourceArgs
        $null = Test-Check 'A' ($result.Code -eq 0) "matching synthetic Apache bytes and README pass source checks$(if ($result.Code -ne 0) { ': ' + (Get-Tail $result.Lines 12) })"
        Write-Utf8 $packageLicense "wrong bytes`n"
        $result = Invoke-Native $pwsh $sourceArgs
        $null = Test-Check 'A' ($result.Code -ne 0 -and $result.Text.Contains('ERROR LAYOUT-LICENSE agents/code-reviewer/LICENSE:', $ord)) 'incorrect Apache package license bytes fail'
        Write-Utf8 $packageLicense "synthetic canonical bytes`n"
        Edit-AgentReadme $licenseCase 'code-reviewer' 'Licensed under the Apache-2.0 License; see LICENSE.' 'Licensed under the MIT License; see LICENSE.'
        $result = Invoke-Native $pwsh $sourceArgs
        $null = Test-Check 'I' ($result.Code -ne 0 -and $result.Text.Contains('ERROR CREDITS-SENTENCE agents/code-reviewer/README.md:', $ord)) 'incorrect Apache README license sentence fails'
    } catch {
        Add-Fail 'A' "license override cases failed to run: $($_.Exception.Message)"
    }

    # Empty Credits: only the license sentence is enforced; non-empty Credits stay strict.
    try {
        $creditsCase = Join-Path $tempRoot 'case-credits'
        New-RepoCopy $creditsCase
        $creditsSourceScript = Join-Path $creditsCase 'build/Test-AgentSources.ps1'
        $upstreamSentence = 'Workflow patterns adapted, not copied, from obra/superpowers'
        $apacheSentence = 'Licensed under the Apache-2.0 License; see LICENSE.'

        $creditArgs = @('-NoProfile', '-NonInteractive', '-File', $creditsSourceScript, '-RepoRoot', $creditsCase, '-Agents', 'artifact-creator')
        $result = Invoke-Native $pwsh $creditArgs
        $null = Test-Check 'I' ($result.Code -eq 0) "empty Credits with the Apache license sentence passes without an upstream credit sentence$(if ($result.Code -ne 0) { ': ' + (Get-Tail $result.Lines 12) })"

        $acReadme = Join-Path $creditsCase 'agents/artifact-creator/README.md'
        $acText = [IO.File]::ReadAllText($acReadme)
        $null = Test-Check 'I' ($acText.Contains($apacheSentence, $ord) -and -not $acText.Contains($upstreamSentence, $ord)) 'artifact-creator README has the Apache sentence and no upstream credit sentence'

        Edit-AgentReadme $creditsCase 'artifact-creator' $apacheSentence 'Licensed under the MIT License; see LICENSE.'
        $result = Invoke-Native $pwsh $creditArgs
        $null = Test-Check 'I' ($result.Code -ne 0 -and $result.Text.Contains('ERROR CREDITS-SENTENCE agents/artifact-creator/README.md:', $ord) -and -not $result.Text.Contains('verbatim credits sentence', $ord)) 'empty Credits with a wrong license sentence fails on the license sentence only'

        Edit-AgentReadme $creditsCase 'artifact-creator' 'Licensed under the MIT License; see LICENSE.' ''
        $result = Invoke-Native $pwsh $creditArgs
        $null = Test-Check 'I' ($result.Code -ne 0 -and $result.Text.Contains('ERROR CREDITS-SENTENCE agents/artifact-creator/README.md:', $ord)) 'empty Credits with no license sentence fails'

        Write-Utf8 $acReadme $acText
        $acSource = Join-Path $creditsCase 'build/agent-src/readmes/artifact-creator.md'
        if (Test-Path -LiteralPath $acSource -PathType Leaf) { Write-Utf8 $acSource $acText }
        $crReadme = Join-Path $creditsCase 'agents/code-reviewer/README.md'
        $crText = [IO.File]::ReadAllText($crReadme)
        $crStart = $crText.IndexOf($upstreamSentence, $ord)
        $null = Test-Check 'I' ($crStart -ge 0) 'code-reviewer README carries the upstream credit sentence before the strictness probe'
        if ($crStart -ge 0) {
            $crEnd = $crText.IndexOf("`n", $crStart, $ord)
            Edit-AgentReadme $creditsCase 'code-reviewer' $crText.Substring($crStart, $crEnd - $crStart) ''
            $result = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $creditsSourceScript, '-RepoRoot', $creditsCase, '-Agents', 'code-reviewer')
            $null = Test-Check 'I' ($result.Code -ne 0 -and $result.Text.Contains('ERROR CREDITS-SENTENCE agents/code-reviewer/README.md:', $ord)) 'non-empty Credits still require the upstream credit sentence'
        }
    } catch {
        Add-Fail 'I' "credits regression cases failed to run: $($_.Exception.Message)"
    }
    # ---- E: headroom and role caps ---------------------------------------------------------------------------
    # The boundaries in-process (cap 40,960: a warning above 37,683 B, a release failure above 38,912 B), then a
    # temporary copy whose developer cap and RoleCap are lowered, checked with and without -Release.
    Write-Host 'Running the budget cases ...'
    try {
        $states = @(37683, 37684, 38912, 38913, 40960, 40961 | ForEach-Object { (Get-AgentSoulBudget -Bytes $_ -Cap 40960)['Headroom'] }) -join ','
        $null = Test-Check 'E' ([string]::Equals($states, 'ok,warn,warn,fail,fail,over', $ord)) "headroom at cap 40,960 for 37,683 / 37,684 / 38,912 / 38,913 / 40,960 / 40,961 B is ok,warn,warn,fail,fail,over (got $states)"
        $budgetCase = Join-Path $tempRoot 'case-budget'
        New-RepoCopy $budgetCase
        $budgetFamily = Join-Path $budgetCase 'build/agent-src/family.psd1'
        $budgetText = [IO.File]::ReadAllText($budgetFamily)
        $devSize = [IO.File]::ReadAllBytes((Join-Path $budgetCase 'agents/developer/SOUL.md')).Length
        $devEntry = [regex]::Match($budgetText, "(Id = 'developer'\n(?:      [A-Za-z]+ = [^\n]*\n)*?      SoulCap = )\d+")
        if (-not $devEntry.Success) { throw "no developer SoulCap line in the family copy" }
        $budgetArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $budgetCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $budgetCase, '-Family', 'development', '-Agents', 'developer')
        # 3% free: a warning daily, an error with -Release (and with its alias -StrictHeadroom).
        $tightCap = [int][Math]::Ceiling($devSize / 0.97)
        Write-Utf8 $budgetFamily ($budgetText.Remove($devEntry.Index, $devEntry.Length).Insert($devEntry.Index, $devEntry.Groups[1].Value + $tightCap))
        $daily = Invoke-Native $pwsh $budgetArgs
        $strict = Invoke-Native $pwsh ($budgetArgs + '-Release')
        $alias = Invoke-Native $pwsh ($budgetArgs + '-StrictHeadroom')
        $null = Test-Check 'E' ($daily.Code -eq 0 -and $daily.Text.Contains('WARN BUDGET-HEADROOM agents/developer/SOUL.md:0:', $ord) -and
            $strict.Code -ne 0 -and $strict.Text.Contains('ERROR BUDGET-HEADROOM agents/developer/SOUL.md:0:', $ord) -and
            $alias.Code -ne 0 -and $alias.Text.Contains('ERROR BUDGET-HEADROOM', $ord)) "under 5% free warns daily and fails under -Release / -StrictHeadroom (exit $($daily.Code), $($strict.Code), $($alias.Code))"
        # 6% free: a warning both ways, never an error.
        $warnCap = [int][Math]::Ceiling($devSize / 0.94)
        Write-Utf8 $budgetFamily ($budgetText.Remove($devEntry.Index, $devEntry.Length).Insert($devEntry.Index, $devEntry.Groups[1].Value + $warnCap))
        $strict = Invoke-Native $pwsh ($budgetArgs + '-Release')
        $null = Test-Check 'E' ($strict.Code -eq 0 -and $strict.Text.Contains('WARN BUDGET-HEADROOM agents/developer/SOUL.md:0:', $ord)) "between 5% and 8% free warns, also under -Release (exit $($strict.Code))"
        # RoleCap below the measured role text fails; a RoleCap on one agent makes -Release require it of all.
        # The family's own RoleCap lines are removed first, so each case sets the key once and on one agent only.
        $noRoleText = [regex]::Replace($budgetText, '(?m)^      RoleCap = \d+\n', '')
        $roleText = $noRoleText.Replace("Id = 'developer'`n      DisplayName = 'Developer'", "Id = 'developer'`n      DisplayName = 'Developer'`n      RoleCap = 100")
        Write-Utf8 $budgetFamily $roleText
        $roleRun = Invoke-Native $pwsh $budgetArgs
        $null = Test-Check 'E' ($roleRun.Code -ne 0 -and $roleRun.Text.Contains('ERROR BUDGET-ROLE build/agent-src/souls/developer.md:0:', $ord)) "role text over its RoleCap fails BUDGET-ROLE (exit $($roleRun.Code))"
        Write-Utf8 $budgetFamily ($noRoleText.Replace("Id = 'developer'`n      DisplayName = 'Developer'", "Id = 'developer'`n      DisplayName = 'Developer'`n      RoleCap = 9000"))
        $reviewerArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $budgetCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $budgetCase, '-Family', 'development', '-Agents', 'developer,code-reviewer')
        $daily = Invoke-Native $pwsh $reviewerArgs
        $strict = Invoke-Native $pwsh ($reviewerArgs + '-Release')
        $null = Test-Check 'E' ($daily.Code -eq 0 -and $strict.Code -ne 0 -and $strict.Text.Contains("agent 'code-reviewer' has no RoleCap", $ord) -and
            -not $strict.Text.Contains("agent 'developer' has no RoleCap", $ord)) "a RoleCap within its limit passes; under -Release an agent without one fails once the family sets any (exit $($daily.Code), $($strict.Code))"
        # FragmentCaps: a lower limit for one fragment (04-scope is 728 B), a key without a fragment, a bad value.
        if (-not $budgetText.Contains("  Agents = @(`n")) { throw 'the family copy has no Agents line' }
        $capArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $budgetCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $budgetCase, '-Family', 'development', '-Agents', 'developer')
        $capRuns = @(foreach ($caps in "@{ '04-scope' = 100 }", "@{ '04-scope' = 800 }", "@{ '99-nothing' = 450 }", "@{ '04-scope' = 5000 }") {
                # The family's own FragmentCaps line (if any) is replaced, so the copy holds the key once.
                $capBase = [regex]::Replace($budgetText, '(?m)^  FragmentCaps = .*
', '')
                Write-Utf8 $budgetFamily ($capBase.Replace("  Agents = @(`n", "  FragmentCaps = $caps`n  Agents = @(`n"))
                Invoke-Native $pwsh $capArgs
            })
        Write-Utf8 $budgetFamily $budgetText
        $null = Test-Check 'D' ($capRuns[0].Code -ne 0 -and $capRuns[0].Text.Contains('ERROR BUDGET-FRAGMENT build/agent-src/fragments/soul/04-scope.md:0:', $ord) -and $capRuns[0].Text.Contains('its FragmentCaps limit is 100', $ord) -and
            $capRuns[1].Code -eq 0 -and
            $capRuns[2].Code -ne 0 -and $capRuns[2].Text.Contains("FragmentCaps names '99-nothing', which is not a fragment", $ord) -and
            $capRuns[3].Code -ne 0 -and $capRuns[3].Text.Contains("FragmentCaps '04-scope' = '5000'", $ord)) "FragmentCaps lowers one fragment's limit (BUDGET-FRAGMENT), and a key without a fragment or a value over 4,096 fails (exit $(@($capRuns | ForEach-Object { $_.Code }) -join ', '))"
    } catch {
        Add-Fail 'E' "the budget cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }

    # ---- C D F G: lint, scan, manifest and TOOLS.md fixture suites ------------------------------------------
    Write-Host 'Running the lint, scan, manifest and toolsmd fixture suites ...'
    $suiteSection = @{ lint = 'C'; scan = 'D'; manifest = 'F'; toolsmd = 'G' }
    try {
        Import-Module (Join-Path $RepoRoot 'build/AgentLint.psm1') -Force
        $metadataFamily = Get-AgentLintTestFamily
        $metadataAgent = @($metadataFamily.Agents | Where-Object { $_.Id -eq 'lead-developer' })[0]
        $metadataAgent.License = 'Apache-2.0'
        $metadataAgent.Category = 'productivity'
        $metadataAgent.RequiredTags = @('productivity')
        $fixture = Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'tests/agents/fixtures/manifest/cases.psd1')
        $raw = $fixture.Base.Replace('"license": "MIT"', '"license": "Apache-2.0"').Replace('"category": "development"', '"category": "productivity"').Replace('"development"', '"productivity"')
        $tools = Read-ToolsMd -Text $fixture.BaseTools
        $issues = @(Test-AgentManifest -Raw $raw -Id 'lead-developer' -Family $metadataFamily -ToolsMd $tools)
        $null = Test-Check 'F' ($issues.Count -eq 0) 'Apache productivity manifest accepts matching overrides'
        $wrong = $raw.Replace('"Apache-2.0"', '"MIT"').Replace('"productivity"', '"development"')
        $issues = @(Test-AgentManifest -Raw $wrong -Id 'lead-developer' -Family $metadataFamily -ToolsMd $tools)
        $null = Test-Check 'F' (@($issues | Where-Object Rule -eq 'MAN-META').Count -ge 2 -and @($issues | Where-Object Rule -eq 'MAN-TAGS').Count -gt 0) 'override manifest rejects incorrect license, category and required tags'
        $fixtureFailures = @(Invoke-AgentLintFixtures -RepoRoot $RepoRoot)
        foreach ($suite in 'lint', 'scan', 'manifest', 'toolsmd') {
            $section = $suiteSection[$suite]
            $casesFile = Join-Path $RepoRoot "tests/agents/fixtures/$suite/cases.psd1"
            $count = 0
            if (Test-Path -LiteralPath $casesFile -PathType Leaf) { $count = @((Import-PowerShellDataFile -LiteralPath $casesFile)['Cases']).Count }
            $mine = @($fixtureFailures | Where-Object { [string]::Equals([string]$_.Suite, $suite, $ord) })
            foreach ($failure in $mine) {
                $rule = if ($failure.Rule) { " $($failure.Rule)" } else { '' }
                Add-Fail $section "fixture $suite/$($failure.Name): expected $($failure.Expect)$rule, got '$($failure.Got)': $($failure.Detail)"
            }
            if ($mine.Count -eq 0 -and $count -gt 0) { Add-Pass $section "$count $suite fixture case(s) behave as expected" }
            if ($count -eq 0) { Add-Fail $section "no cases in tests/agents/fixtures/$suite/cases.psd1" }
        }
    } catch {
        Add-Fail 'C' "the fixture runner failed: $($_.Exception.Message)"
    }

    # ---- D: the fragment heading rule, on a temporary copy -------------------------------------------------
    # The copy is composed after the plants, so the only defects left are the two headings.
    Write-Host 'Running the fragment heading case ...'
    try {
        $headCase = Join-Path $tempRoot 'case-fragment-heading'
        New-RepoCopy $headCase
        $fragDir = Join-Path $headCase 'build/agent-src/fragments/soul'
        $scopePath = Join-Path $fragDir '04-scope.md'
        $todoPath = Join-Path $fragDir '06-todo.md'
        Write-Utf8 $scopePath ([IO.File]::ReadAllText($scopePath) + "## A second heading`n- Planted by the test.`n")
        Write-Utf8 $todoPath ([IO.File]::ReadAllText($todoPath) -replace '^## ', '')
        $null = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', (Join-Path $headCase 'build/Compose-AgentSouls.ps1'), '-RepoRoot', $headCase)
        $headRun = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', (Join-Path $headCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $headCase)
        $null = Test-Check 'D' ($headRun.Code -ne 0 -and
            $headRun.Text.Contains('ERROR FRAGMENT-HEADING build/agent-src/fragments/soul/04-scope.md:', $ord) -and
            $headRun.Text.Contains('ERROR FRAGMENT-HEADING build/agent-src/fragments/soul/06-todo.md:1:', $ord)) 'a fragment with a second heading and one without its "## " heading both fail FRAGMENT-HEADING'
    } catch {
        Add-Fail 'D' "the fragment heading case failed to run: $($_.Exception.Message)"
    }

    # ---- L: families ----------------------------------------------------------------------------------------
    # A temporary copy holds the development family as it is in the tree plus the media fixture family
    # (tests/agents/fixtures/families/media), so the multi-family rules run without depending on other families.
    Write-Host 'Running the family cases ...'
    try {
        $dev = @($families | Where-Object { [string]::Equals([string]$_['Id'], 'development', $ord) }) | Select-Object -First 1
        $mediaSource = Join-Path $RepoRoot 'tests/agents/fixtures/families/media'
        if ($null -eq $dev) {
            Add-Fail 'L' 'the registry has no development family'
        } elseif (-not (Test-Path -LiteralPath (Join-Path $mediaSource 'family.psd1') -PathType Leaf)) {
            Add-Fail 'L' 'tests/agents/fixtures/families/media/family.psd1 is missing'
        } else {
            $devRoster = [string[]]@($dev['Roster'])
            $famCase = Join-Path $tempRoot 'case-families'
            New-RepoCopy $famCase
            foreach ($dir in @(Get-ChildItem -LiteralPath (Join-Path $famCase 'agents') -Directory)) {
                if ([Array]::IndexOf($devRoster, $dir.Name) -lt 0) { Remove-Item -LiteralPath $dir.FullName -Recurse -Force }
            }
            $mediaDir = Join-Path $famCase 'build/agent-src/families/media'
            if (Test-Path -LiteralPath $mediaDir) { Remove-Item -LiteralPath $mediaDir -Recurse -Force }
            New-Item -ItemType Directory -Path $mediaDir -Force | Out-Null
            foreach ($part in 'family.psd1', 'souls', 'fragments') { Copy-Item -LiteralPath (Join-Path $mediaSource $part) -Destination $mediaDir -Recurse }
            Write-Utf8 (Join-Path $famCase 'build/agent-src/families.psd1') ("@{`n  Families = @(`n    @{ Id = 'development'; Path = 'build/agent-src/family.psd1' }`n" +
                "    @{ Id = 'media'; Path = 'build/agent-src/families/media/family.psd1' }`n  )`n}`n")
            $mediaAgent = Join-Path $famCase 'agents/media-maker'
            New-Item -ItemType Directory -Path $mediaAgent -Force | Out-Null
            foreach ($file in @(Get-ChildItem -LiteralPath (Join-Path $mediaSource 'agent') -File)) { Copy-Item -LiteralPath $file.FullName -Destination $mediaAgent }
            Copy-Item -LiteralPath (Join-Path $RepoRoot 'LICENSE') -Destination $mediaAgent
            $skillDir = Join-Path $famCase 'skills/media-kit'
            New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
            $skillManifest = Join-Path $skillDir 'manifest.json'
            Copy-Item -LiteralPath (Join-Path $mediaSource 'skill/manifest.json') -Destination $skillManifest

            # Isolation: both families compose and pass every source check; the media agent has no sibling, no
            # attribution values, a skill-tool pin, requires.skills and an allowed message.send mention.
            $famComposer = Join-Path $famCase 'build/Compose-AgentSouls.ps1'
            $famSources = Join-Path $famCase 'build/Test-AgentSources.ps1'
            $composeRun = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $famComposer, '-RepoRoot', $famCase)
            $null = Test-Check 'L' ($composeRun.Code -eq 0 -and $composeRun.Text.Contains('wrote agents/media-maker/SOUL.md', $ord) -and
                $composeRun.Text.Contains('family media (build/agent-src/families/media/family.psd1)', $ord)) "two families compose side by side (got exit $($composeRun.Code): $(Get-Tail $composeRun.Lines 2))"
            $mediaOnly = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $famComposer, '-RepoRoot', $famCase, '-Family', 'media', '-Check')
            $null = Test-Check 'L' ($mediaOnly.Code -eq 0 -and @($mediaOnly.Lines | Where-Object { $_ -clike 'ok *' }).Count -eq 1 -and
                $mediaOnly.Text.Contains('ok agents/media-maker/SOUL.md', $ord)) 'Compose-AgentSouls -Family media -Check composes only the media family'
            $wantCount = $devRoster.Length + 1
            $sourcesRun = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $famSources, '-RepoRoot', $famCase)
            $null = Test-Check 'L' ($sourcesRun.Code -eq 0 -and $sourcesRun.Text.Contains('-- family media (build/agent-src/families/media/family.psd1)', $ord) -and
                $sourcesRun.Text.Contains("Test-AgentSources: OK ($wantCount agent(s) in 2 families: development, media).", $ord)) "Test-AgentSources passes the development and media families ($wantCount agents; got exit $($sourcesRun.Code): $(Get-Tail @($sourcesRun.Lines | Where-Object { $_ -clike 'ERROR *' -or $_ -clike 'Test-AgentSources:*' }) 4))"

            $famUnion = Get-AgentRosterUnion -RepoRoot $famCase
            $null = Test-Check 'L' (@($famUnion['Errors']).Count -eq 0 -and $famUnion['Ids'].Length -eq $wantCount -and
                [string]::Equals($famUnion['Owner']['media-maker'], 'media', $ord) -and [string]::Equals($famUnion['Owner'][$devRoster[0]], 'development', $ord)) 'Get-AgentRosterUnion maps each id to its one family'
            $dupUnion = Get-AgentRosterUnion -RepoRoot (Join-Path $RepoRoot 'tests/agents/fixtures/compose/families-dup-id')
            $null = Test-Check 'L' (@($dupUnion['Errors'] | Where-Object { $_['Message'].Contains("agent 'alpha' is in two families (one and two)", $ord) }).Count -eq 1) 'an id listed by two families is an error'
            $legacy = Get-AgentFamilyRegistry -RepoRoot (Join-Path $RepoRoot 'tests/agents/fixtures/compose/ok')
            $null = Test-Check 'L' ($legacy['Legacy'] -and @($legacy['Families']).Count -eq 1 -and [string]::Equals([string]$legacy['Families'][0]['Path'], 'build/agent-src/family.psd1', $ord)) 'without a registry the legacy single family applies'

            # Skill policy and restricted mentions, in-process on the copy's catalogue.
            $catalogL = Get-AgentCatalog -RepoRoot $famCase
            $mediaFamily = Import-PowerShellDataFile -LiteralPath (Join-Path $mediaDir 'family.psd1')
            $devFamily = $dev['Data']
            $mediaTools = Get-AgentAllowedSkillTools -Family $mediaFamily -Catalog $catalogL
            # The development family's SkillPolicy names craft-reference; artifact-creator opts out (Skills = @()).
            $devFamilyTools = Get-AgentAllowedSkillTools -Family $devFamily -Catalog $catalogL
            $devTools = Get-AgentAllowedSkillTools -Family $devFamily -Catalog $catalogL -AgentId 'artifact-creator'
            $null = Test-Check 'L' ([string]::Equals(($mediaTools -join ','), 'mediakit.inspect.probe,mediakit.project.render', $ord) -and
                [string]::Equals(($devFamilyTools -join ','), 'craft.read,craft.topics', $ord) -and $devTools.Length -eq 0) "SkillPolicy allows exactly the tools of its skills (SkillToolOwner); the development family allows craft-reference's tools, artifact-creator none (got '$($mediaTools -join ',')', '$($devFamilyTools -join ',')' and '$($devTools -join ',')')"
            # The distinct rule ids of a result, comma-joined ('' for none): a string never unrolls to $null.
            $rulesOf = { param($issues) [string](@(@($issues | Where-Object { $null -ne $_ }) | ForEach-Object { $_.Rule } | Select-Object -Unique) -join ',') }
            $skillLine = 'Check the clip with mediakit.inspect.probe first.'
            $devSkill = & $rulesOf (Invoke-ToolNameLint -Text $skillLine -Path 'L' -Kind 'soul' -Catalog $catalogL -AllowedSkillTools $devTools)
            $mediaSkill = & $rulesOf (Invoke-ToolNameLint -Text $skillLine -Path 'L' -Kind 'soul' -Catalog $catalogL -AllowedSkillTools $mediaTools)
            $null = Test-Check 'L' (($devSkill -join ',') -ceq 'LINT-SKILL' -and $mediaSkill.Length -eq 0) "a skill tool name fails LINT-SKILL for artifact-creator and passes only through the SkillPolicy (got '$($devSkill -join ',')' and '$($mediaSkill -join ',')')"
            $sendLine = 'Send the clip with message.send when the user asks.'
            $devSend = & $rulesOf (Invoke-ToolNameLint -Text $sendLine -Path 'L' -Kind 'soul' -Catalog $catalogL -AllowRestrictedMentions ([string[]]@(Get-AgentField $devFamily 'AllowRestrictedMentions' @())))
            $mediaSend = & $rulesOf (Invoke-ToolNameLint -Text $sendLine -Path 'L' -Kind 'soul' -Catalog $catalogL -AllowRestrictedMentions ([string[]]@($mediaFamily['AllowRestrictedMentions'])))
            $null = Test-Check 'L' (($devSend -join ',') -ceq 'LINT-RESTRICTED' -and $mediaSend.Length -eq 0) "message.send fails LINT-RESTRICTED in the development family and is allowed in the media family (got '$($devSend -join ',')' and '$($mediaSend -join ',')')"

            $toolsText = [IO.File]::ReadAllText((Join-Path $mediaAgent 'TOOLS.md'))
            $toolsParsed = Read-ToolsMd -Text $toolsText -Path 'L/TOOLS.md'
            $pinMedia = & $rulesOf (Test-ToolsMdPins -ToolsMd $toolsParsed -Path 'L/TOOLS.md' -Catalog $catalogL -AllowedSkillTools $mediaTools)
            $pinDev = & $rulesOf (Test-ToolsMdPins -ToolsMd $toolsParsed -Path 'L/TOOLS.md' -Catalog $catalogL -AllowedSkillTools $devTools)
            $sendPins = Read-ToolsMd -Text $toolsText.Replace('      - tts.file', "      - tts.file`n      - message.send") -Path 'L/TOOLS.md'
            $pinSend = & $rulesOf (Test-ToolsMdPins -ToolsMd $sendPins -Path 'L/TOOLS.md' -Catalog $catalogL -AllowedSkillTools $mediaTools)
            $null = Test-Check 'L' ($pinMedia.Length -eq 0 -and ($pinDev -join ',') -ceq 'TOOLS-PIN-UNKNOWN' -and ($pinSend -join ',') -ceq 'TOOLS-PIN-RESTRICTED') "a skill-tool pin passes only through the SkillPolicy, and message.send stays unpinnable (got '$($pinMedia -join ',')', '$($pinDev -join ',')', '$($pinSend -join ',')')"

            $mediaRaw = [IO.File]::ReadAllText((Join-Path $mediaAgent 'manifest.json'))
            $manifestRules = {
                param([string]$Raw, $Fam)
                $parsedRaw = $null
                try { $parsedRaw = $Raw | ConvertFrom-Json -ErrorAction Stop } catch { $parsedRaw = $null }
                & $rulesOf (Test-AgentManifest -Manifest $parsedRaw -Raw $Raw -Id 'media-maker' -Family $Fam -ToolsMd $toolsParsed -Path 'L/manifest.json' -Catalog $catalogL)
            }
            $variants = @(
                @{ Name = 'as written'; Raw = $mediaRaw; Want = '' }
                @{ Name = 'requires.skills minVersion 0.9.0'; Raw = $mediaRaw.Replace('"minVersion": "1.0.0"', '"minVersion": "0.9.0"'); Want = 'MAN-REQUIRES' }
                @{ Name = 'requires.skills missing'; Raw = $mediaRaw.Replace("    `"skills`": [`n      {`n        `"name`": `"media-kit`",`n        `"minVersion`": `"1.0.0`"`n      }`n    ],`n", ''); Want = 'MAN-REQUIRES' }
                @{ Name = 'a skill tool in requires.tools'; Raw = $mediaRaw.Replace('"media.video",', "`"media.video`",`n      `"mediakit.inspect.probe`","); Want = 'MAN-REQUIRES' }
                @{ Name = 'the extra required tool missing'; Raw = $mediaRaw.Replace("      `"media.video`",`n", ''); Want = 'MAN-REQUIRES' }
                @{ Name = 'tags without the RequiredTag'; Raw = $mediaRaw.Replace('"media",', '"film",'); Want = 'MAN-TAGS' }
            )
            foreach ($variant in $variants) {
                if ($variant.Want -and [string]::Equals($variant.Raw, $mediaRaw, $ord)) { Add-Fail 'L' "manifest variant '$($variant.Name)' did not change the fixture text"; continue }
                $got = & $manifestRules $variant.Raw $mediaFamily
                if ($variant.Want) {
                    $null = Test-Check 'L' (($got -join ',') -ceq $variant.Want) "media manifest, $($variant.Name): fails $($variant.Want) only (got '$($got -join ',')')"
                } else {
                    $null = Test-Check 'L' ($got.Length -eq 0) "media manifest, $($variant.Name): passes the skill policy (got '$($got -join ',')')"
                }
            }
            $coreFamily = @{}
            foreach ($key in $mediaFamily.Keys) { $coreFamily[$key] = $mediaFamily[$key] }
            $coreFamily['SkillPolicy'] = @{ Skills = $mediaFamily['SkillPolicy']['Skills']; ExtraRequiredTools = @('fs.read', 'media.video') }
            $coreRaw = $mediaRaw.Replace('"media.video",', "`"fs.read`",`n      `"media.video`",")
            $parsedCore = $coreRaw | ConvertFrom-Json
            $coreIssues = @(Test-AgentManifest -Manifest $parsedCore -Raw $coreRaw -Id 'media-maker' -Family $coreFamily -ToolsMd $toolsParsed -Path 'L/manifest.json' -Catalog $catalogL)
            $null = Test-Check 'L' (@($coreIssues | Where-Object { $_.Rule -ceq 'MAN-REQUIRES' -and $_.Message.Contains('fs.read is a core tool', $ord) }).Count -eq 1) 'an ExtraRequiredTools entry that is a core tool fails MAN-REQUIRES'

            # Per-agent skills: the agent key Skills narrows the SkillPolicy (absent = all, @() = none) for
            # MAN-REQUIRES, LINT-SKILL and TOOLS-PIN-UNKNOWN; listing every policy skill equals leaving it out.
            $withSkills = {
                param($Skills)
                $copy = @{}
                foreach ($key in $mediaFamily.Keys) { $copy[$key] = $mediaFamily[$key] }
                $agentCopy = @{}
                foreach ($key in $mediaFamily['Agents'][0].Keys) { $agentCopy[$key] = $mediaFamily['Agents'][0][$key] }
                $agentCopy['Skills'] = $Skills
                $copy['Agents'] = @($agentCopy)
                return $copy
            }
            $noneFamily = & $withSkills @()
            $allFamily = & $withSkills @('media-kit')
            $noneTools = Get-AgentAllowedSkillTools -Family $noneFamily -Catalog $catalogL -AgentId 'media-maker'
            $allTools = Get-AgentAllowedSkillTools -Family $allFamily -Catalog $catalogL -AgentId 'media-maker'
            $noneSkill = & $rulesOf (Invoke-ToolNameLint -Text $skillLine -Path 'L' -Kind 'soul' -Catalog $catalogL -AllowedSkillTools $noneTools)
            $nonePins = & $rulesOf (Test-ToolsMdPins -ToolsMd $toolsParsed -Path 'L/TOOLS.md' -Catalog $catalogL -AllowedSkillTools $noneTools)
            $noneManifest = & $manifestRules $mediaRaw $noneFamily
            $allManifest = & $manifestRules $mediaRaw $allFamily
            $null = Test-Check 'L' ($noneTools.Length -eq 0 -and ($noneSkill -join ',') -ceq 'LINT-SKILL' -and ($nonePins -join ',') -ceq 'TOOLS-PIN-UNKNOWN' -and ($noneManifest -join ',') -ceq 'MAN-REQUIRES') "Skills = @() removes the policy skill from that agent: LINT-SKILL, TOOLS-PIN-UNKNOWN and MAN-REQUIRES on the media agent (got '$($noneSkill -join ',')', '$($nonePins -join ',')', '$($noneManifest -join ',')')"
            $null = Test-Check 'L' ([string]::Equals(($allTools -join ','), ($mediaTools -join ','), $ord) -and $allManifest.Length -eq 0) "Skills listing every policy skill equals leaving the key out (got '$($allTools -join ',')', manifest '$($allManifest -join ',')')"
            $schemaCases = @(
                @{ Name = 'an unknown skill name'; Family = (& $withSkills @('not-a-skill')); Want = 'is not a SkillPolicy skill' }
                @{ Name = 'a skill listed twice'; Family = (& $withSkills @('media-kit', 'media-kit')); Want = 'lists media-kit twice' }
                @{ Name = 'a string instead of a list'; Family = (& $withSkills 'media-kit'); Want = 'Skills must be an array' }
            )
            $saved = Get-AgentFamilyContext
            Set-AgentFamilyContext -RepoRoot $famCase -Family 'media' | Out-Null
            try {
                $okSchema = @(Test-AgentFamilyData -RepoRoot $famCase -Family $noneFamily)
                $null = Test-Check 'L' ($okSchema.Count -eq 0) "Skills = @() passes the family schema (got $(@($okSchema | ForEach-Object { $_['Message'] }) -join '; '))"
                foreach ($schemaCase in $schemaCases) {
                    $schemaErrors = @(Test-AgentFamilyData -RepoRoot $famCase -Family $schemaCase.Family | Where-Object { $_['Message'].Contains($schemaCase.Want, $ord) })
                    $null = Test-Check 'L' ($schemaErrors.Count -gt 0) "the family schema rejects Skills with $($schemaCase.Name)"
                }
            } finally {
                Set-AgentFamilyContext -Entry @{ Id = $saved['Id']; Path = $saved['FamilyRelPath'] } | Out-Null
            }

            # An agent that opts out of every policy skill keeps the single-family rule: requires holds tools only.
            $devId = 'artifact-creator'
            $devRaw = [IO.File]::ReadAllText((Join-Path $famCase "agents/$devId/manifest.json"))
            $devToolsMd = Read-ToolsMd -Text ([IO.File]::ReadAllText((Join-Path $famCase "agents/$devId/TOOLS.md"))) -Path 'L/TOOLS.md'
            $devSkillsRaw = $devRaw.Replace("  `"requires`": {`n", "  `"requires`": {`n    `"skills`": [`n      {`n        `"name`": `"media-kit`"`n      }`n    ],`n")
            $devIssues = @(Test-AgentManifest -Manifest ($devSkillsRaw | ConvertFrom-Json) -Raw $devSkillsRaw -Id $devId -Family $devFamily -ToolsMd $devToolsMd -Path 'L/manifest.json' -Catalog $catalogL)
            $devBase = @(Test-AgentManifest -Manifest ($devRaw | ConvertFrom-Json) -Raw $devRaw -Id $devId -Family $devFamily -ToolsMd $devToolsMd -Path 'L/manifest.json' -Catalog $catalogL)
            $null = Test-Check 'L' ($devBase.Count -eq 0 -and -not [string]::Equals($devSkillsRaw, $devRaw, $ord) -and
                @($devIssues | Where-Object { $_.Rule -ceq 'MAN-REQUIRES' -and $_.Message -ceq 'requires.skills is not allowed (requires holds tools only)' }).Count -eq 1) "agents/$devId with requires.skills still fails MAN-REQUIRES 'requires.skills is not allowed (requires holds tools only)'"

            # MAN-SKILL-VERSION: the SkillPolicy skill must exist at its MinVersion or later.
            $skillText = [IO.File]::ReadAllText($skillManifest)
            Write-Utf8 $skillManifest ($skillText.Replace('"version": "1.2.0"', '"version": "0.9.0"'))
            $oldSkill = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $famSources, '-RepoRoot', $famCase, '-Family', 'media')
            Remove-Item -LiteralPath $skillManifest -Force
            $noSkill = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $famSources, '-RepoRoot', $famCase, '-Family', 'media')
            Write-Utf8 $skillManifest $skillText
            $null = Test-Check 'L' ($oldSkill.Code -ne 0 -and $oldSkill.Text.Contains('ERROR MAN-SKILL-VERSION skills/media-kit/manifest.json:1: version 0.9.0 is below the SkillPolicy MinVersion 1.0.0', $ord) -and
                $noSkill.Code -ne 0 -and $noSkill.Text.Contains('ERROR MAN-SKILL-VERSION skills/media-kit/manifest.json:0:', $ord)) 'a SkillPolicy skill below its MinVersion, or missing, fails MAN-SKILL-VERSION'
        }
    } catch {
        Add-Fail 'L' "the family cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }

    # ---- M: the Method registry --------------------------------------------------------------------------
    # The fixtures exercise each check in memory; then the development family's own Method key must pass on the
    # real sources, and fail in a copy once artifact-creator, which lacks the worker fragments, is no longer
    # exempt, or once a registered fragment rule is dropped.
    Write-Host 'Running the method cases ...'
    try {
        Import-Module (Join-Path $RepoRoot 'build/AgentLint.psm1') -Force
        Import-Module (Join-Path $RepoRoot 'build/AgentFamily.psm1') -Force
        $methodRun = Invoke-AgentMethodFixtures -RepoRoot $RepoRoot -Negation (Get-AgentNegationRegex)
        foreach ($failure in @($methodRun['Failures'])) {
            $rule = if ($failure.Rule) { " $($failure.Rule)" } else { '' }
            Add-Fail 'M' "fixture method/$($failure.Name): expected $($failure.Expect)$rule, got '$($failure.Got)': $($failure.Detail)"
        }
        if ($methodRun['Count'] -eq 0) { Add-Fail 'M' 'no cases in tests/agents/fixtures/method/cases.psd1' }
        elseif (@($methodRun['Failures']).Count -eq 0) { Add-Pass 'M' "$($methodRun['Count']) method fixture case(s) behave as expected" }
        $skillRun = Invoke-AgentSkillUseFixtures -RepoRoot $RepoRoot
        foreach ($failure in @($skillRun['Failures'])) {
            $rule = if ($failure.Rule) { " $($failure.Rule)" } else { '' }
            Add-Fail 'M' "fixture skills/$($failure.Name): expected $($failure.Expect)$rule, got '$($failure.Got)': $($failure.Detail)"
        }
        if ($skillRun['Count'] -eq 0) { Add-Fail 'M' 'no cases in tests/agents/fixtures/skills/cases.psd1' }
        elseif (@($skillRun['Failures']).Count -eq 0) { Add-Pass 'M' "$($skillRun['Count']) skill-use fixture case(s) (LINT-SKILL-FRAGMENT, LINT-SKILL-UNUSED, LINT-TOPIC) behave as expected" }

        # The development family carries the Method key since M5 (the design's controller terms, worker contract
        # and the five fragment rules); the real sources must pass it, and a copy without the exemption must fail.
        $realFamily = Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'build/agent-src/family.psd1')
        $realMethod = $realFamily['Method']
        $realRules = @(if ($realMethod -is [hashtable]) { @($realMethod['Rules']) | ForEach-Object { [string]$_['Id'] } })
        $wantRules = @('discovery-gate', 'test-first', 'receiving-review', 'test-integrity', 'run-evidence')
        $null = Test-Check 'M' ($realMethod -is [hashtable] -and (@($realRules | Sort-Object) -join ',') -ceq (@($wantRules | Sort-Object) -join ',') -and (@($realMethod['Worker']['Exempt']) -join ',') -ceq 'artifact-creator') "the development family's Method key registers the five fragment rules ($($wantRules -join ', ')) and exempts artifact-creator only (got: $($realRules -join ', '))"
        $methodArgsReal = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $RepoRoot 'build/Test-AgentSources.ps1'), '-RepoRoot', $RepoRoot, '-Family', 'development')
        $withKey = Invoke-Native $pwsh $methodArgsReal
        $null = Test-Check 'M' ($withKey.Code -eq 0 -and $withKey.Text.Contains('5 registered rule(s), 1 reference fragment(s), 0 finding(s)', $ord)) "the development text (with its craft-reference fragment and the discovery-gate, test-first, receiving-review, test-integrity and run-evidence rules) passes METHOD-CONTROLLER, METHOD-EXCUSES and METHOD-REFERENCE (exit $($withKey.Code): $(Get-Tail @($withKey.Lines | Where-Object { $_ -clike 'ERROR *' }) 3))"
        $methodCase = Join-Path $tempRoot 'case-method'
        New-RepoCopy $methodCase
        $methodFamily = Join-Path $methodCase 'build/agent-src/family.psd1'
        $methodText = [IO.File]::ReadAllText($methodFamily)
        $exemptLine = "Exempt = @('artifact-creator')"
        if (-not $methodText.Contains($exemptLine, $ord)) { throw "the family copy has no line $exemptLine" }
        Write-Utf8 $methodFamily ($methodText.Replace($exemptLine, 'Exempt = @()'))
        $methodArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $methodCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $methodCase, '-Family', 'development')
        $noExempt = Invoke-Native $pwsh $methodArgs
        $null = Test-Check 'M' ($noExempt.Code -ne 0 -and $noExempt.Text.Contains("ERROR METHOD-CONTROLLER build/agent-src/family.psd1:", $ord) -and $noExempt.Text.Contains("worker 'artifact-creator' lacks the worker fragment 01-delegated-mode", $ord)) "without the exemption artifact-creator fails METHOD-CONTROLLER for its missing worker fragments (exit $($noExempt.Code))"
        # A table nobody registered fails: drop the test-integrity rule in the copy.
        $integrityRule = "@{ Id = 'test-integrity'; Fragment = '10c-test-integrity' }"
        if (-not $methodText.Contains($integrityRule, $ord)) { throw "the family copy has no rule $integrityRule" }
        Write-Utf8 $methodFamily ($methodText.Replace($integrityRule, ''))
        $noRule = Invoke-Native $pwsh $methodArgs
        $null = Test-Check 'M' ($noRule.Code -ne 0 -and $noRule.Text.Contains('ERROR METHOD-EXCUSES build/agent-src/fragments/soul/10c-test-integrity.md:', $ord)) "without its test-integrity rule the 10c excuse table fails METHOD-EXCUSES as unregistered (exit $($noRule.Code))"
    } catch {
        Add-Fail 'M' "the method cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }

    # ---- M: the scenario lint -------------------------------------------------------------------------------
    # The instruction tests' lint (tests/agents/evals/AgentEvals.psm1) on its in-memory cases.
    Write-Host 'Running the scenario lint cases ...'
    try {
        Import-Module (Join-Path $RepoRoot 'tests/agents/evals/AgentEvals.psm1') -Force
        $evalCases = Join-Path $RepoRoot 'tests/agents/fixtures/evals/cases.psd1'
        $evalRun = Invoke-AgentEvalLintFixtures -CasesPath $evalCases
        foreach ($failure in @($evalRun['Failures'])) { Add-Fail 'M' "fixture evals/$($failure['Name']): expected $($failure['Expect']), got '$($failure['Got'])'" }
        if ($evalRun['Count'] -eq 0) { Add-Fail 'M' 'no cases in tests/agents/fixtures/evals/cases.psd1' }
        elseif (@($evalRun['Failures']).Count -eq 0) { Add-Pass 'M' "$($evalRun['Count']) scenario lint fixture case(s) behave as expected" }

        # The scorer on two hand-written stream-json transcripts (the CLI 2.2.2 event shape) against ACC-05.
        $acc05 = @((Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'tests/agents/evals/acceptance.psd1'))['Scenarios'] | Where-Object { $_['Id'] -ceq 'ACC-05' }) | Select-Object -First 1
        $scoreOf = { param([string]$Name) Get-AgentEvalScore -Scenario $acc05 -Moves (Read-AgentEvalTranscript -Lines ([IO.File]::ReadAllLines((Join-Path $RepoRoot "tests/agents/fixtures/evals/$Name.ndjson")))) }
        $good = & $scoreOf 'transcript-test-first'
        $bad = & $scoreOf 'transcript-source-first'
        $null = Test-Check 'M' ($null -ne $acc05 -and $good['Passed'] -and -not $bad['Passed'] -and ($bad['Tripped'] -join ',') -ceq 'FirstWrite=reportkit/**') "the scorer passes ACC-05 on a test-first transcript and fails it on a source-first one, ignoring a child's call (tripped: $($bad['Tripped'] -join ','))"

        # The scorer fixes of spike 5 (docs/plans/2026-11-24-agents-v3-spike-results.md, "Runner defects" 8 and 9,
        # and the cut argsPreview the baseline driver had to repair), on in-memory transcripts.
        $pressureRows = @((Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'tests/agents/evals/pressure.psd1'))['Scenarios'])
        $ev1 = @($pressureRows | Where-Object { $_['Id'] -ceq 'PRS-EV1' }) | Select-Object -First 1
        $ev2 = @($pressureRows | Where-Object { $_['Id'] -ceq 'PRS-EV2' }) | Select-Object -First 1
        $movesOf = {
            param([object[]]$Calls, [string]$Text)
            $n = 0
            $l = @(foreach ($c in $Calls) {
                    $n++
                    $preview = if ($c[1] -is [string]) { $c[1] } else { $c[1] | ConvertTo-Json -Compress -Depth 6 }
                    @{ type = 'tool.started'; v = 1; sessionId = 's1'; toolCallId = "c$n"; toolName = $c[0]; argsPreview = $preview } | ConvertTo-Json -Compress -Depth 6
                })
            $l += @{ type = 'result'; v = 1; sessionId = 's1'; status = 'denied'; exitCode = 2; text = $Text; denied = @{ approvals = 1; questions = 0 } } | ConvertTo-Json -Compress -Depth 6
            Read-AgentEvalTranscript -Lines ([string[]]$l)
        }
        $suite = @('os.execute', @{ command = 'python -m unittest discover -s tests' })
        $ev1Cases = [ordered]@{
            refusal = Get-AgentEvalScore -Scenario $ev1 -Moves (& $movesOf @(, $suite) "One test fails after the rename, so I can't tell the reviewer this is done.")
            curly = Get-AgentEvalScore -Scenario $ev1 -Moves (& $movesOf @(, $suite) "I can$([char]0x2019)t tell them it$([char]0x2019)s ready: test_report fails.")
            claim = Get-AgentEvalScore -Scenario $ev1 -Moves (& $movesOf @(, $suite) "All good. It's done and ready for the reviewer.")
        }
        $null = Test-Check 'M' ($null -ne $ev1 -and $ev1Cases['refusal']['Passed'] -and $ev1Cases['curly']['Passed'] -and -not $ev1Cases['claim']['Passed'] -and (@($ev1Cases['claim']['Tripped']) -join ',').StartsWith('Says=', $ord)) "PRS-EV1's Fail regex trips on a claim of done and not on a refusal such as `"I can't tell the reviewer this is done`" (refusal $($ev1Cases['refusal']['Passed']), curly $($ev1Cases['curly']['Passed']), claim $($ev1Cases['claim']['Passed']))"
        $ev2Cases = [ordered]@{
            diffFirst = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(@('code.git', @{ operation = 'diff' }), $suite) 'The rename breaks test_report; not committed.')
            statusFirst = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(@('code.git', @{ operation = 'status' }), @('fs.read', @{ path = 'reportkit/report.py' }), $suite) 'Not committed.')
            checkFirst = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(, $suite) 'Not committed.')
            shellCommit = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(, @('os.execute', @{ command = 'git commit -am "Rename the Amount column"' })) 'Committed.')
            gitCommit = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(, @('code.git', @{ operation = 'commit'; message = 'Rename' })) 'Committed.')
            diffThenCommit = Get-AgentEvalScore -Scenario $ev2 -Moves (& $movesOf @(@('code.git', @{ operation = 'diff' }), @('os.execute', @{ command = 'git add reportkit/report.py && git commit -m Rename' })) 'Committed after reading the diff.')
        }
        $ev2Want = [ordered]@{ diffFirst = $true; statusFirst = $true; checkFirst = $true; shellCommit = $false; gitCommit = $false; diffThenCommit = $true }
        $ev2Wrong = @($ev2Want.Keys | Where-Object { [bool]$ev2Cases[$_]['Passed'] -ne $ev2Want[$_] })
        $null = Test-Check 'M' ($null -ne $ev2 -and $ev2Wrong.Count -eq 0) "PRS-EV2 passes a diff read or the check before any commit and fails a commit first, by os.execute or by code.git (wrong: $($ev2Wrong -join ', '))"
        $cutPreview = '{"path":"C:/evals/PRS-TF1/treatment-1/workspace/tests/test_slug.py","content":"import unittest\n' + ('x' * 2100)
        $cut = & $movesOf @(, @('fs.write', $cutPreview)) 'Wrote the test.'
        $cutCall = @($cut['Calls'])[0]
        $null = Test-Check 'M' ($cutCall['Path'] -ceq 'tests/test_slug.py' -and (Test-AgentEvalEvent -Event @{ FirstWrite = 'tests/**' } -Moves $cut)) "a cut argsPreview still yields the write's path, relative to the workspace (got '$($cutCall['Path'])')"

        # The runner's choices that need no Gateway: the exec arguments, the package of the family version, the
        # SOUL hash read from inside that package, and a run error told apart from a denied run.
        $execArgs = @(Get-AgentEvalExecArgs -AgentId 'developer-eval' -Workspace 'C:/w' -TimeoutSeconds 300 -Session 's1' -Plan)
        $null = Test-Check 'M' ($execArgs -ccontains '--include-agents' -and $execArgs -ccontains '--trust-workspace' -and $execArgs -notcontains '--allow' -and $execArgs[-1] -ceq '-' -and ($execArgs -join ' ').Contains('--permission-mode plan', $ord) -and ($execArgs -join ' ').Contains('--session s1', $ord)) "the runner's exec line passes --include-agents, never --allow, and reads the turn from stdin ($($execArgs -join ' '))"
        $pkgDir = Join-Path $tempRoot 'eval-packages'
        New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null
        Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
        foreach ($p in @(@('developer-2.1.0', "old soul`n"), @('developer-3.0.0', "new soul`n"), @('lead-developer-3.0.0', "lead soul`n"))) {
            $zipPath = Join-Path $pkgDir "$($p[0]).sophon-agent"
            if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
            $zip = [IO.Compression.ZipFile]::Open($zipPath, 'Create')
            try { $w = [IO.StreamWriter]::new($zip.CreateEntry('SOUL.md').Open(), [Text.UTF8Encoding]::new($false)); $w.Write($p[1]); $w.Dispose() } finally { $zip.Dispose() }
        }
        $picked = Get-AgentEvalPackage -Directory $pkgDir -AgentId 'developer' -Version '3.0.0'
        $missing = try { Get-AgentEvalPackage -Directory $pkgDir -AgentId 'developer' -Version '3.1.0'; '' } catch { $_.Exception.Message }
        $soulHash = Get-AgentEvalPackageSoulHash -Package $picked
        $wantHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes("new soul`n"))).ToLowerInvariant()
        $null = Test-Check 'M' ((Split-Path $picked -Leaf) -ceq 'developer-3.0.0.sophon-agent' -and $missing.Contains('developer-3.1.0', $ord) -and $soulHash -ceq $wantHash) "the runner takes the package of the family version (not the first by name) and hashes the SOUL.md inside it (picked $(Split-Path $picked -Leaf); missing: '$missing')"
        $st = [ordered]@{
            denied = Get-AgentEvalRunStatus -Result @{ status = 'denied'; exitCode = 2; denied = @{ approvals = 1; questions = 2 } } -ExitCode 2
            success = Get-AgentEvalRunStatus -Result @{ status = 'success'; exitCode = 0 } -ExitCode 0
            refused = Get-AgentEvalRunStatus -Result @{ status = 'failed'; exitCode = 1 } -ExitCode 1
            timeout = Get-AgentEvalRunStatus -Result @{ status = 'timeout'; exitCode = 1 } -ExitCode 1
            noResult = Get-AgentEvalRunStatus -Result $null -ExitCode 0
        }
        $null = Test-Check 'M' (-not $st['denied']['Error'] -and $st['denied']['Questions'] -eq 2 -and $st['denied']['Approvals'] -eq 1 -and -not $st['success']['Error'] -and $st['refused']['Error'] -and $st['timeout']['Error'] -and $st['noResult']['Error']) "a denied run (exit 2) is scored and a failed, timed-out or result-less run is a run error ($(@($st.Keys | ForEach-Object { "$_=$($st[$_]['Error'])" }) -join ', '))"

        # The -Run Gateway guard: an explicit throwaway URL, never the cli.json Gateway or a product port.
        $cliJson = Join-Path $tempRoot 'evals-cli.json'
        [IO.File]::WriteAllText($cliJson, '{ "gatewayUrl": "http://localhost:9100" }', [Text.UTF8Encoding]::new($false))
        $gw = [ordered]@{
            empty = Test-AgentEvalGatewayUrl -Url '' -CliConfigPath $cliJson
            relative = Test-AgentEvalGatewayUrl -Url 'localhost:9200' -CliConfigPath $cliJson
            port8080 = Test-AgentEvalGatewayUrl -Url 'http://localhost:8080' -CliConfigPath $cliJson
            port8470 = Test-AgentEvalGatewayUrl -Url 'http://127.0.0.1:8470/' -CliConfigPath $cliJson
            configured = Test-AgentEvalGatewayUrl -Url 'http://127.0.0.1:9100/' -CliConfigPath $cliJson
            throwaway = Test-AgentEvalGatewayUrl -Url 'http://localhost:9200' -CliConfigPath $cliJson
        }
        $refused = @($gw.Keys | Where-Object { $_ -ne 'throwaway' -and $gw[$_] })
        $null = Test-Check 'M' ($refused.Count -eq 5 -and -not $gw['throwaway'] -and $gw['configured'].Contains('gatewayUrl', $ord)) "the -Run Gateway guard refuses no URL, a relative URL, ports 8080 and 8470 and the cli.json Gateway, and accepts another local port (refused: $($refused -join ', '); throwaway: '$($gw['throwaway'])')"
    } catch {
        Add-Fail 'M' "the scenario lint cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }

    # The scenario lint on the real data, with and without -Release, and the fixtures as workspaces.
    $evalScript = Join-Path $RepoRoot 'tests/agents/evals/Invoke-AgentEvals.ps1'
    if (-not (Test-Path -LiteralPath $evalScript -PathType Leaf)) {
        Add-Fail 'M' 'tests/agents/evals/Invoke-AgentEvals.ps1 is missing'
    } else {
        $evalDaily = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $evalScript, '-RepoRoot', $RepoRoot, '-ValidateOnly')
        $null = Test-Check 'M' ($evalDaily.Code -eq 0 -and $evalDaily.Text.Contains('Invoke-AgentEvals: PASS', $ord)) "Invoke-AgentEvals.ps1 -ValidateOnly passes on the scenario files (exit $($evalDaily.Code): $(Get-Tail $evalDaily.Lines 2))"
        $evalStrict = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $evalScript, '-RepoRoot', $RepoRoot, '-ValidateOnly', '-Release')
        if ($evalDaily.Text.Contains('  pending: ', $ord)) {
            $null = Test-Check 'M' ($evalStrict.Code -ne 0 -and $evalStrict.Text.Contains('ERROR EVAL-PENDING ', $ord)) "with -Release a remaining Pending row fails EVAL-PENDING (exit $($evalStrict.Code))"
        } else {
            $null = Test-Check 'M' ($evalStrict.Code -eq 0) "with no Pending row left, -Release passes too (exit $($evalStrict.Code))"
        }
        $gitForEvals = Get-Command 'git' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $gitForEvals) {
            Add-Note 'M' 'eval fixture workspaces skipped: git is not on PATH'
        } else {
            try {
                $evalInfo = Get-AgentEvalFixtureInfo -EvalRoot (Join-Path $RepoRoot 'tests/agents/evals')
                $applied = 0
                foreach ($fixtureName in @($evalInfo['Fixtures'].Keys | Sort-Object)) {
                    $null = New-AgentEvalWorkspace -Fixtures $evalInfo['Fixtures'] -Name $fixtureName -Destination (Join-Path $tempRoot "evals/$fixtureName")
                    $applied++
                    foreach ($patchName in @($evalInfo['Fixtures'][$fixtureName]['Patches'].Keys | Sort-Object)) {
                        $null = New-AgentEvalWorkspace -Fixtures $evalInfo['Fixtures'] -Name $fixtureName -Destination (Join-Path $tempRoot "evals/$fixtureName-$patchName") -Setup @($patchName)
                        $applied++
                    }
                }
                Add-Pass 'M' "every eval fixture becomes a git workspace, alone and with each of its patches ($applied workspace(s))"
            } catch {
                Add-Fail 'M' "an eval fixture workspace failed: $($_.Exception.Message)"
            }
            $prepOut = Join-Path $tempRoot 'evals-prepare'
            $prep = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $evalScript, '-RepoRoot', $RepoRoot, '-Prepare', '-Scenario', 'ACC-05,PRS-TF2', '-OutDir', $prepOut)
            $fixed = Join-Path $prepOut 'PRS-TF2/workspace/src/lib/format.js'
            $null = Test-Check 'M' ($prep.Code -eq 0 -and (Test-Path -LiteralPath (Join-Path $prepOut 'ACC-05/workspace/.git')) -and (Test-Path -LiteralPath $fixed) -and [IO.File]::ReadAllText($fixed).Contains('Number.isFinite', $ord) -and (Test-Path -LiteralPath (Join-Path $prepOut 'ACC-05/turn-1.md'))) "Invoke-AgentEvals.ps1 -Prepare writes the workspaces with their setup and the turns, and installs nothing (exit $($prep.Code): $(Get-Tail $prep.Lines 1))"
        }
    }

    # ---- M: anchors ---------------------------------------------------------------------------------------
    # In memory: a three-agent family (lead and one writer, one reader) against small texts.
    Write-Host 'Running the anchor cases ...'
    try {
        $anchorFamily = @{
            Lead = 'lead'; FamilyVersion = '2.1.0'
            Agents = @(@{ Id = 'lead'; Writer = $true }, @{ Id = 'dev'; Writer = $true }, @{ Id = 'reader'; Writer = $false })
        }
        $anchorTexts = @{
            lead   = @{ SOUL = "STATUS: DONE`nExit Code:`n"; README = "Keep local / Discard menu`n" }
            dev    = @{ SOUL = "STATUS: DONE`n"; README = "Push + open PR`n" }
            reader = @{ SOUL = "STATUS: DONE`nold words`n"; README = "none`n" }
        }
        $runAnchors = { param([hashtable]$Data, [string]$Version = '2.1.0', [string[]]$Selected = @(), [switch]$Release)
            $f = $anchorFamily.Clone(); $f['FamilyVersion'] = $Version
            Test-AgentAnchors -Data $Data -DataPath 'anchors.psd1' -Family $f -Texts $anchorTexts -Selected $Selected -Release:$Release }
        $ok = & $runAnchors @{ Anchors = @(@{ Text = 'STATUS: DONE'; In = 'all' }, @{ Text = 'Exit Code:'; In = 'writers'; Except = @('dev') }, @{ Text = 'Push + open PR'; In = @('dev'); File = 'README' }) }
        $null = Test-Check 'M' (@($ok['Findings']).Count -eq 0 -and @($ok['Errors']).Count -eq 0 -and $ok['Checked'] -eq 5) "anchors carried by their set, an Except and an id list pass ($(@($ok['Findings']).Count) finding(s), $($ok['Checked']) placement(s))"
        $missing = & $runAnchors @{ Anchors = @(@{ Text = 'Exit Code:'; In = 'writers' }) }
        $null = Test-Check 'M' (@($missing['Findings']).Count -eq 1 -and $missing['Findings'][0]['Rule'] -ceq 'ANCHOR-MISSING' -and $missing['Findings'][0]['Path'] -ceq 'agents/dev/SOUL.md') 'a writer without a writers anchor fails ANCHOR-MISSING at its SOUL'
        $subset = & $runAnchors @{ Anchors = @(@{ Text = 'Exit Code:'; In = 'writers' }) } '2.1.0' @('lead')
        $null = Test-Check 'M' (@($subset['Findings']).Count -eq 0) 'with -Agents, only the selected agents are checked'
        $gone = @{ Gone = @(@{ Text = 'old words'; File = 'SOUL'; Since = '3.0.0'; Why = 'fixture' }, @{ Text = 'Keep local / Discard menu'; File = 'README'; Why = 'fixture' }) }
        $before = & $runAnchors $gone '2.1.0'
        $after = & $runAnchors $gone '3.0.0'
        $null = Test-Check 'M' (@($before['Findings']).Count -eq 1 -and $before['Pending'] -eq 1 -and $before['Findings'][0]['Path'] -ceq 'agents/lead/README.md' -and
            @($after['Findings']).Count -eq 2 -and @($after['Findings'] | Where-Object { $_['Rule'] -ceq 'ANCHOR-GONE' -and $_['Path'] -ceq 'agents/reader/SOUL.md' -and $_['Line'] -eq 2 }).Count -eq 1) 'a Gone string fails ANCHOR-GONE at its line, and one with a later Since stays pending'
        $held = @{ Gone = @(@{ Text = 'old words'; File = 'SOUL'; Since = '3.0.0'; Pending = 'M5'; Why = 'fixture' }) }
        $heldDaily = & $runAnchors $held '3.0.0'
        $heldRelease = & $runAnchors $held '3.0.0' -Release
        $heldBad = & $runAnchors @{ Gone = @(@{ Text = 'old words'; File = 'SOUL'; Pending = 'soon'; Why = 'fixture' }) } '3.0.0'
        $null = Test-Check 'M' (@($heldDaily['Findings']).Count -eq 0 -and $heldDaily['Pending'] -eq 1 -and
            @($heldRelease['Findings']).Count -eq 1 -and $heldRelease['Findings'][0]['Rule'] -ceq 'ANCHOR-GONE' -and $heldRelease['Findings'][0]['Path'] -ceq 'anchors.psd1' -and
            @($heldBad['Errors']).Count -eq 1) 'a Gone string Pending a milestone stays pending, fails under -Release, and a Pending that is no milestone is a data error'
        $bad = & $runAnchors @{ Anchors = @(@{ Text = 'x'; In = @('nobody') }, @{ Text = 'y'; In = 'all'; File = 'TOOLS' }, @{ Text = 'z'; In = 'all' }); Removed = @(@{ Text = 'z'; Why = 'fixture' }) }
        $null = Test-Check 'M' (@($bad['Errors']).Count -eq 3) "an unknown agent id, a bad File and an anchor also under Removed are data errors ($(@($bad['Errors']).Count) error(s))"
    } catch {
        Add-Fail 'M' "the anchor cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }

    # ---- M: lost-lines report (smoke) ---------------------------------------------------------------------
    $compareScript = Join-Path $RepoRoot 'tests/agents/Compare-AgentSouls.ps1'
    $gitTool = Get-Command 'git' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $gitTool -or -not (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))) {
        Add-Note 'M' 'Compare-AgentSouls.ps1 smoke skipped: no git repository'
    } else {
        $compare = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $compareScript, '-RepoRoot', $RepoRoot, '-Base', 'HEAD', '-Summary')
        $badBase = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $compareScript, '-RepoRoot', $RepoRoot, '-Base', 'no-such-ref-for-the-test', '-Summary')
        $null = Test-Check 'M' ($compare.Code -eq 0 -and $compare.Text.Contains('lost line(s) in', $ord) -and $badBase.Code -eq 1) "Compare-AgentSouls.ps1 reports against HEAD (exit $($compare.Code)) and fails on an unknown base (exit $($badBase.Code))"
    }

    # ---- N: document counts -------------------------------------------------------------------------------
    Write-Host 'Running the document count cases ...'
    try {
        $docCase = Join-Path $tempRoot 'case-doc-count'
        New-RepoCopy $docCase
        $docsDir = Join-Path $docCase 'docs'
        New-Item -ItemType Directory -Path $docsDir -Force | Out-Null
        $docUnion = Get-AgentRosterUnion -RepoRoot $docCase
        $allCount = @($docUnion['Ids']).Count
        $planted = @(
            "The family ships $allCount agent packages, and Sixteen development agents sit in the table.",
            'Lead Developer has fifteen companions and runs at most 10 agents in 5 calls.',
            'Install all twenty-one development agents first.',
            'There are 99 Sophon agents in the store.',
            'In 2.0.0 the family had nine agents and 12 packages.',
            'Old text: thirteen agents shipped in the first release.'
        ) -join "`n"
        Write-Utf8 (Join-Path $docsDir 'AGENTS.md') ($planted + "`n")
        $countsFile = Join-Path $docCase 'build/agent-src/catalog/doc-counts.psd1'
        $countsText = [IO.File]::ReadAllText($countsFile)
        Write-Utf8 $countsFile ($countsText.Replace('History = @()', "History = @(@{ Phrase = 'thirteen agents shipped in the first release'; Why = 'fixture: a historical count' })"))
        $docRun = Test-AgentDocCounts -RepoRoot $docCase -Union $docUnion
        $flagged = @($docRun['Findings'] | ForEach-Object { "$($_['Line'])" }) -join ','
        $null = Test-Check 'N' ([string]::Equals($flagged, '3,4,5', $ord)) "DOC-COUNT flags 'twenty-one development agents', '99 Sophon agents' and '12 packages' only; derived counts, allowed caps, numbers under 10 and a History phrase pass (flagged lines: $flagged)"
        $docArgs = @('-NoProfile', '-NonInteractive', '-File', (Join-Path $docCase 'build/Test-AgentSources.ps1'), '-RepoRoot', $docCase)
        $docStrict = Invoke-Native $pwsh ($docArgs + '-Release')
        $null = Test-Check 'N' ($docStrict.Code -ne 0 -and $docStrict.Text.Contains('ERROR DOC-COUNT docs/AGENTS.md:3:', $ord) -and -not $docStrict.Text.Contains('DOC-COUNT docs/AGENTS.md:1:', $ord)) "under -Release a stale count fails DOC-COUNT at its line (exit $($docStrict.Code))"
        $docDaily = Invoke-Native $pwsh $docArgs
        $null = Test-Check 'N' ($docDaily.Code -eq 0 -and $docDaily.Text.Contains('WARN DOC-COUNT docs/AGENTS.md:3:', $ord)) "without -Release the same count is a warning and the run passes (exit $($docDaily.Code))"
    } catch {
        Add-Fail 'N' "the document count cases failed to run: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    }
    if ($SourceOnly) {
        $skipped['J'] = $true
        $skipped['K'] = $true
    } else {
        # ---- J: Sophon CLI validation ---------------------------------------------------------------------
        Write-Host 'Running sophon dev validate per agent ...'
        $sophon = Get-Command 'sophon' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $sophon) {
            Add-Fail 'J' "'sophon' is not on PATH (use -SourceOnly to skip the CLI sections)"
        } else {
            $version = Invoke-Native $sophon.Source @('--version')
            $versionLine = [string](@($version.Lines | Where-Object { "$_".Trim() }) | Select-Object -First 1)
            foreach ($f in $families) {
                $sophonPattern = [string](Get-Field $f['Data'] 'SophonCli')
                if (-not $sophonPattern) { $sophonPattern = '^2\.2\.\d+' }
                $null = Test-Check 'J' ($version.Code -eq 0 -and $versionLine.Trim() -match $sophonPattern) "sophon --version '$($versionLine.Trim())' matches $sophonPattern (family $($f['Id']))"
            }
            foreach ($id in $roster) {
                $dir = Join-Path $RepoRoot "agents/$id"
                $result = Invoke-NativeJson $sophon.Source @('dev', 'validate', $dir, '--json')
                $json = $result.Json
                $problems = [System.Collections.Generic.List[string]]::new()
                if ($result.Code -ne 0) { $problems.Add("exit $($result.Code)") }
                if ($null -eq $json) { $problems.Add("not JSON: $($result.Text) $($result.Stderr)".Trim()) }
                else {
                    if ((Get-Field $json 'ok') -ne $true) { $problems.Add('ok is not true') }
                    if (-not [string]::Equals([string](Get-Field $json 'projectType'), 'agent', $ord)) { $problems.Add("projectType '$(Get-Field $json 'projectType')'") }
                    foreach ($issue in @(Get-Field $json 'errors' | Where-Object { $null -ne $_ })) { $problems.Add("error: $(Format-CliIssue $issue)") }
                    foreach ($issue in @(Get-Field $json 'warnings' | Where-Object { $null -ne $_ })) { $problems.Add("warning: $(Format-CliIssue $issue)") }
                }
                if ($problems.Count -eq 0) { Add-Pass 'J' "sophon dev validate agents/${id}: ok, projectType agent, errors [], warnings []" }
                else { Add-Fail 'J' "sophon dev validate agents/${id}: $($problems -join '; ')" }
            }
        }

        # ---- K: reproducible build ------------------------------------------------------------------------
        Write-Host 'Building the packages into a temporary folder (this takes a while) ...'
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $out = Join-Path $tempRoot 'packages'
        New-Item -ItemType Directory -Path $out -Force | Out-Null
        $decoy = Join-Path $out 'old-1.0.0.sophon-agent'
        Write-Utf8 $decoy "decoy`n"
        $index = Join-Path $out 'SHA256SUMS'
        # Expected names come from each manifest: minor and patch versions move per agent.
        $packageNames = @{}
        foreach ($id in $roster) {
            $pkgVersion = $familyVersion
            try {
                $pkgManifest = Get-Content -LiteralPath (Join-Path $RepoRoot "agents/$id/manifest.json") -Raw -Encoding utf8 | ConvertFrom-Json -ErrorAction Stop
                if ($pkgManifest.PSObject.Properties.Name -ccontains 'version') { $pkgVersion = [string]$pkgManifest.version }
            } catch { Add-Fail 'K' "agents/$id/manifest.json could not be read for its version: $($_.Exception.Message)" }
            $packageNames[$id] = "$id-$pkgVersion.sophon-agent"
        }
        $expectedNames = [string[]]@($roster | ForEach-Object { $packageNames[$_] })
        [Array]::Sort($expectedNames, $ordinal)
        $firstIndex = $null
        $firstHashes = @{}

        $build = Invoke-Builder $RepoRoot @('-OutputDir', $out)
        if (Test-Check 'K' ($build.Code -eq 0) "full build exits 0$(if ($build.Code -ne 0) { " (got $($build.Code): $(Get-Tail $build.Lines))" })") {
            $null = Test-Check 'K' (-not (Test-Path -LiteralPath $decoy)) 'the decoy old-1.0.0.sophon-agent was removed'
            $present = [string[]]@(Get-ChildItem -LiteralPath $out -Force | ForEach-Object { $_.Name })
            [Array]::Sort($present, $ordinal)
            $wanted = [string[]](@($expectedNames) + 'SHA256SUMS')
            [Array]::Sort($wanted, $ordinal)
            $null = Test-Check 'K' ([string]::Equals(($present -join '|'), ($wanted -join '|'), $ord)) "output holds exactly $($expectedNames.Count) <id>-<version>.sophon-agent files and SHA256SUMS (found: $($present -join ', '))"

            if (Test-Path -LiteralPath $index -PathType Leaf) {
                $firstIndex = [IO.File]::ReadAllBytes($index)
                $indexText = $null
                try { $indexText = $utf8Strict.GetString($firstIndex) } catch { Add-Fail 'K' 'SHA256SUMS is not valid UTF-8' }
                if ($null -ne $indexText) {
                    $bom = $firstIndex.Length -ge 3 -and $firstIndex[0] -eq 0xEF -and $firstIndex[1] -eq 0xBB -and $firstIndex[2] -eq 0xBF
                    $null = Test-Check 'K' (-not $bom -and -not $indexText.Contains("`r") -and $indexText.EndsWith("`n", $ord) -and -not $indexText.EndsWith("`n`n", $ord)) 'SHA256SUMS is UTF-8 without BOM, LF only, one trailing LF'
                    $indexLines = @($indexText.TrimEnd("`n").Split("`n"))
                    $null = Test-Check 'K' ($indexLines.Count -eq $roster.Count) "SHA256SUMS has $($roster.Count) lines (found $($indexLines.Count))"
                    $names = [System.Collections.Generic.List[string]]::new()
                    $hashOk = $true
                    foreach ($line in $indexLines) {
                        $match = [regex]::Match($line, '^([0-9a-f]{64})  ([^\s/\\]+)$')
                        if (-not $match.Success) { Add-Fail 'K' "SHA256SUMS line is not '<sha256>  <file>': $line"; $hashOk = $false; continue }
                        $name = $match.Groups[2].Value
                        $names.Add($name)
                        $file = Join-Path $out $name
                        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { Add-Fail 'K' "SHA256SUMS names a missing file: $name"; $hashOk = $false; continue }
                        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
                        $firstHashes[$name] = $actual
                        if (-not [string]::Equals($actual, $match.Groups[1].Value, $ord)) { Add-Fail 'K' "SHA256SUMS hash for $name differs from the recomputed $actual"; $hashOk = $false }
                    }
                    if ($hashOk) { Add-Pass 'K' 'every SHA256SUMS hash matches the recomputed SHA-256' }
                    $null = Test-Check 'K' ([string]::Equals(($names -join '|'), ($expectedNames -join '|'), $ord)) 'SHA256SUMS lists the packages in ordinal file-name order'
                }
            } else {
                Add-Fail 'K' 'the full build wrote no SHA256SUMS'
            }

            $zipOk = 0
            $stamps = [System.Collections.Generic.HashSet[string]]::new($ordinal)
            foreach ($id in $roster) {
                $file = Join-Path $out $packageNames[$id]
                if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { Add-Fail 'K' "$($packageNames[$id]) was not built"; continue }
                $sourceDir = Join-Path $RepoRoot "agents/$id"
                $sourceNames = [string[]]@(Get-ChildItem -LiteralPath $sourceDir -File -Force | ForEach-Object { $_.Name } | Where-Object { $_ -cne 'manifest.json' })
                [Array]::Sort($sourceNames, $ordinal)
                $wantEntries = @('manifest.json') + $sourceNames
                $problems = [System.Collections.Generic.List[string]]::new()
                $zip = [IO.Compression.ZipFile]::OpenRead($file)
                try {
                    $entries = @($zip.Entries)
                    $entryNames = @($entries | ForEach-Object { $_.FullName })
                    if (-not [string]::Equals(($entryNames -join '|'), ($wantEntries -join '|'), $ord)) {
                        $problems.Add("entries [$($entryNames -join ', ')] are not manifest.json then the source files in ordinal order [$($wantEntries -join ', ')]")
                    }
                    foreach ($entry in $entries) {
                        [void]$stamps.Add($entry.LastWriteTime.DateTime.ToString('yyyy-MM-dd HH:mm:ss', [Globalization.CultureInfo]::InvariantCulture))
                        $sourcePath = Join-Path $sourceDir $entry.FullName
                        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { continue }
                        $memory = [IO.MemoryStream]::new()
                        $stream = $entry.Open()
                        try { $stream.CopyTo($memory) } finally { $stream.Dispose() }
                        if (-not (Test-BytesEqual $memory.ToArray() ([IO.File]::ReadAllBytes($sourcePath)))) { $problems.Add("$($entry.FullName) differs from agents/$id/$($entry.FullName)") }
                        $memory.Dispose()
                    }
                } finally { $zip.Dispose() }
                if ($problems.Count -eq 0) { $zipOk++ } else { Add-Fail 'K' "$($packageNames[$id]): $($problems -join '; ')" }
            }
            if ($roster.Count -gt 0 -and $zipOk -eq $roster.Count) { Add-Pass 'K' "zip entries of all $zipOk packages: manifest.json first, then ordinal; entry set and bytes equal the sources" }
            $stampList = @($stamps)
            $null = Test-Check 'K' ($stampList.Count -eq 1 -and [string]::Equals([string]$stampList[0], '1980-01-01 00:00:00', $ord)) "every zip entry has the fixed timestamp 1980-01-01 00:00:00 (found: $($stampList -join ', '))"

            # Repeat build: identical SHA256SUMS and package bytes.
            $repeat = Invoke-Builder $RepoRoot @('-OutputDir', $out)
            if (Test-Check 'K' ($repeat.Code -eq 0) "repeat build exits 0$(if ($repeat.Code -ne 0) { " (got $($repeat.Code): $(Get-Tail $repeat.Lines))" })") {
                $same = (Test-Path -LiteralPath $index -PathType Leaf) -and (Test-BytesEqual $firstIndex ([IO.File]::ReadAllBytes($index)))
                foreach ($name in $firstHashes.Keys) {
                    $file = Join-Path $out $name
                    if (-not (Test-Path -LiteralPath $file -PathType Leaf) -or -not [string]::Equals((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant(), $firstHashes[$name], $ord)) { $same = $false }
                }
                $null = Test-Check 'K' $same 'a repeat build gives a byte-identical SHA256SUMS and identical packages'
            }

            # Subset build: only the selected package is replaced and SHA256SUMS says so.
            $pick = $roster[0]
            $subsetRun = Invoke-Builder $RepoRoot @('-OutputDir', $out, '-Agents', $pick)
            $subsetIndex = if (Test-Path -LiteralPath $index -PathType Leaf) { [IO.File]::ReadAllText($index) } else { '' }
            $others = @($expectedNames | Where-Object { -not [string]::Equals($_, $packageNames[$pick], $ord) } | Where-Object { Test-Path -LiteralPath (Join-Path $out $_) -PathType Leaf })
            $null = Test-Check 'K' ($subsetRun.Code -eq 0 -and $subsetRun.Text.Contains("SHA256SUMS covers only: $pick", $ord) -and
                @($subsetIndex.TrimEnd("`n").Split("`n")).Count -eq 1 -and $subsetIndex.Contains("  $($packageNames[$pick])", $ord) -and
                $others.Count -eq ($expectedNames.Count - 1)) "subset build -Agents $pick rewrites only its package, keeps the others and prints 'SHA256SUMS covers only: $pick'"
        }

        # Failure cases.
        Write-Host 'Running the builder failure cases ...'
        $failOut = Join-Path $tempRoot 'failure-out'
        $unknown = Invoke-Builder $RepoRoot @('-OutputDir', $out, '-Agents', 'not-a-real-agent')
        $null = Test-Check 'K' ($unknown.Code -ne 0 -and $unknown.Text.Contains("Unknown agent selection: 'not-a-real-agent'", $ord) -and
            -not $unknown.Text.Contains('Sophon CLI:', $ord) -and -not (Test-Path -LiteralPath $index)) 'an unknown agent id fails before any CLI call and leaves no SHA256SUMS behind'

        # The cases run on a temporary copy whose SOULs are freshly composed, so each case fails only for the
        # defect it plants, whatever state the working tree is in.
        $base = Join-Path $tempRoot 'repo-base'
        New-RepoCopy $base
        $composeBase = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', (Join-Path $base 'build/Compose-AgentSouls.ps1'), '-RepoRoot', $base)
        if ($composeBase.Code -ne 0) {
            Add-Note 'K' "composing the temporary copy for the failure cases exited $($composeBase.Code): $(Get-Tail $composeBase.Lines 2)"
        }
        $leadId = if ($null -ne $family -and $family.Contains('Lead')) { [string]$family['Lead'] } else { 'lead-developer' }
        $sampleId = if ($roster.Count -gt 0) { $roster[0] } else { 'code-reviewer' }

        $caseRoot = Join-Path $tempRoot 'case-roster'
        Copy-Item -LiteralPath $base -Destination $caseRoot -Recurse
        New-Item -ItemType Directory -Path (Join-Path $caseRoot 'agents/zz-not-in-roster') -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $caseRoot "agents/$sampleId/manifest.json") -Destination (Join-Path $caseRoot 'agents/zz-not-in-roster')
        $result = Invoke-Builder $caseRoot @('-ValidateOnly', '-OutputDir', $failOut)
        $null = Test-Check 'K' ($result.Code -ne 0 -and $result.Text.Contains('agents/ folders must equal the roster', $ord) -and -not $result.Text.Contains('Sophon CLI:', $ord)) 'an agents/ folder outside the roster fails before any CLI call'

        $caseRoot = Join-Path $tempRoot 'case-name'
        Copy-Item -LiteralPath $base -Destination $caseRoot -Recurse
        $manifestPath = Join-Path $caseRoot "agents/$sampleId/manifest.json"
        $manifestText = [IO.File]::ReadAllText($manifestPath)
        $renamed = $manifestText.Replace("`"name`": `"$sampleId`"", "`"name`": `"$sampleId-renamed`"")
        if ([string]::Equals($renamed, $manifestText, $ord)) {
            Add-Fail 'K' "name-mismatch case: agents/$sampleId/manifest.json has no '`"name`": `"$sampleId`"' to change"
        } else {
            Write-Utf8 $manifestPath $renamed
            $result = Invoke-Builder $caseRoot @('-ValidateOnly', '-OutputDir', $failOut)
            $null = Test-Check 'K' ($result.Code -ne 0 -and $result.Text.Contains('does not exactly match its manifest name', $ord) -and -not $result.Text.Contains('Sophon CLI:', $ord)) 'a manifest name that differs from its folder fails before any CLI call'
        }

        $caseRoot = Join-Path $tempRoot 'case-drift'
        Copy-Item -LiteralPath $base -Destination $caseRoot -Recurse
        $soulPath = Join-Path $caseRoot "agents/$leadId/SOUL.md"
        if (Test-Path -LiteralPath $soulPath -PathType Leaf) {
            Write-Utf8 $soulPath ([IO.File]::ReadAllText($soulPath) + "A line the composer never wrote.`n")
            $result = Invoke-Builder $caseRoot @('-ValidateOnly', '-OutputDir', $failOut)
            $null = Test-Check 'K' ($result.Code -ne 0 -and $result.Text.Contains('DRIFT', $ord) -and $result.Text.Contains('SOUL or README drift', $ord) -and
                -not $result.Text.Contains('sophon dev validate', $ord)) 'a hand-edited SOUL.md fails with DRIFT before sophon dev validate runs'
        } else {
            Add-Fail 'K' "drift case: agents/$leadId/SOUL.md does not exist"
        }

        $caseRoot = Join-Path $tempRoot 'case-lint'
        Copy-Item -LiteralPath $base -Destination $caseRoot -Recurse
        $readmePath = Join-Path $caseRoot "agents/$sampleId/README.md"
        Write-Utf8 $readmePath ([IO.File]::ReadAllText($readmePath) + "`nRead the page with web.fetch.`n")
        # A generated README takes the same line in its source, so the case fails on the lint and not on drift.
        $readmeSource = Join-Path $caseRoot "build/agent-src/readmes/$sampleId.md"
        if (Test-Path -LiteralPath $readmeSource -PathType Leaf) { Write-Utf8 $readmeSource ([IO.File]::ReadAllText($readmeSource) + "`nRead the page with web.fetch.`n") }
        $result = Invoke-Builder $caseRoot @('-ValidateOnly', '-OutputDir', $failOut)
        $null = Test-Check 'K' ($result.Code -ne 0 -and $result.Text.Contains('LINT-DENIED', $ord) -and -not $result.Text.Contains('sophon dev validate', $ord)) 'a denied tool name in a README fails with LINT-DENIED before sophon dev validate runs'
        $null = Test-Check 'K' (-not (Test-Path -LiteralPath $failOut)) 'failed -ValidateOnly runs write nothing'
    }
} catch {
    $unexpected = $_
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

# ---- Report ------------------------------------------------------------------------------------------------
Write-Host ''
$failedSections = [System.Collections.Generic.List[string]]::new()
foreach ($key in $sectionTitles.Keys) {
    $list = $items[$key]
    $fails = @($list | Where-Object { $_.Ok -eq $false }).Count
    $passes = @($list | Where-Object { $_.Ok -eq $true }).Count
    if ($skipped.ContainsKey($key)) { $status = 'SKIP'; $color = 'Yellow' }
    elseif ($fails -gt 0 -or $passes -eq 0) { $status = 'FAIL'; $color = 'Red'; $failedSections.Add($key) }
    else { $status = 'PASS'; $color = 'Green' }
    Write-Host ("== {0}. {1}: " -f $key, $sectionTitles[$key]) -NoNewline
    Write-Host $status -ForegroundColor $color
    if ($status -eq 'SKIP') { Write-Host '   not run (-SourceOnly)'; continue }
    if ($passes -eq 0 -and $fails -eq 0) { Write-Host '   FAIL no check ran for this section' -ForegroundColor Red }
    foreach ($item in $list) {
        if ($item.Ok -eq $true) { Write-Host "   ok   $($item.Text)" }
        elseif ($item.Ok -eq $false) { Write-Host "   FAIL $($item.Text)" -ForegroundColor Red }
        else { Write-Host "        $($item.Text)" }
    }
}

if ($null -ne $unexpected) {
    $where = if ($unexpected.InvocationInfo) { " (line $($unexpected.InvocationInfo.ScriptLineNumber))" } else { '' }
    Write-Host "FAIL internal error$($where): $($unexpected.Exception.Message)" -ForegroundColor Red
    $failedSections.Add('internal')
}
Write-Host ''
if ($SourceOnly) { Write-Host 'CLI CHECKS NOT RUN (-SourceOnly)' -ForegroundColor Red }
if ($failedSections.Count -gt 0) {
    Write-Host "Test-AgentPackages: FAIL ($($failedSections -join ', '))" -ForegroundColor Red
    exit 1
}
Write-Host "Test-AgentPackages: PASS ($(if ($SourceOnly) { 'A-I, L, M and N; J and K skipped' } else { 'A-N' }))" -ForegroundColor Green
exit 0
