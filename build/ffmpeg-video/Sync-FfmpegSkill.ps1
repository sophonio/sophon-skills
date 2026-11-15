#Requires -Version 7.0

<#
.SYNOPSIS
    Vendors a tagged release of kajisho5/ffmpeg-skill into skills/ffmpeg-video/vendor/ffmpeg-skill/,
    or checks that the vendored files still match it.
.DESCRIPTION
    Sync (default):
      1. Opens the upstream repository (-Source: a local clone, or a URL that is cloned into a temp
         folder), resolves -Tag to a commit and asserts it equals -ExpectedCommit, and that the
         tag's package.json version equals the tag.
      2. Expands build/ffmpeg-video/vendor-files.txt against `git ls-tree` at that commit. Every
         pattern must match a file. A matched shell, PowerShell, batch or native-binary file, a
         dotfile, a path under an excluded folder name, a symlink or a submodule fails the sync.
      3. Copies each file's exact bytes with `git cat-file blob <commit>:<path>` into a staging
         folder and checks each copy against its git blob id.
      4. Runs an AST import scan of the staged code (generate.py --scan-imports): a non-stdlib,
         non-local import outside a try block fails the sync.
      5. Swaps the vendor folder in one step, writes vendor.lock.json and regenerates the tool
         surface (generate.py --write-lock --summary), which prints the surface diff and fails on
         any unclassified path-like parameter or an upstream contract change that needs review.
      6. Prints the review checklist.
    -Check writes nothing in the repository: it re-derives every vendored file from the tag and
    fails when a file on disk differs, is missing or is extra, when vendor.lock.json does not
    describe the tag's files, when THIRD_PARTY_NOTICES.md does not name the tag and commit, or when
    generate.py --check reports drift. CI runs it on changes under skills/ffmpeg-video/vendor/.

    The upstream repository is only read (rev-parse, ls-tree, cat-file); it is never modified.
    -RunUpstreamTests runs the upstream contract tests in a throwaway clone (they need FFmpeg).
.PARAMETER Tag
    The upstream tag to vendor, e.g. v3.9.2. Tags only, never a branch.
.PARAMETER ExpectedCommit
    The full commit sha the tag must resolve to. Strongly recommended; without it the resolved
    commit is printed and a warning is raised.
.PARAMETER Source
    A local clone of the upstream repository, or a git URL. Defaults to -RepoUrl.
.PARAMETER RepoUrl
    The canonical upstream URL written into vendor.lock.json.
.PARAMETER RunUpstreamTests
    Also run `CI=true python -B tests/test_contract.py` in a temporary checkout of the tag; a
    failure fails the sync. Needs FFmpeg 6.1+ on PATH.
.PARAMETER Check
    Verify only; write nothing in the repository.
.PARAMETER Python
    The Python 3.10+ interpreter to run generate.py with. Defaults to python, python3, then py -3.
.EXAMPLE
    pwsh -NoProfile -File build/ffmpeg-video/Sync-FfmpegSkill.ps1 -Tag v3.9.2 -ExpectedCommit 3f8ba63cc8eb991c1730d57b0215e6127765399a -Check
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Tag,
    [string]$ExpectedCommit = '',
    [string]$Source = '',
    [string]$RepoUrl = 'https://github.com/kajisho5/ffmpeg-skill',
    [switch]$RunUpstreamTests,
    [switch]$Check,
    [string]$Python = '',
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$VendorName       = 'ffmpeg-skill'
$SkillDir         = Join-Path $RepoRoot 'skills/ffmpeg-video'
$VendorParent     = Join-Path $SkillDir 'vendor'
$VendorDir        = Join-Path $VendorParent $VendorName
$LockPath         = Join-Path $SkillDir 'vendor.lock.json'
$NoticesPath      = Join-Path $SkillDir 'THIRD_PARTY_NOTICES.md'
$AllowlistPath    = Join-Path $PSScriptRoot 'vendor-files.txt'
$GeneratePath     = Join-Path $PSScriptRoot 'generate.py'
$PreviewCapBytes  = 262144

# Mirrors build/catalog/marketplace-rules.psd1 Vendor.DeniedExtensions, plus compiled Python.
$DeniedExtensions = @('.sh', '.ps1', '.psm1', '.bat', '.cmd', '.exe', '.dll', '.so', '.dylib', '.pyc', '.pyo')
# Folder names `sophon dev install` (DevCommand.cs) or the package build drop; a vendored file
# under one would be missing from the installed skill and break the lock.
$ExcludedSegments = @('.git', 'node_modules', '__pycache__', 'bin', 'obj', '.vs', 'dist', '.venv', '.vscode',
    '.idea', '.next', '.sophon', '.env')
