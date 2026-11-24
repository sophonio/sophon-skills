#Requires -Version 7.0

<#
.SYNOPSIS
    The instruction tests of the agent families: the scenario lint, a prepare mode and a headless runner.
.DESCRIPTION
    docs/plans/2026-11-23-agents-v3-design.md, "Instruction tests". Three modes:

    -ValidateOnly  The scenario lint (Test-AgentEvalData in AgentEvals.psm1) over acceptance.psd1, pressure.psd1,
                   design.psd1, voice.psd1, the smoke ids of scenarios.md and the fixtures. Needs no Sophon CLI and
                   no Gateway; CI runs it. Pending rows print as NOTE lines; -Release turns a remaining Pending
                   into an error. Exit 1 on any error.
    -Prepare       For the selected scenarios: a fixture copy per scenario (git repository, setup applied) and,
                   for each pressure scenario, the control SOUL composed with -Omit <rule> and its package built
                   with 'sophon dev build'. Prints the install lines and the exact turns to paste. Installs
                   nothing and calls no Gateway.
    -Run           The headless runner. UNVERIFIED: it is written against the stream-json contract of Sophon CLI
                   2.2.2 (src/Sophon.CLI/Headless/StreamJsonSink.cs) and has not run against a Gateway; spike 5
                   of the design must confirm its five facts first (see README.md). It installs both arms into
                   the -DataDir Gateway data folder, pipes each turn to 'sophon exec ... --output-format
                   stream-json -', scores the first moves and writes transcripts and a summary to
                   dist/evals/<date>/. Guards: refuses under CI or GITHUB_ACTIONS, requires -DataDir and refuses
                   the default data folder, one repetition by default, stops before starting when the planned
                   runs exceed -MaxRuns.
.PARAMETER Scenario
    Scenario ids to select (wildcards allowed). Default: all, or all of -Tier.
.EXAMPLE
    pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly
.EXAMPLE
    pwsh -NoProfile -File tests/agents/evals/Invoke-AgentEvals.ps1 -Prepare -Scenario PRS-TF1 -OutDir $env:TEMP/evals
