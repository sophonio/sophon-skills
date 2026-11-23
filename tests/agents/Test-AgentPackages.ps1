#Requires -Version 7.0

<#
.SYNOPSIS
    End-to-end tests for the Buildersoft development family packages in agents/ (sections A-K).
.DESCRIPTION
    Sections (docs/plans/2026-11-15-agents-v2-design.md section 7.5):
      A-I  build/Test-AgentSources.ps1 on the real tree: layout, composer -Check, tool-name lint, preflight,
           budgets (with the headroom table), manifests, TOOLS.md, attribution, credits.
      B    plus every tests/agents/fixtures/compose/<case> through Compose-AgentSouls.ps1 -RepoRoot <case> -Check,
           compared with its EXPECT file, and two -OutDir builds of the real tree that must be byte-identical.
      C D F G plus the lint, scan, manifest and toolsmd fixture suites (Invoke-AgentLintFixtures in AgentLint.psm1).
      D    plus a temporary copy with one fragment given a second heading and one stripped of its heading,
           which Test-AgentSources must fail with FRAGMENT-HEADING.
      J    'sophon --version' matches the family SophonCli; 'sophon dev validate --json' per agent gives ok,
           projectType agent, no errors and no warnings.
      K    build/Build-AgentPackages.ps1 into a temporary folder: a decoy package is removed, one package per roster agent, a
           well-formed SHA256SUMS with recomputed hashes, zip entries equal to the sources, a byte-identical
           repeat build, a subset build, and failure cases (unknown agent, roster mismatch, name mismatch,
           SOUL drift, a lint error).

    -SourceOnly skips J and K (no Sophon CLI needed). Prints PASS, FAIL or SKIP per section and exits 1 on any
    failure. Temporary folders live under the system temp folder and are removed at the end.
.PARAMETER RepoRoot
    Repository root. Defaults to two folders above this script.
.PARAMETER SourceOnly
    Run sections A-I only.
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

$tempRoot = Join-Path ([IO.Path]::GetTempPath()) ('sophon-agent-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$unexpected = $null

try {
    # ---- Family --------------------------------------------------------------------------------------------
    $family = $null
    $roster = [string[]]@()
    try {
        $family = Import-PowerShellDataFile -LiteralPath (Join-Path $RepoRoot 'build/agent-src/family.psd1')
        $list = [System.Collections.Generic.List[string]]::new()
        foreach ($entry in @($family['Agents'])) { $list.Add([string]$entry['Id']) }
        $list.Sort($ordinal)
        $roster = $list.ToArray()
    } catch {
        Add-Fail 'A' "build/agent-src/family.psd1 does not load with Import-PowerShellDataFile: $($_.Exception.Message)"
    }
    $familyVersion = if ($null -ne $family -and $family.Contains('FamilyVersion')) { [string]$family['FamilyVersion'] } else { '2.0.0' }
    $sophonPattern = if ($null -ne $family -and $family.Contains('SophonCli')) { [string]$family['SophonCli'] } else { '^2\.2\.\d+' }
    Write-Host "Repo: $RepoRoot"
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
        foreach ($key in 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I') { $captured[$key] = [System.Collections.Generic.List[string]]::new(); $errorCounts[$key] = 0 }
        foreach ($line in $run.Lines) {
            $heading = [regex]::Match($line, '^== ([A-I])\. ')
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
            $result = Invoke-Native $pwsh @('-NoProfile', '-NonInteractive', '-File', $composer, '-RepoRoot', $case.FullName, '-Check')
            if ([string]::Equals($expect, 'OK', $ord)) {
                $good = $result.Code -eq 0
                $want = 'exit 0'
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
        }
    }

    # ---- C D F G: lint, scan, manifest and TOOLS.md fixture suites ------------------------------------------
    Write-Host 'Running the lint, scan, manifest and toolsmd fixture suites ...'
    $suiteSection = @{ lint = 'C'; scan = 'D'; manifest = 'F'; toolsmd = 'G' }
    try {
        Import-Module (Join-Path $RepoRoot 'build/AgentLint.psm1') -Force
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
            $null = Test-Check 'J' ($version.Code -eq 0 -and $versionLine.Trim() -match $sophonPattern) "sophon --version '$($versionLine.Trim())' matches $sophonPattern"
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
            $null = Test-Check 'K' ($result.Code -ne 0 -and $result.Text.Contains('DRIFT', $ord) -and $result.Text.Contains('SOUL drift', $ord) -and
                -not $result.Text.Contains('sophon dev validate', $ord)) 'a hand-edited SOUL.md fails with DRIFT before sophon dev validate runs'
        } else {
            Add-Fail 'K' "drift case: agents/$leadId/SOUL.md does not exist"
        }

        $caseRoot = Join-Path $tempRoot 'case-lint'
        Copy-Item -LiteralPath $base -Destination $caseRoot -Recurse
        $readmePath = Join-Path $caseRoot "agents/$sampleId/README.md"
        Write-Utf8 $readmePath ([IO.File]::ReadAllText($readmePath) + "`nRead the page with web.fetch.`n")
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
Write-Host "Test-AgentPackages: PASS ($(if ($SourceOnly) { 'A-I; J and K skipped' } else { 'A-K' }))" -ForegroundColor Green
exit 0