$ExcludedLeaves   = @('.DS_Store', 'Thumbs.db')

$script:Failures = [System.Collections.Generic.List[string]]::new()
$script:Warnings = [System.Collections.Generic.List[string]]::new()
$script:TempDirs = [System.Collections.Generic.List[string]]::new()

function Add-Failure([string]$Message) { $script:Failures.Add($Message); Write-Host "FAIL: $Message" -ForegroundColor Red }
function Add-Warning([string]$Message) { $script:Warnings.Add($Message); Write-Host "WARN: $Message" -ForegroundColor Yellow }

function New-TempDir([string]$Prefix) {
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ("$Prefix-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    $script:TempDirs.Add($path)
    return $path
}

function Invoke-Native {
    # Runs an executable with an exact argument list and returns stdout as bytes (no newline or
    # encoding translation). Throws with stderr on a non-zero exit.
    param(
        [Parameter(Mandatory)] [string]$FilePath,
        [Parameter(Mandatory)] [string[]]$Arguments,
        [string]$WorkingDirectory = '',
        [hashtable]$Environment = @{},
        [switch]$AllowFailure
    )
    $psi = [System.Diagnostics.ProcessStartInfo]::new($FilePath)
    foreach ($a in $Arguments) { $psi.ArgumentList.Add($a) }
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    if ($WorkingDirectory) { $psi.WorkingDirectory = $WorkingDirectory }
    foreach ($k in $Environment.Keys) { $psi.Environment[$k] = [string]$Environment[$k] }
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stderrTask = $proc.StandardError.ReadToEndAsync()
    $buffer = [System.IO.MemoryStream]::new()
    $proc.StandardOutput.BaseStream.CopyTo($buffer)
    $proc.WaitForExit()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($proc.ExitCode -ne 0 -and -not $AllowFailure) {
        throw "$FilePath $($Arguments -join ' ') failed (exit $($proc.ExitCode)): $($stderr.Trim())"
    }
    return [pscustomobject]@{ ExitCode = $proc.ExitCode; Stdout = $buffer.ToArray(); Stderr = $stderr }
}

function Invoke-Git([string]$GitDir, [string[]]$Arguments, [switch]$AllowFailure) {
    return Invoke-Native -FilePath 'git' -Arguments (@('-C', $GitDir) + $Arguments) -AllowFailure:$AllowFailure
}

function Get-Utf8([byte[]]$Bytes) { return [System.Text.UTF8Encoding]::new($false, $true).GetString($Bytes) }

function Get-Sha256Hex([byte[]]$Bytes) {
    return ([System.Security.Cryptography.SHA256]::HashData($Bytes) | ForEach-Object { $_.ToString('x2') }) -join ''
}

function Get-GitBlobId([byte[]]$Bytes) {
    $header = [System.Text.Encoding]::ASCII.GetBytes("blob $($Bytes.Length)`0")
    $all = [byte[]]::new($header.Length + $Bytes.Length)
    [System.Buffer]::BlockCopy($header, 0, $all, 0, $header.Length)
    [System.Buffer]::BlockCopy($Bytes, 0, $all, $header.Length, $Bytes.Length)
    return ([System.Security.Cryptography.SHA1]::HashData($all) | ForEach-Object { $_.ToString('x2') }) -join ''
}

function ConvertTo-GlobRegex([string]$Glob) {
    $sb = [System.Text.StringBuilder]::new('^')
    foreach ($ch in $Glob.ToCharArray()) {
        switch ($ch) {
            '*' { [void]$sb.Append('[^/]*') }
            '?' { [void]$sb.Append('[^/]') }
            default { [void]$sb.Append([regex]::Escape([string]$ch)) }
        }
    }
    [void]$sb.Append('$')
    return [regex]::new($sb.ToString(), [System.Text.RegularExpressions.RegexOptions]::CultureInvariant)
}

function Get-DenyReason([string]$Path, [string]$Mode, [string]$Type) {
    if ($Type -ne 'blob') { return "it is a $Type, not a file" }
    if ($Mode -eq '120000') { return 'it is a symlink' }
    if ($Mode -notin @('100644', '100755')) { return "it has git mode $Mode" }
    $segments = $Path.Split('/')
    foreach ($segment in $segments) {
        if ($segment.StartsWith('.')) { return 'it is a dotfile or under a dot folder' }
        if ($ExcludedSegments -contains $segment) { return "it is under the excluded folder name '$segment'" }
    }
    $leaf = $segments[-1]
    if ($ExcludedLeaves -contains $leaf) { return 'it is an excluded file name' }
    $ext = [System.IO.Path]::GetExtension($leaf).ToLowerInvariant()
    if ($DeniedExtensions -contains $ext) { return "its extension $ext is a script or binary" }
    return $null
}

function Resolve-Python {
    $candidates = @()
    if ($Python) { $candidates += , @($Python) }
    $candidates += , @('python')
    $candidates += , @('python3')
    $candidates += , @('py', '-3')
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        $prefix = @($candidate | Select-Object -Skip 1)
        $probe = Invoke-Native -FilePath $exe -Arguments ($prefix + @('-c', 'import sys; print(int(sys.version_info >= (3, 10)))')) -AllowFailure
        if ($probe.ExitCode -eq 0 -and (Get-Utf8 $probe.Stdout).Trim() -eq '1') {
            return [pscustomobject]@{ Exe = $exe; Prefix = $prefix }
        }
    }
    throw 'No Python 3.10+ interpreter found (tried -Python, python, python3, py -3).'
}