#>
[CmdletBinding(DefaultParameterSetName = 'Validate')]
param(
    [Parameter(ParameterSetName = 'Validate')][switch]$ValidateOnly,
    [Parameter(ParameterSetName = 'Prepare', Mandatory)][switch]$Prepare,
    [Parameter(ParameterSetName = 'Run', Mandatory)][switch]$Run,
    [Alias('StrictHeadroom')][switch]$Release,
    [string]$RepoRoot = (Join-Path $PSScriptRoot '../../..'),
    [string]$EvalRoot = $PSScriptRoot,
    [string[]]$Scenario = @(),
    [ValidateSet('acceptance', 'pressure', 'design', 'voice')][string[]]$Tier = @(),
    [Parameter(ParameterSetName = 'Prepare')][Parameter(ParameterSetName = 'Run')][string]$OutDir = '',
    [Parameter(ParameterSetName = 'Run', Mandatory)][string]$DataDir,
    [Parameter(ParameterSetName = 'Run')][ValidateRange(1, 10)][int]$Repeat = 1,
    [Parameter(ParameterSetName = 'Run')][ValidateRange(1, 1000)][int]$MaxRuns = 30,
    [Parameter(ParameterSetName = 'Run')][ValidateRange(30, 1800)][int]$TimeoutSeconds = 300,
    [Parameter(ParameterSetName = 'Run')][ValidateSet('both', 'treatment', 'control')][string]$Arm = 'both'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = [IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($RepoRoot))
$EvalRoot = [IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($EvalRoot))
# -Scenario 'ACC-05,PRS-TF2' arrives as one string under pwsh -File.
$Scenario = [string[]]@($Scenario | ForEach-Object { "$_".Split(',') } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
Import-Module (Join-Path $PSScriptRoot 'AgentEvals.psm1') -Force

# ---- Lint (every mode starts with it) -------------------------------------------------------------------------
$data = Import-AgentEvalData -EvalRoot $EvalRoot -RepoRoot $RepoRoot
$context = Get-AgentEvalContext -RepoRoot $RepoRoot -EvalRoot $EvalRoot
$result = Test-AgentEvalData -Data $data -Context $context -Release:$Release
$findings = @($result['Findings'])
foreach ($e in @($context['Errors'])) { $findings += @{ Level = 'error'; Rule = 'EVAL-FAMILY'; Path = 'build/agent-src'; Line = 0; Message = $e } }
$errors = @($findings | Where-Object { $_['Level'] -eq 'error' })
$notes = @($findings | Where-Object { $_['Level'] -ne 'error' })

$relEval = [IO.Path]::GetRelativePath($RepoRoot, $EvalRoot).Replace('\', '/')
Write-Host "Invoke-AgentEvals: scenario lint ($relEval)$(if ($Release) { ', -Release' })"
$countLine = @(foreach ($key in $result['Counts'].Keys) { "$key $($result['Counts'][$key])" }) -join ', '
$smokeIds = @($data['Smoke'] | Where-Object { $_ -and $_['Kind'] -eq 'heading' }).Count
Write-Host "  scenarios: $countLine; smoke sections: $smokeIds"
if ($result['Pending'].Count -gt 0) {
    Write-Host "  pending: $(@($result['Pending'].Keys | Sort-Object | ForEach-Object { "$_ $($result['Pending'][$_])" }) -join ', ')"
}
if ($result['Rules'].Count -gt 0) {
    Write-Host "  rules with pressure scenarios: $(@($result['Rules'].Keys | Sort-Object | ForEach-Object { "$_ ($($result['Rules'][$_].Count))" }) -join ', ')"
}
foreach ($f in $notes) { Write-Host "  $(Format-AgentEvalFinding -Finding $f)" }
foreach ($f in $errors) { Write-Host "  $(Format-AgentEvalFinding -Finding $f)" -ForegroundColor Red }
$summary = "$($errors.Count) error(s), $($notes.Count) note(s)"
if ($errors.Count -gt 0) {
    Write-Host "Invoke-AgentEvals: FAIL ($summary)" -ForegroundColor Red
    exit 1
}
if ($PSCmdlet.ParameterSetName -eq 'Validate') {
    Write-Host "Invoke-AgentEvals: PASS ($summary)" -ForegroundColor Green
    exit 0
}

# ---- Selection ------------------------------------------------------------------------------------------------
$selected = [System.Collections.Generic.List[hashtable]]::new()
foreach ($tierName in @('acceptance', 'pressure', 'design', 'voice')) {
    if ($Tier.Count -gt 0 -and $tierName -notin $Tier) { continue }
    $file = $data['Files'][$tierName]
    foreach ($row in @($file['Data']['Scenarios'])) {
        if ($Scenario.Count -gt 0 -and @($Scenario | Where-Object { $row['Id'] -like $_ }).Count -eq 0) { continue }
        $selected.Add($row)
    }
}
if ($selected.Count -eq 0) { Write-Host 'Invoke-AgentEvals: no scenario matches the selection' -ForegroundColor Red; exit 1 }
$byId = @{}
foreach ($tierName in @('acceptance', 'pressure', 'design', 'voice')) { foreach ($row in @($data['Files'][$tierName]['Data']['Scenarios'])) { $byId[$row['Id']] = $row } }

$runnable = [System.Collections.Generic.List[hashtable]]::new()
foreach ($row in $selected) {
    $why = ''
    if ($row.ContainsKey('Manual') -and $row['Manual']) { $why = 'manual: run it by hand' }
    elseif ($row.ContainsKey('SameRunAs')) { $why = "scored from the run of $($row['SameRunAs'])" }
    elseif (-not $context['Agents'].ContainsKey([string]$row['Agent'])) { $why = "agent $($row['Agent']) is not in a roster yet (Pending $($row['Pending']))" }
    elseif ($row.ContainsKey('Skill') -and $row['Skill'] -eq 'installed') { $why = 'needs the reference skill installed: run it by hand' }
    if ($why) { Write-Host "  skip $($row['Id']): $why"; continue }
    $runnable.Add($row)
}

function Get-EvalTurns([hashtable]$Row) {
    $turns = [System.Collections.Generic.List[string]]::new()
    if ($Row.ContainsKey('Brief')) { $turns.Add($context['Briefs'][[string]$Row['Brief']]) }
    foreach ($t in @($Row['Turns'] | Where-Object { $_ })) { $turns.Add([string]$t) }
    return $turns.ToArray()
}

function Get-EvalArms([hashtable]$Row) {
    if ($Row['Tier'] -ne 'pressure') { return @('treatment') }
    $method = $context['Methods'][$context['Agents'][[string]$Row['Agent']]['Family']]
    $registered = $null -ne $method -and @(@($method['Rules']) | Where-Object { $_['Id'] -ceq $Row['Rule'] }).Count -gt 0
    if (-not $registered) { Write-Host "  $($Row['Id']): rule $($Row['Rule']) is not registered yet, so there is no control arm (treatment only)"; return @('treatment') }
    return @('treatment', 'control')
}

function Get-EvalControlId([hashtable]$Row) {
    # One control agent per agent and rule: each control omits a different rule, so they never share an install.
    return "$($Row['Agent'])-ctl-$($Row['Rule'])"
}

function New-EvalControlPackage([hashtable]$Row, [string]$Into) {
    # Composes the agent without the rule and builds a package from a copy of agents/<id> with that SOUL.
    $agentId = [string]$Row['Agent']
    $composeOut = Join-Path $Into 'compose'
    $composer = Join-Path $RepoRoot 'build/Compose-AgentSouls.ps1'
    $out = @(& pwsh -NoProfile -NonInteractive -File $composer -RepoRoot $RepoRoot -Agents $agentId -Omit ([string]$Row['Rule']) -OutDir $composeOut 2>&1 | ForEach-Object { "$_" })
    if ($LASTEXITCODE -ne 0) { throw "compose -Omit $($Row['Rule']) failed for ${agentId}: $($out -join ' / ')" }
    $pkg = Join-Path $Into "pkg/$agentId"
    New-Item -ItemType Directory -Path (Split-Path $pkg) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot "agents/$agentId") -Destination $pkg -Recurse -Force
    Copy-Item -LiteralPath (Join-Path $composeOut "$agentId/SOUL.md") -Destination (Join-Path $pkg 'SOUL.md') -Force
    $buildOut = Join-Path $Into 'out'
    $out = @(& sophon dev build $pkg --output $buildOut 2>&1 | ForEach-Object { "$_" })
    if ($LASTEXITCODE -ne 0) { throw "sophon dev build failed for the control arm of ${agentId}: $($out -join ' / ')" }
    $file = @(Get-ChildItem -LiteralPath $buildOut -Filter '*.sophon-agent' | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
    if ($file.Count -eq 0) { throw "sophon dev build wrote no package for $agentId" }
    return @{ Package = $file[0].FullName; Removed = ($out -join "`n"); Soul = (Join-Path $composeOut "$agentId/SOUL.md") }
}

function Get-EvalPackage([string]$AgentId) {
    $file = @(Get-ChildItem -LiteralPath (Join-Path $RepoRoot 'dist/agents') -Filter "$AgentId-*.sophon-agent" -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($file.Count -eq 0) { throw "dist/agents has no $AgentId package: run build/Build-AgentPackages.ps1 first" }
    return $file[0].FullName
}

$stamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
if (-not $OutDir) { $OutDir = Join-Path $RepoRoot "dist/evals/$stamp" }
$OutDir = [IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

# ---- Prepare --------------------------------------------------------------------------------------------------
if ($PSCmdlet.ParameterSetName -eq 'Prepare') {
    foreach ($row in $runnable) {
        $dir = Join-Path $OutDir $row['Id']
        Write-Host ''
        Write-Host "== $($row['Id']) ($($row['Tier']), $($row['Agent']))"
        if ($row['Fixture'] -ne 'none') {
            $ws = New-AgentEvalWorkspace -Fixtures $context['Fixtures'] -Name $row['Fixture'] -Destination (Join-Path $dir 'workspace') -Setup ([string[]]@($row['Setup'] | Where-Object { $_ }))
            Write-Host "  workspace: $ws (git repository; setup: $(if (@($row['Setup']).Count) { $row['Setup'] -join ', ' } else { 'none' }))"
        } else { Write-Host '  workspace: none (start sophon in an empty folder)' }
        foreach ($arm in (Get-EvalArms $row)) {
            if ($arm -eq 'control') {
                $control = New-EvalControlPackage $row (Join-Path $dir 'control')
                Write-Host "  control package: $($control['Package'])"
                Write-Host "    install: sophon agents install --file `"$($control['Package'])`" --id $(Get-EvalControlId $row)"
            } else {
                Write-Host "  treatment: sophon agents install --file (Get-Item dist/agents/$($row['Agent'])-*.sophon-agent) --show-files"
            }
        }
        if ($row.ContainsKey('Mode') -and $row['Mode'] -eq 'plan') { Write-Host '  mode: turn plan mode on before the first message' }
        $n = 0
        foreach ($turn in (Get-EvalTurns $row)) {
            $n++
            $turnFile = Join-Path $dir "turn-$n.md"
            [IO.File]::WriteAllText($turnFile, $turn, [Text.UTF8Encoding]::new($false))
            Write-Host "  turn ${n} ($turnFile):"
            foreach ($line in $turn.Split("`n")) { Write-Host "    | $line" }
        }
        Write-Host "  record: the first tool call, what it chose, the excuse in its own words. Read: $($row['Read'])"
    }
    Write-Host ''
    Write-Host "Invoke-AgentEvals: prepared $($runnable.Count) scenario(s) in $OutDir (nothing installed)" -ForegroundColor Green
    exit 0
}

# ---- Run (unverified until spike 5) --------------------------------------------------------------------------
if ($env:CI -or $env:GITHUB_ACTIONS) { Write-Host 'Invoke-AgentEvals: -Run refuses to run under CI' -ForegroundColor Red; exit 1 }
$DataDir = [IO.Path]::GetFullPath($DataDir)
$defaultData = [IO.Path]::GetFullPath((Join-Path ([Environment]::GetFolderPath('UserProfile')) '.sophon'))
if ($DataDir.TrimEnd('\', '/') -ieq $defaultData.TrimEnd('\', '/') -or ($env:SOPHON_DATA_DIR -and [IO.Path]::GetFullPath($env:SOPHON_DATA_DIR) -ieq $defaultData)) {
    Write-Host "Invoke-AgentEvals: -DataDir must be a throwaway folder, not $defaultData" -ForegroundColor Red; exit 1
}
$sophon = Get-Command 'sophon' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if ($null -eq $sophon) { Write-Host "Invoke-AgentEvals: 'sophon' is not on PATH" -ForegroundColor Red; exit 1 }

$plan = [System.Collections.Generic.List[hashtable]]::new()
foreach ($row in $runnable) {
    foreach ($a in (Get-EvalArms $row)) {
        if ($Arm -ne 'both' -and $a -ne $Arm) { continue }
        for ($r = 1; $r -le $Repeat; $r++) { $plan.Add(@{ Row = $row; Arm = $a; Rep = $r }) }
    }
}
Write-Host "Invoke-AgentEvals: $($plan.Count) planned run(s) into $OutDir (data folder $DataDir)"
if ($plan.Count -gt $MaxRuns) { Write-Host "Invoke-AgentEvals: $($plan.Count) runs exceed -MaxRuns $MaxRuns; nothing started" -ForegroundColor Red; exit 1 }

$env:SOPHON_DATA_DIR = $DataDir
$cliVersion = (@(& $sophon.Source --version 2>&1) | Select-Object -First 1)
$installed = @{}
$rows = [System.Collections.Generic.List[object]]::new()
foreach ($item in $plan) {
    $row = $item['Row']; $arm = $item['Arm']
    $agentId = [string]$row['Agent']
    $runDir = Join-Path $OutDir "$($row['Id'])/$arm-$($item['Rep'])"
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
    $installId = if ($arm -eq 'control') { Get-EvalControlId $row } else { $agentId }
    if (-not $installed.ContainsKey($installId)) {
        if ($arm -eq 'control') {
            $control = New-EvalControlPackage $row (Join-Path $OutDir "$($row['Id'])/control-build")
            $pkg = $control['Package']; $soul = $control['Soul']
            & $sophon.Source agents install --file $pkg --id $installId | Out-Null
        } else {
            $pkg = Get-EvalPackage $agentId; $soul = Join-Path $RepoRoot "agents/$agentId/SOUL.md"
            & $sophon.Source agents install --file $pkg | Out-Null
        }
        if ($LASTEXITCODE -ne 0) { throw "sophon agents install failed for $installId" }
        $installed[$installId] = (Get-FileHash -LiteralPath $soul -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $workspace = Join-Path $runDir 'workspace'
    if ($row['Fixture'] -ne 'none') { New-AgentEvalWorkspace -Fixtures $context['Fixtures'] -Name $row['Fixture'] -Destination $workspace -Setup ([string[]]@($row['Setup'] | Where-Object { $_ })) | Out-Null }
    else { New-Item -ItemType Directory -Path $workspace -Force | Out-Null }
    $session = ''
    $lines = [System.Collections.Generic.List[string]]::new()
    $n = 0
    foreach ($turn in (Get-EvalTurns $row)) {
        $n++
        $cliArgs = @('exec', '--agent', $installId, '--workspace', $workspace, '--trust-workspace', '--output-format', 'stream-json', '--timeout', "$TimeoutSeconds")
        if ($row.ContainsKey('Mode') -and $row['Mode'] -eq 'plan') { $cliArgs += @('--permission-mode', 'plan') }
        if ($session) { $cliArgs += @('--session', $session) }
        $cliArgs += '-'
        $turnLines = @($turn | & $sophon.Source @cliArgs 2>$null | ForEach-Object { "$_" })
        [IO.File]::WriteAllLines((Join-Path $runDir "turn-$n.ndjson"), [string[]]$turnLines)
        foreach ($l in $turnLines) {
            if (-not $session -and $l -match '"type":"session\.started"') { try { $session = [string](($l | ConvertFrom-Json).sessionId) } catch { } }
        }
        $lines.Clear(); foreach ($l in $turnLines) { $lines.Add($l) }   # only the last turn is scored
    }
    $moves = Read-AgentEvalTranscript -Lines $lines.ToArray()
    $score = Get-AgentEvalScore -Scenario $row -Moves $moves -Markers ([string[]]@($result['Markers']))
    $cost = if ($null -ne $moves['Result'] -and $moves['Result']['usage'] -is [hashtable]) { $moves['Result']['usage']['costUsd'] } else { $null }
    $rows.Add([pscustomobject]@{
            Id = $row['Id']; Arm = $arm; Rep = $item['Rep']; Passed = $score['Passed']
            First = if (@($moves['Calls']).Count) { $moves['Calls'][0]['Tool'] } else { '(none)' }
            Missed = $score['Missed'] -join '; '; Tripped = $score['Tripped'] -join '; '
            Soul = $installed[$installId].Substring(0, 12); Cost = $cost; Dir = $runDir
        })
    Write-Host ("  {0,-8} {1,-9} #{2} {3}  first {4}" -f $row['Id'], $arm, $item['Rep'], $(if ($score['Passed']) { 'pass' } else { 'FAIL' }), $rows[-1].First)
}

# Summary: control against treatment per scenario, and the transcripts a person should read.
$summaryLines = [System.Collections.Generic.List[string]]::new()
$summaryLines.Add("# Eval run $stamp")
$summaryLines.Add('')
$summaryLines.Add("CLI: $cliVersion. Repetitions: $Repeat. Data folder: a throwaway Gateway.")
$summaryLines.Add('')
$summaryLines.Add('| Id | Arm | Passed | Runs | SOUL sha256 | First calls |')
$summaryLines.Add('|---|---|---|---|---|---|')
foreach ($group in @($rows | Group-Object Id, Arm)) {
    $first = $group.Group[0]
    $summaryLines.Add("| $($first.Id) | $($first.Arm) | $(@($group.Group | Where-Object Passed).Count) | $($group.Count) | $($first.Soul) | $(@($group.Group | ForEach-Object First) -join ', ') |")
}
$summaryLines.Add('')
$summaryLines.Add('Flagged for reading (a failed treatment or a passed control):')
foreach ($r in $rows) {
    if (($r.Arm -eq 'treatment' -and -not $r.Passed) -or ($r.Arm -eq 'control' -and $r.Passed)) { $summaryLines.Add("- $($r.Id) $($r.Arm) #$($r.Rep): $($r.Dir) (missed: $($r.Missed); tripped: $($r.Tripped))") }
}
[IO.File]::WriteAllLines((Join-Path $OutDir 'summary.md'), $summaryLines.ToArray())
Write-Host "Invoke-AgentEvals: $($rows.Count) run(s); summary at $(Join-Path $OutDir 'summary.md')" -ForegroundColor Green
exit 0
