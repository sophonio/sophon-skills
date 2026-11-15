#Requires -Version 7.0

[CmdletBinding()]
param([string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')))

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$builder = Join-Path $RepoRoot 'build/Build-AgentPackages.ps1'
$testRoot = Join-Path $RepoRoot ('dist/agent-tests-' + [guid]::NewGuid().ToString('N'))
$output = Join-Path $testRoot 'packages'
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
Write-Host "Test files retained at $testRoot"

function Assert-True([bool]$condition, [string]$message) {
    if (-not $condition) { throw $message }
}

function Run-Builder([string[]]$arguments, [bool]$expectSuccess) {
    $text = @(& pwsh -NoProfile -File $builder @arguments 2>&1)
    $code = $LASTEXITCODE
    if (($code -eq 0) -ne $expectSuccess) {
        throw "Builder exit $code; output: $($text -join "`n")"
    }
    return ($text -join "`n")
}

try {
    $agentRoot = Join-Path $RepoRoot 'agents'
    Assert-True (Test-Path -LiteralPath $agentRoot -PathType Container) 'No agents source directory.'
    $agents = @(Get-ChildItem -LiteralPath $agentRoot -Directory | Where-Object {
        Test-Path -LiteralPath (Join-Path $_.FullName 'manifest.json') -PathType Leaf
    })
    $expectedIds = @('developer', 'lead-developer', 'qa-engineer', 'researcher', 'software-architect', 'ui-ux-designer')
    Assert-True ($agents.Count -eq 6) 'Expected exactly six development agents.'
    foreach ($id in $expectedIds) {
        Assert-True (@($agents | Where-Object { $_.Name -ceq $id }).Count -eq 1) "Missing agent: $id"
    }

    # The owner explicitly chose to preserve QA's accessibility line, a possible_secret false
    # positive. Pin the complete warning set before allowing the canonical build to proceed.
    foreach ($agent in $agents) {
        $validationText = & sophon dev validate $agent.FullName --json
        Assert-True ($LASTEXITCODE -eq 0) "Canonical validation failed: $($agent.Name)"
        $validation = $validationText | ConvertFrom-Json
        if ($agent.Name -ceq 'qa-engineer') {
            Assert-True (@($validation.warnings).Count -eq 1) 'QA warning set changed; review required.'
            Assert-True ($validation.warnings[0].message -ceq 'SOUL.md: line 30 looks like a credential; remove it before you share the package.') 'QA warning changed; review required.'
            $line = (Get-Content -LiteralPath (Join-Path $agent.FullName 'SOUL.md'))[29]
            Assert-True ($line -ceq '6. Accessibility: automated scan (e.g. axe) at each key state PLUS manual pass: keyboard-only, visible focus, focus not obscured, 200% and 400% zoom, target size, contrast, screen reader where available. Automation alone is not a pass.') 'Acknowledged accessibility line changed; review required.'
        } else {
            Assert-True (@($validation.warnings).Count -eq 0) "Unreviewed warnings: $($agent.Name)"
        }
    }
    $buildArgs = @('-RepoRoot', $RepoRoot, '-OutputDir', $output, '-AllowWarnings')
    $null = Run-Builder $buildArgs $true
    $index = Join-Path $output 'SHA256SUMS'
    Assert-True (Test-Path -LiteralPath $index -PathType Leaf) 'Missing SHA256SUMS.'
    $firstIndex = [IO.File]::ReadAllBytes($index)
    $allowed = @('manifest.json', 'SOUL.md', 'VOICE.md', 'HEARTBEAT.md', 'TOOLS.md', 'README.md', 'LICENSE')
    $required = @('manifest.json', 'LICENSE', 'README.md', 'SOUL.md')
    $leadCount = 0
    $hashes = @{}
    Add-Type -AssemblyName System.IO.Compression.FileSystem

    foreach ($agent in $agents) {
        $source = Get-Content -LiteralPath (Join-Path $agent.FullName 'manifest.json') -Raw | ConvertFrom-Json -AsHashtable
        Assert-True ($source.name -ceq $agent.Name) "Source ID differs from folder: $($agent.Name)."
        $file = Join-Path $output "$($agent.Name)-$($source.version).sophon-agent"
        Assert-True (Test-Path -LiteralPath $file -PathType Leaf) "Missing package: $file"
        $hashes[$agent.Name] = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
        $zip = [IO.Compression.ZipFile]::OpenRead($file)
        try {
            $entries = @($zip.Entries | ForEach-Object { $_.FullName })
            Assert-True (($entries -join ',') -ceq ($required -join ',')) "Incorrect canonical entry order or file set: $file"
            Assert-True ($entries.Count -eq @($entries | Select-Object -Unique).Count) "Duplicate entries in $file"
            foreach ($entry in $entries) {
                Assert-True ($allowed -ccontains $entry) "Unexpected package entry '$entry' in $file"
            }
            foreach ($entry in $required) {
                Assert-True ($entries -ccontains $entry) "Missing $entry in $file"
                $zipEntry = $zip.GetEntry($entry)
                Assert-True ($zipEntry.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss') -ceq '1980-01-01 00:00:00') "Non-deterministic timestamp: $entry"
                $memory = [IO.MemoryStream]::new()
                $stream = $zipEntry.Open()
                try {
                    $stream.CopyTo($memory)
                    $sourceBytes = [IO.File]::ReadAllBytes((Join-Path $agent.FullName $entry))
                    Assert-True ([Convert]::ToBase64String($memory.ToArray()) -ceq [Convert]::ToBase64String($sourceBytes)) "Packaged content differs from source: $entry in $file"
                } finally { $stream.Dispose(); $memory.Dispose() }
            }
            $licenseText = Get-Content -LiteralPath (Join-Path $agent.FullName 'LICENSE') -Raw
            Assert-True ($licenseText -match '^MIT License' -and $licenseText -match 'Copyright \(c\) 2026 Buildersoft LLC' -and $licenseText -match 'THE SOFTWARE IS PROVIDED') "Incomplete MIT license: $file"
            $reader = [IO.StreamReader]::new($zip.GetEntry('manifest.json').Open())
            try { $manifest = $reader.ReadToEnd() | ConvertFrom-Json -AsHashtable }
            finally { $reader.Dispose() }
        }
        finally { $zip.Dispose() }

        Assert-True ($manifest.name -ceq $agent.Name) "Package ID differs from folder: $($agent.Name)."
        Assert-True ($manifest.version -ceq $source.version) "Package version differs: $($agent.Name)."
        Assert-True ($manifest.type -ceq 'agent') "Incorrect type: $($agent.Name)."
        Assert-True ($manifest.schemaVersion -eq 1 -and $manifest.sophon.minVersion -ceq '2.2.0') "Incorrect package format or minimum version: $file"
        Assert-True ($manifest.author -ceq 'Buildersoft LLC' -and $manifest.license -ceq 'MIT') "Incorrect author or license: $file"
        Assert-True ($manifest.version -ceq '1.0.0' -and $manifest.category -ceq 'development') "Incorrect release metadata: $file"
        foreach ($key in @('runtime', 'entrypoint', 'tools', 'permissions', 'pluginInterface')) {
            Assert-True (-not $manifest.ContainsKey($key)) "Forbidden manifest key $key in $file"
        }
        Assert-True ($manifest.ContainsKey('defaults') -and $manifest.defaults.ContainsKey('subAgents')) "Missing delegation settings: $file"
        $defaults = $manifest.defaults
        foreach ($key in @('autoApprove', 'allowPlanning', 'modelProviderType', 'modelId', 'notifyOnAction')) {
            Assert-True (-not $defaults.ContainsKey($key)) "Forbidden defaults.$key in $file"
        }
        foreach ($pair in @(@('heartbeat', @('enabled', 'autoApprove', 'allowPlanning', 'modelProviderType', 'modelId', 'notifyOnAction')), @('subAgents', @('restrictToAllowList', 'allowedAgentIds')), @('modelRouting', @('pin', 'roles', 'allowFallback')))) {
            if ($defaults.ContainsKey($pair[0])) {
                foreach ($key in $pair[1]) {
                    Assert-True (-not $defaults[$pair[0]].ContainsKey($key)) "Forbidden defaults.$($pair[0]).$key in $file"
                }
            }
        }
        if ($agent.Name -ceq 'lead-developer') {
            $leadCount++
            Assert-True ($defaults.subAgents.enabled -ceq $true -and $defaults.subAgents.maxDepth -eq 2) "Lead delegation must be enabled at depth 2: $file"
        } else {
            Assert-True ($defaults.subAgents.enabled -ceq $false -and $defaults.subAgents.maxDepth -eq 3) "Specialist delegation must be disabled at depth 3: $file"
        }
        Write-Host "ok package $($agent.Name)"
    }
    Assert-True ($leadCount -eq 1) 'Expected exactly one delegation-enabled lead.'
    Assert-True (@(Get-ChildItem -LiteralPath $output -Filter '*.sophon-agent').Count -eq $agents.Count) 'Unexpected package count.'
    $null = Run-Builder $buildArgs $true
    Assert-True ([Convert]::ToBase64String($firstIndex) -ceq [Convert]::ToBase64String([IO.File]::ReadAllBytes($index))) 'Repeat build changed SHA256SUMS.'
    foreach ($agent in $agents) {
        $source = Get-Content -LiteralPath (Join-Path $agent.FullName 'manifest.json') -Raw | ConvertFrom-Json -AsHashtable
        $file = Join-Path $output "$($agent.Name)-$($source.version).sophon-agent"
        Assert-True ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ceq $hashes[$agent.Name]) "Repeat hash differs: $file"
    }
    Write-Host 'ok deterministic repeat build'

    $unknown = Run-Builder ($buildArgs + @('-Agents', 'not-a-real-agent')) $false
    Assert-True ($unknown -match 'Unknown agent selection') 'Unknown selection failed for the wrong reason.'
    Assert-True (-not (Test-Path -LiteralPath $index)) 'Failed build left a stale SHA256SUMS.'
    Write-Host 'ok unknown selection'

    $fixtureRoot = Join-Path $testRoot 'mismatch'
    $fixtureDir = Join-Path $fixtureRoot 'agents/mismatch-check'
    New-Item -ItemType Directory -Path $fixtureDir -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $fixtureDir 'manifest.json'), '{"name":"different-name"}')
    $mismatch = Run-Builder @('-RepoRoot', $fixtureRoot, '-ValidateOnly') $false
    Assert-True ($mismatch -match 'does not exactly match') 'Name mismatch failed for the wrong reason.'
    Write-Host 'ok manifest name mismatch'
    Write-Host 'All agent package tests passed.'
}
catch {
    Write-Error "FAIL: $_" -ErrorAction Continue
    exit 1
}