function Invoke-Generate([string[]]$Arguments) {
    # Streams generate.py's output to the console and returns its exit code.
    $all = @($script:Py.Prefix) + @('-I', '-B', '-X', 'utf8', $GeneratePath) + $Arguments
    & $script:Py.Exe @all 2>&1 | ForEach-Object { Write-Host $_ }
    return $LASTEXITCODE
}

try {
    $script:Py = Resolve-Python
    Write-Host "python: $($script:Py.Exe) $($script:Py.Prefix -join ' ')"

    # --- 1. open the upstream repository and resolve the tag ---------------------------------
    if (-not $Source) { $Source = $RepoUrl }
    $isLocal = Test-Path -LiteralPath $Source -PathType Container
    if ($isLocal) {
        $GitDir = (Resolve-Path -LiteralPath $Source).Path
        Write-Host "source: local clone $GitDir (read only)"
    } else {
        $GitDir = New-TempDir 'ffvideo-upstream'
        Write-Host "source: cloning $Source into $GitDir"
        Invoke-Native -FilePath 'git' -Arguments @('clone', '--quiet', '--no-checkout', $Source, $GitDir) | Out-Null
    }

    if ($Tag -notmatch '^v\d+\.\d+\.\d+$') { throw "-Tag '$Tag' is not a release tag of the form vX.Y.Z" }
    $tagRef = Invoke-Git $GitDir @('rev-parse', '--verify', '--quiet', "refs/tags/$Tag^{commit}") -AllowFailure
    if ($tagRef.ExitCode -ne 0) { throw "tag $Tag not found in $Source" }
    $Commit = (Get-Utf8 $tagRef.Stdout).Trim()
    if ($Commit -notmatch '^[0-9a-f]{40}$') { throw "tag $Tag resolved to an unexpected value '$Commit'" }
    if ($ExpectedCommit) {
        if ($Commit -ne $ExpectedCommit.ToLowerInvariant()) {
            throw "tag $Tag resolves to $Commit, not the expected $ExpectedCommit (a moved tag must be reviewed)"
        }
        Write-Host "tag: $Tag = $Commit (matches -ExpectedCommit)"
    } else {
        Add-Warning "no -ExpectedCommit given; $Tag resolved to $Commit"
    }

    $packageBytes = (Invoke-Git $GitDir @('cat-file', 'blob', "${Commit}:package.json")).Stdout
    $Version = [string]((Get-Utf8 $packageBytes) | ConvertFrom-Json).version
    if ($Version -ne $Tag.Substring(1)) { throw "package.json at $Tag says version $Version, not $($Tag.Substring(1))" }

    # --- 2. expand the allowlist -------------------------------------------------------------
    $treeText = Get-Utf8 (Invoke-Git $GitDir @('ls-tree', '-r', '-z', '--full-tree', $Commit)).Stdout
    $tree = [System.Collections.Generic.List[object]]::new()
    foreach ($record in $treeText.Split([char]0)) {
        if (-not $record) { continue }
        $tab = $record.IndexOf("`t")
        $meta = $record.Substring(0, $tab).Split(' ')
        $tree.Add([pscustomobject]@{ Mode = $meta[0]; Type = $meta[1]; Id = $meta[2]; Path = $record.Substring($tab + 1) })
    }

    $patterns = @(Get-Content -LiteralPath $AllowlistPath -Encoding utf8 |
        ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not $_.StartsWith('#') })
    if ($patterns.Count -eq 0) { throw "$AllowlistPath lists no patterns" }
    $selected = [System.Collections.Generic.SortedDictionary[string, object]]::new([System.StringComparer]::Ordinal)
    foreach ($pattern in $patterns) {
        if ($pattern.Contains('\') -or $pattern.StartsWith('/') -or $pattern.Contains('..')) {
            Add-Failure "vendor-files.txt pattern '$pattern' must be a relative forward-slash glob"
            continue
        }
        $regex = ConvertTo-GlobRegex $pattern
        $hits = @($tree | Where-Object { $regex.IsMatch($_.Path) })
        if ($hits.Count -eq 0) { Add-Failure "vendor-files.txt pattern '$pattern' matches nothing at $Tag"; continue }
        foreach ($hit in $hits) {
            $reason = Get-DenyReason $hit.Path $hit.Mode $hit.Type
            if ($reason) { Add-Failure "$($hit.Path) matches '$pattern' but is denied: $reason"; continue }
            $selected[$hit.Path] = $hit
        }
    }
    $lowerSeen = @{}
    foreach ($p in $selected.Keys) {
        $lower = $p.ToLowerInvariant()
        if ($lowerSeen.ContainsKey($lower)) { Add-Failure "$p and $($lowerSeen[$lower]) differ only by case" }
        $lowerSeen[$lower] = $p
    }
    if ($script:Failures.Count -gt 0) { throw 'the allowlist could not be expanded cleanly' }
    Write-Host "allowlist: $($selected.Count) files from $($patterns.Count) patterns"

    # --- 3. copy exact bytes into a staging folder -------------------------------------------
    $stageRoot = New-TempDir 'ffvideo-stage'
    $stageVendor = Join-Path $stageRoot $VendorName
    $expected = [System.Collections.Generic.List[object]]::new()
    $utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)
    foreach ($entry in $selected.Values) {
        $bytes = (Invoke-Git $GitDir @('cat-file', 'blob', "${Commit}:$($entry.Path)")).Stdout
        if ((Get-GitBlobId $bytes) -ne $entry.Id) { throw "$($entry.Path): copied bytes do not match git blob $($entry.Id)" }
        if ([Array]::IndexOf($bytes, [byte]0) -ge 0) { Add-Failure "$($entry.Path) contains a NUL byte (binary)" }
        try { [void]$utf8Strict.GetString($bytes) } catch { Add-Failure "$($entry.Path) is not valid UTF-8" }
        if ($bytes.Length -gt $PreviewCapBytes) {
            Add-Warning "$($entry.Path) is $($bytes.Length) bytes, over the marketplace's 256 KiB moderator preview"
        }
        $target = Join-Path $stageVendor $entry.Path
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        [System.IO.File]::WriteAllBytes($target, $bytes)
        $expected.Add([pscustomobject]@{
                Path   = "vendor/$VendorName/$($entry.Path)"
                Sha256 = Get-Sha256Hex $bytes
                Bytes  = $bytes.Length
            })
    }
    if ($script:Failures.Count -gt 0) { throw 'a vendored file failed the content checks' }

    # --- 4. AST import scan -------------------------------------------------------------------
    Write-Host 'import scan:'
    if ((Invoke-Generate @('--scan-imports', $stageVendor)) -ne 0) { throw 'the import scan found a non-stdlib import' }

    # --- optional: upstream tests -------------------------------------------------------------
    if ($RunUpstreamTests) {
        $testDir = New-TempDir 'ffvideo-tests'
        Invoke-Native -FilePath 'git' -Arguments @('clone', '--quiet', '--no-checkout', '--no-hardlinks', $GitDir, $testDir) | Out-Null
        Invoke-Git $testDir @('checkout', '--quiet', '--detach', $Commit) | Out-Null
        Write-Host "upstream tests: CI=true python -B tests/test_contract.py in $testDir"
        $all = @($script:Py.Prefix) + @('-B', 'tests/test_contract.py')
        $test = Invoke-Native -FilePath $script:Py.Exe -Arguments $all -WorkingDirectory $testDir `
            -Environment @{ CI = 'true'; PYTHONDONTWRITEBYTECODE = '1' } -AllowFailure
        $tail = ((Get-Utf8 $test.Stdout) + $test.Stderr).Trim().Split("`n") | Select-Object -Last 15
        $tail | ForEach-Object { Write-Host "  $_" }
        if ($test.ExitCode -ne 0) { throw "upstream tests failed (exit $($test.ExitCode))" }
        Write-Host 'upstream tests: passed'
    }

    $contractBytes = (Get-Item -LiteralPath (Join-Path $stageVendor 'scripts/_contract.py')).Length
    $limitsLine = (Select-String -LiteralPath (Join-Path $stageVendor 'scripts/_platforms.py') -Pattern '^UPLOAD_LIMITS_AS_OF\s*=' |
        Select-Object -First 1)
    $limitsAsOf = if ($limitsLine) { $limitsLine.Line.Trim() } else { '(not found)' }

    if ($Check) {
        # --- -Check: compare, write nothing ---------------------------------------------------
        if (-not (Test-Path -LiteralPath $VendorDir -PathType Container)) {
            Add-Failure "$VendorDir does not exist"
        } else {
            $reparse = @(Get-ChildItem -LiteralPath $VendorParent -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue)
            foreach ($r in $reparse) { Add-Failure "$($r.FullName) is a symlink or reparse point" }
            $skillFull = (Resolve-Path -LiteralPath $SkillDir).Path
            $onDisk = @{}
            foreach ($file in (Get-ChildItem -LiteralPath $VendorParent -Recurse -File -Force)) {
                $rel = $file.FullName.Substring($skillFull.Length).TrimStart('\', '/').Replace('\', '/')
                $onDisk[$rel] = $file.FullName
            }
            $expectedPaths = @{}
            foreach ($e in $expected) {
                $expectedPaths[$e.Path] = $true
                if (-not $onDisk.ContainsKey($e.Path)) { Add-Failure "$($e.Path) is missing"; continue }
                $diskHash = Get-Sha256Hex ([System.IO.File]::ReadAllBytes($onDisk[$e.Path]))
                if ($diskHash -ne $e.Sha256) { Add-Failure "$($e.Path) differs from $Tag" }
            }
            foreach ($rel in ($onDisk.Keys | Sort-Object)) {
                if (-not $expectedPaths.ContainsKey($rel)) { Add-Failure "$rel is not an upstream file at $Tag (extra)" }
            }
        }

        if (-not (Test-Path -LiteralPath $LockPath -PathType Leaf)) {
            Add-Failure 'vendor.lock.json is missing'
        } else {
            $lock = Get-Content -LiteralPath $LockPath -Raw -Encoding utf8 | ConvertFrom-Json
            if ($lock.schemaVersion -ne 1) { Add-Failure 'vendor.lock.json schemaVersion is not 1' }
            if ($lock.upstream.repo -cne $RepoUrl) { Add-Failure "vendor.lock.json upstream.repo is '$($lock.upstream.repo)', not $RepoUrl" }
            if ($lock.upstream.tag -cne $Tag) { Add-Failure "vendor.lock.json upstream.tag is '$($lock.upstream.tag)', not $Tag" }
            if ($lock.upstream.commit -cne $Commit) { Add-Failure "vendor.lock.json upstream.commit is '$($lock.upstream.commit)', not $Commit" }
            if ($lock.upstream.version -cne $Version) { Add-Failure "vendor.lock.json upstream.version is '$($lock.upstream.version)', not $Version" }
            $lockFiles = @($lock.files)
            if ($lockFiles.Count -ne $expected.Count) {
                Add-Failure "vendor.lock.json lists $($lockFiles.Count) files; $Tag has $($expected.Count)"
            } else {
                for ($i = 0; $i -lt $expected.Count; $i++) {
                    $want = $expected[$i]; $have = $lockFiles[$i]
                    if ($have.path -cne $want.Path -or $have.sha256 -cne $want.Sha256 -or [int64]$have.bytes -ne $want.Bytes) {
                        Add-Failure "vendor.lock.json files[$i] ($($have.path)) does not match $($want.Path) at $Tag"
                    }
                }
            }
        }

        if (-not (Test-Path -LiteralPath $NoticesPath -PathType Leaf)) {
            Add-Failure 'THIRD_PARTY_NOTICES.md is missing'
        } else {
            $notices = Get-Content -LiteralPath $NoticesPath -Raw -Encoding utf8
            foreach ($needle in @($Tag, $Commit, 'Copyright (c) 2026 kajisho5')) {
                if (-not $notices.Contains($needle)) { Add-Failure "THIRD_PARTY_NOTICES.md does not mention '$needle'" }
            }
        }

        Write-Host 'generate.py --check:'
        if ((Invoke-Generate @('--check')) -ne 0) { Add-Failure 'generate.py --check reports drift' }

        if ($script:Failures.Count -gt 0) {
            Write-Host ''
            Write-Host "Sync -Check FAILED ($($script:Failures.Count) problems)" -ForegroundColor Red
            exit 1
        }
        Write-Host ''
        Write-Host "Sync -Check passed: $($expected.Count) files match $Tag ($Commit)" -ForegroundColor Green
        exit 0
    }

    # --- 5. swap the vendor folder, write the lock, regenerate ----------------------------------
    New-Item -ItemType Directory -Path $VendorParent -Force | Out-Null
    $foreign = @(Get-ChildItem -LiteralPath $VendorParent -Force | Where-Object { $_.Name -ne $VendorName })
    foreach ($f in $foreign) { Add-Failure "skills/ffmpeg-video/vendor/ holds $($f.Name), which no lock describes; remove it" }
    if ($script:Failures.Count -gt 0) { throw 'the vendor folder holds unexpected entries' }

    $previous = $null
    if (Test-Path -LiteralPath $VendorDir) {
        $previous = Join-Path (New-TempDir 'ffvideo-previous') $VendorName
        Move-Item -LiteralPath $VendorDir -Destination $previous
    }
    try {
        Move-Item -LiteralPath $stageVendor -Destination $VendorDir
    } catch {
        if ($previous) { Move-Item -LiteralPath $previous -Destination $VendorDir }
        throw
    }
    Write-Host "vendored $($expected.Count) files into skills/ffmpeg-video/vendor/$VendorName"

    Write-Host 'generate.py --write-lock --summary:'
    $genExit = Invoke-Generate @('--write-lock', '--repo', $RepoUrl, '--tag', $Tag, '--commit', $Commit, '--summary')
    if ($genExit -ne 0) {
        Add-Failure 'generate.py failed: fix the problems above (policy.json, or review an upstream change), then run this sync again'
    }

    if (Test-Path -LiteralPath $NoticesPath -PathType Leaf) {
        $notices = Get-Content -LiteralPath $NoticesPath -Raw -Encoding utf8
        if (-not ($notices.Contains($Tag) -and $notices.Contains($Commit))) {
            Add-Warning "THIRD_PARTY_NOTICES.md does not name $Tag and $Commit yet"
        }
    } else {
        Add-Warning 'THIRD_PARTY_NOTICES.md does not exist yet'
    }

    # --- 6. review checklist --------------------------------------------------------------------
    $base = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.base.json') -Raw -Encoding utf8 | ConvertFrom-Json
    Write-Host ''
    Write-Host 'Review checklist:'
    Write-Host "  [ ] bump build/ffmpeg-video/manifest.base.json version (now $($base.version)): patch when the surface diff is empty, minor for additions, major for removals or renames; then run generate.py"
    Write-Host '  [ ] review every new or changed path classification in the summary above (policy.json paths/literals)'
    Write-Host "  [ ] scripts/_contract.py is $contractBytes bytes (moderator preview cap $PreviewCapBytes)"
    Write-Host "  [ ] _platforms.py $limitsAsOf (note a change in the release notes)"
    Write-Host "  [ ] THIRD_PARTY_NOTICES.md names $Tag and $Commit"
    Write-Host '  [ ] on a major bump: update the video-producer agent text and pins'
    Write-Host '  [ ] run python tests/skills/run_all.py and the media tests; then Sync -Check'

    if ($script:Failures.Count -gt 0) {
        Write-Host ''
        Write-Host "Sync finished with $($script:Failures.Count) problems" -ForegroundColor Red
        exit 1
    }
    Write-Host ''
    Write-Host "Sync complete: $Tag ($Commit)" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    foreach ($dir in $script:TempDirs) {
        if (Test-Path -LiteralPath $dir) { Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue }
    }
}
