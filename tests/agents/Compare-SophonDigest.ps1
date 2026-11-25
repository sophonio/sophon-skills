#Requires -Version 7.0

<#
.SYNOPSIS
    The Sophon-default digest check: every value of fragment 21-sophon-default and of topic design-sophon-default,
    looked up in the shipped Sophon Dashboard tokens.
.DESCRIPTION
    Read-only and maintainer-only (never in CI: CI has no sibling repository). It reads the value lines of
    build/agent-src/fragments/soul/21-sophon-default.md and of build/craft-reference/topics/design/design-sophon-default.md
    and checks each colour, size, duration, easing, radius and font value against the Dashboard token files at a
    pinned commit of the sibling sophon repository, read with git show (nothing is checked out or fetched):

      src/Sophon.Dashboard/src/index.css          the colour roles (@theme = light, .dark, .extra-dark, .graphite)
      src/Sophon.Dashboard/src/styles/tokens.css  space, type, radius, tracking, elevation, status, shell
      src/Sophon.Dashboard/src/styles/motion.css  durations, easings, reduced motion, the loading loops

    Where a document names the token (a role, a type step, a space step, a radius, a motion token, a status, a chart
    series), the value must equal that token in that theme; elsewhere it must occur in the token set of its kind.
    A colour, font or unit-bearing size or duration the tokens do not carry may instead be found in the product's
    design-language notes (sophon docs/DESIGN-LANGUAGE.md at the v3-main pin) or the website's design rules
    (sophon-website DESIGN.md), which are searched as text for the whole value (a whole font name, a number with its
    unit, a hex that is not part of a longer one). Contrast ratios, alpha percentages, font weights and shadow colours
    are not checked; shadow px values are checked only as members of the set of all --elev-* px values.

    A value that is neither found nor listed in the explain table below (value, source, reason, line context) is a miss.
    Exit 0 when every value is found or explained, or when the sibling repository is absent (SKIP, unless
    -Require); 1 on any miss or when a pinned token file cannot be read. The fallback documents are optional: one that cannot be read is skipped
    with a note, which can only add misses.
.PARAMETER SophonRepo
    The sophon repository. Default: the folder 'sophon' beside this repository's main checkout.
.PARAMETER Require
    Fail (exit 1) instead of SKIP when the sophon repository is absent. The release gate runs with it.
.PARAMETER SophonCommit
    The Dashboard token pin. Default: a431e1a64.
.PARAMETER DesignLanguageRepo
    A checkout that holds the design-language pin (a sophon worktree shares its objects). Default: sophon-wt/v3-main
    beside the main checkout, else -SophonRepo.
.PARAMETER DesignLanguageCommit
    Default: 38c3f7d.
.PARAMETER WebsiteRepo
    The sophon-website repository. Default: the folder 'sophon-website' beside the main checkout.
.PARAMETER WebsiteCommit
    Default: 4973283.
.PARAMETER TokenDir
    Read index.css, tokens.css and motion.css from this folder instead of git (the test fixtures).
.PARAMETER FallbackDir
    With -TokenDir: read DESIGN-LANGUAGE.md and DESIGN.md from this folder when present.
.PARAMETER FragmentPath
    The fragment to check. Default: build/agent-src/fragments/soul/21-sophon-default.md.
.PARAMETER TopicPath
    The topic to check. Default: build/craft-reference/topics/design/design-sophon-default.md.
.PARAMETER NoTopic
    Check the fragment only.
.PARAMETER RepoRoot
    Repository root. Defaults to the grandparent of this script.
.PARAMETER ShowAll
    Print every checked value, not only the misses, the explained values and the fallback finds.
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Compare-SophonDigest.ps1
.EXAMPLE
    pwsh -NoProfile -File tests/agents/Compare-SophonDigest.ps1 -SophonRepo ../sophon -ShowAll
#>
[CmdletBinding()]
param(
    [string]$SophonRepo = '',
    [switch]$Require,
    [string]$SophonCommit = 'a431e1a64',
    [string]$DesignLanguageRepo = '',
    [string]$DesignLanguageCommit = '38c3f7d',
    [string]$WebsiteRepo = '',
    [string]$WebsiteCommit = '4973283',
    [string]$TokenDir = '',
    [string]$FallbackDir = '',
    [string]$FragmentPath = '',
    [string]$TopicPath = '',
    [switch]$NoTopic,
    [string]$RepoRoot = (Join-Path $PSScriptRoot '../..'),
    [switch]$ShowAll
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepoRoot = [IO.Path]::GetFullPath($RepoRoot)
$ord = [StringComparison]::Ordinal

# ---- Explain table ----------------------------------------------------------------------------------------------
# A value the tokens and the fallback documents do not carry, with the reason it is still right. Source is
# 'fragment' or 'topic'; Kind is the kind the report prints; Value is the value as the report prints it; Context is
# text the value's line must contain, so an entry explains only the sentence it was written for.
$Explain = @(
    @{ Source = 'topic'; Kind = 'colour'; Value = '#100E21'; Context = 'flattens to about #100E21'
       Reason = 'computed, not a token: tokens.css flattens the dark shell panel as color-mix(#ffffff 3%, #09071A); the topic names it only to send readers to the panel token #110F26' }
    @{ Source = 'topic'; Kind = 'text-size'; Value = '10 px'; Context = 'older 10 px labels are not copied'
       Reason = 'a rejected size: the topic says older 10 px labels are not copied; the type scale starts at --text-xs 11px' }
)

$TokenFiles = [ordered]@{
    'index.css'  = 'src/Sophon.Dashboard/src/index.css'
    'tokens.css' = 'src/Sophon.Dashboard/src/styles/tokens.css'
    'motion.css' = 'src/Sophon.Dashboard/src/styles/motion.css'
}

# Role words of the two documents -> the Dashboard colour token that carries them.
$RoleTokens = @{
    'page' = 'color-background'; 'panel' = 'color-card'; 'raised fill' = 'color-muted'; 'selected fill' = 'color-accent'
    'text' = 'color-foreground'; 'muted text' = 'color-muted-foreground'; 'hairline' = 'color-border'
    'primary' = 'color-primary'; 'on primary' = 'color-primary-foreground'; 'focus ring' = 'color-ring'
    'success' = 'color-success'; 'warning' = 'color-warning'; 'info' = 'color-info'; 'danger' = 'color-danger'
}
$ThemeColumns = @{ 'dark' = 'dark'; 'light' = 'light'; 'core extra dark' = 'extra-dark'; 'graphite' = 'graphite' }

$hexPattern = '#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b'
$easePattern = 'cubic-bezier\(\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*,\s*-?[\d.]+\s*\)'

function Get-NormalHex([string]$Hex) {
    $h = $Hex.TrimStart('#').ToUpperInvariant()
    if ($h.Length -eq 3) { $h = -join @($h.ToCharArray() | ForEach-Object { "$_$_" }) }
    "#$h"
}
function Get-NormalEase([string]$Text) { ($Text -replace '\s+', '').ToLowerInvariant() }
function Get-Ms([string]$Number, [string]$Unit) {
    $n = [double]::Parse($Number, [Globalization.CultureInfo]::InvariantCulture)
    if ($Unit -eq 's') { $n * 1000 } else { $n }
}

function Resolve-SiblingRoot {
    # The folder that holds the sibling repositories: the parent of this repository's main checkout (a linked
    # worktree resolves through the git common directory), else the parent of RepoRoot.
    try {
        $common = @(& git -C $RepoRoot rev-parse --path-format=absolute --git-common-dir 2>$null)
        if ($LASTEXITCODE -eq 0 -and $common.Count -gt 0) {
            $main = Split-Path -Parent ([IO.Path]::GetFullPath([string]$common[0]))
            return (Split-Path -Parent $main)
        }
    } catch { }
    Split-Path -Parent $RepoRoot
}

function Read-GitFile([string]$Repo, [string]$Commit, [string]$Path) {
    $out = & git -C $Repo show "${Commit}:$Path" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "git show ${Commit}:$Path in $Repo failed: $(@($out) -join ' ')" }
    (@($out | ForEach-Object { "$_" }) -join "`n")
}

# ---- CSS: declarations with their selector stack ----------------------------------------------------------------
function Read-CssDeclarations([string]$Text, [string]$File) {
    $clean = [regex]::Replace($Text, '/\*.*?\*/', ' ', [Text.RegularExpressions.RegexOptions]::Singleline)
    $decls = [System.Collections.Generic.List[object]]::new()
    $stack = [System.Collections.Generic.List[string]]::new()
    $buf = [Text.StringBuilder]::new()
    $quote = [char]0
    $flush = {
        $t = ($buf.ToString() -replace '\s+', ' ').Trim()
        [void]$buf.Clear()
        if ($t -match '^(?<p>-{0,2}[A-Za-z][\w-]*)\s*:\s*(?<v>.+)$' -and -not $t.StartsWith('@')) {
            $decls.Add([pscustomobject]@{ File = $File; Prop = $Matches['p']; Value = $Matches['v'].Trim(); Stack = @($stack) })
        }
    }
    foreach ($ch in $clean.ToCharArray()) {
        if ($quote -ne [char]0) { [void]$buf.Append($ch); if ($ch -eq $quote) { $quote = [char]0 }; continue }
        switch ($ch) {
            { $_ -eq '"' -or $_ -eq "'" } { $quote = $ch; [void]$buf.Append($ch); continue }
            '{' { $stack.Add(($buf.ToString() -replace '\s+', ' ').Trim()); [void]$buf.Clear(); continue }
            '}' { & $flush; if ($stack.Count -gt 0) { $stack.RemoveAt($stack.Count - 1) }; continue }
            ';' { & $flush; continue }
            default { [void]$buf.Append($ch) }
        }
    }
    $decls
}

function Get-DeclModes($Decl) {
    # light (:root, @theme), dark, extra-dark, graphite; 'reduced-' in front inside a reduced-motion media query.
    $reduced = $false
    $modes = @()
    for ($i = $Decl.Stack.Count - 1; $i -ge 0; $i--) {
        $sel = [string]$Decl.Stack[$i]
        if ($sel.StartsWith('@media', $ord) -and $sel.Contains('prefers-reduced-motion', $ord)) { $reduced = $true; continue }
        if ($sel.StartsWith('@layer', $ord) -or $sel.StartsWith('@media', $ord)) { continue }
        if ($modes.Count -gt 0) { continue }
        foreach ($part in $sel.Split(',')) {
            $p = $part.Trim()
            if ($p -ceq ':root' -or $p -ceq '@theme') { $modes += 'light' }
            elseif ($p -ceq '.dark') { $modes += 'dark' }
            elseif ($p -ceq '.extra-dark') { $modes += 'extra-dark' }
            elseif ($p -ceq '.graphite') { $modes += 'graphite' }
        }
        if ($modes.Count -eq 0) { $modes = @('other') }
    }
    if ($reduced) { $modes = @($modes | ForEach-Object { "reduced-$_" }) }
    $modes
}

# ---- The token model ----------------------------------------------------------------------------------------------
function New-TokenModel([hashtable]$Texts) {
    $all = [System.Collections.Generic.List[object]]::new()
    foreach ($name in $Texts.Keys) { foreach ($d in @(Read-CssDeclarations $Texts[$name] $name)) { $all.Add($d) } }
    $byMode = @{}
    foreach ($d in $all) {
        foreach ($m in @(Get-DeclModes $d)) {
            if (-not $byMode.ContainsKey($m)) { $byMode[$m] = @{} }
            $byMode[$m][$d.Prop] = $d   # the last declaration wins, as in the cascade of one file order
        }
    }
    $model = @{
        All = $all; ByMode = $byMode
        Colours = [System.Collections.Generic.HashSet[string]]::new()
        TextSizes = @{}; TextPairs = @{}; Space = @{}; Radius = @{}; Tracking = @{}
        Durations = @{}; DurationSet = [System.Collections.Generic.HashSet[double]]::new()
        Easings = @{}; EasingSet = [System.Collections.Generic.HashSet[string]]::new()
        Fonts = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        ElevPx = [System.Collections.Generic.HashSet[int]]::new(); AllPx = [System.Collections.Generic.HashSet[int]]::new()
        Props = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    }
    foreach ($d in $all) {
        [void]$model.Props.Add($d.Prop)
        foreach ($m in [regex]::Matches($d.Value, $hexPattern)) { [void]$model.Colours.Add((Get-NormalHex $m.Value)) }
        foreach ($m in [regex]::Matches($d.Value, '(?<![\w.])(\d+)px\b')) { [void]$model.AllPx.Add([int]$m.Groups[1].Value) }
        if ($d.Prop.StartsWith('--elev-', $ord)) { foreach ($m in [regex]::Matches($d.Value, '(?<![\w.])(\d+)px\b')) { [void]$model.ElevPx.Add([int]$m.Groups[1].Value) } }
        if ($d.File -eq 'motion.css') {
            foreach ($m in [regex]::Matches($d.Value, '(?<![\w.])(\d+(?:\.\d+)?)(ms|s)\b')) { [void]$model.DurationSet.Add((Get-Ms $m.Groups[1].Value $m.Groups[2].Value)) }
            foreach ($m in [regex]::Matches($d.Value, $easePattern)) { [void]$model.EasingSet.Add((Get-NormalEase $m.Value)) }
            if ($d.Value -ceq 'linear') { [void]$model.EasingSet.Add('linear') }
        }
        if ($d.Prop -ceq 'font-family' -or $d.Prop.StartsWith('--font-', $ord)) {
            foreach ($f in $d.Value.Split(',')) { $n = $f.Trim().Trim('"', "'").Trim(); if ($n) { [void]$model.Fonts.Add($n) } }
        }
    }
    $light = if ($byMode.ContainsKey('light')) { $byMode['light'] } else { @{} }
    foreach ($prop in $light.Keys) {
        $v = [string]$light[$prop].Value
        $px = [regex]::Match($v, '^(\d+)px$')
        $pm = [regex]::Match($prop, '^--(?:(?<k>text|space|radius|tracking)-(?<s>\w+)|(?<k>motion-duration|motion-ease|motion)-(?<s>[\w-]+))$')
        if (-not $pm.Success) { continue }
        $s = $pm.Groups['s'].Value
        switch ($pm.Groups['k'].Value) {
            'text' { if ($px.Success) { $model.TextSizes[$s] = [int]$px.Groups[1].Value } }
            'space' { if ($px.Success -and $s -match '^\d+$') { $model.Space[$s] = [int]$px.Groups[1].Value } }
            'radius' { if ($px.Success) { $model.Radius[$s] = [int]$px.Groups[1].Value } }
            'tracking' { $model.Tracking[$s] = $v }
            'motion-duration' { $dm = [regex]::Match($v, '^(\d+(?:\.\d+)?)(ms|s)$'); if ($dm.Success) { $model.Durations[$s] = (Get-Ms $dm.Groups[1].Value $dm.Groups[2].Value) } }
            { $_ -in 'motion-ease', 'motion' } { if ($v -match $easePattern) { $model.Easings[$s] = (Get-NormalEase $v) } }
        }
    }
    foreach ($step in @($model.TextSizes.Keys)) {
        $lineProp = "--text-$step-line"
        if ($light.ContainsKey($lineProp) -and [string]$light[$lineProp].Value -match '^(\d+)px$') { $model.TextPairs["$($model.TextSizes[$step])/$($Matches[1])"] = $step }
    }
    $model
}

function Get-Token($Model, [string]$Mode, [string]$Name) {
    if (-not $Model.ByMode.ContainsKey($Mode)) { return $null }
    $prop = "--$Name"
    if ($Model.ByMode[$Mode].ContainsKey($prop)) { return $Model.ByMode[$Mode][$prop] }
    $null
}

# ---- Value records ------------------------------------------------------------------------------------------------
$records = [System.Collections.Generic.List[object]]::new()
function Add-Value([string]$Source, [int]$Line, [string]$Kind, [string]$Value, [hashtable]$Named = $null, $Number = $null) {
    $records.Add([pscustomobject]@{ Source = $Source; Line = $Line; Kind = $Kind; Value = $Value; Named = $Named; Number = $Number; Status = ''; Detail = '' })
}
function Add-Hex([string]$Source, [int]$Line, [string]$Hex, [string]$Mode, [string]$Token) {
    $named = if ($Token) { @{ Mode = $Mode; Token = $Token } } else { $null }
    Add-Value $Source $Line 'colour' (Get-NormalHex $Hex) $named
}

function Get-Ints([string]$Text) { @([regex]::Matches($Text, '(?<![\w.#-])(\d+)(?!\w|\.\d|\s*:)') | ForEach-Object { [int]$_.Groups[1].Value }) }

function Add-UnitValues([string]$Source, [int]$Line, [string]$Text, [string]$PxKind) {
    # Lists such as "80, 150, 220 or 320 ms" or "6, 10, 14 or 18 px"; "1px" and "1.4 s" too.
    foreach ($m in [regex]::Matches($Text, '(?<![\w.#-])(?<nums>\d+(?:\.\d+)?(?:\s*(?:,|or|and)\s*\d+(?:\.\d+)?)*)\s*(?<unit>px|ms|s)\b')) {
        $unit = $m.Groups['unit'].Value
        foreach ($n in [regex]::Matches($m.Groups['nums'].Value, '\d+(?:\.\d+)?')) {
            if ($unit -eq 'px') { Add-Value $Source $Line $PxKind "$($n.Value) px" $null ([int][double]$n.Value) }
            else { Add-Value $Source $Line 'duration' "$($n.Value) $unit" $null (Get-Ms $n.Value $unit) }
        }
    }
}
function Add-Easings([string]$Source, [int]$Line, [string]$Text) {
    foreach ($m in [regex]::Matches($Text, $easePattern)) { Add-Value $Source $Line 'easing' (Get-NormalEase $m.Value) }
}
function Add-LooseHexes([string]$Source, [int]$Line, [string]$Text, [string[]]$Taken) {
    $left = [System.Collections.Generic.List[string]]::new()
    foreach ($t in $Taken) { $left.Add($t) }
    foreach ($m in [regex]::Matches($Text, $hexPattern)) {
        $h = Get-NormalHex $m.Value
        if ($left.Contains($h)) { [void]$left.Remove($h); continue }
        Add-Hex $Source $Line $h '' ''
    }
}

function Add-RolePairs([string]$Source, [int]$Line, [string]$Text) {
    # "page #09071A / #F8FAFC; ... primary #818CF8 under #1A1735 text / #4F46E5 under white text" (dark / light).
    $taken = [System.Collections.Generic.List[string]]::new()
    foreach ($clause in [regex]::Split($Text, '[;,]')) {
        if (-not $clause.Contains(' / ', $ord) -or $clause -notmatch $hexPattern) { continue }
        $first = [regex]::Match($clause, $hexPattern)
        $role = $clause.Substring(0, $first.Index).Trim().ToLowerInvariant()
        if (-not $RoleTokens.ContainsKey($role)) { continue }
        $parts = $clause.Substring($first.Index).Split(' / ')
        $modes = @('dark', 'light')
        for ($i = 0; $i -lt [Math]::Min(2, $parts.Count); $i++) {
            $m = [regex]::Match($parts[$i].Trim(), "^(?<main>$hexPattern)(?:\s+under\s+(?<fg>#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}|white|black)\s+text)?")
            if (-not $m.Success) { continue }
            Add-Hex $Source $Line $m.Groups['main'].Value $modes[$i] $RoleTokens[$role]; $taken.Add((Get-NormalHex $m.Groups['main'].Value))
            if ($m.Groups['fg'].Success) {
                $fg = switch ($m.Groups['fg'].Value) { 'white' { '#FFFFFF' } 'black' { '#000000' } default { Get-NormalHex $_ } }
                Add-Hex $Source $Line $fg $modes[$i] "$($RoleTokens[$role])-foreground"
                if ($m.Groups['fg'].Value.StartsWith('#')) { $taken.Add($fg) }
            }
        }
    }
    Add-LooseHexes $Source $Line $Text @($taken)
}

function Read-Fragment([string]$Path) {
    $lines = [IO.File]::ReadAllText($Path).Replace("`r", '').Split("`n")
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $n = $i + 1; $line = $lines[$i]
        $label = if ($line -match '^- (?<l>[A-Z][\w ]*?):\s') { $Matches.l } else { '' }
        $body = if ($label) { $line.Substring($line.IndexOf(':') + 1) } else { $line }
        switch ($label) {
            { $_ -in 'Colour', 'Status' } { Add-RolePairs 'fragment' $n $body }
            'Type' {
                foreach ($sentence in [regex]::Split($body, '\.\s+')) {
                    if ($sentence -match '\d') {
                        foreach ($p in [regex]::Matches($sentence, '(\d+)\s*/\s*(\d+)')) { Add-Value 'fragment' $n 'text-pair' "$($p.Groups[1].Value)/$($p.Groups[2].Value)" }
                        $rest = [regex]::Replace($sentence, '(\d+)\s*/\s*(\d+)', ' ')
                        foreach ($v in Get-Ints $rest) { Add-Value 'fragment' $n 'text-size' "$v px" $null $v }
                    } else {
                        foreach ($clause in $sentence.Split(';')) {
                            if ($clause.Trim() -cmatch '^(?<f>[A-Z][\w-]*(?:\s+[A-Z][\w-]*)*)') { Add-Value 'fragment' $n 'font' $Matches.f }
                        }
                    }
                }
            }
            'Space' {
                foreach ($sentence in [regex]::Split($body, '\.\s+')) {
                    if ($sentence.Trim().StartsWith('Radius', $ord)) {
                        foreach ($v in Get-Ints $sentence) { Add-Value 'fragment' $n 'radius' "$v px" $null $v }
                        if ($sentence -match '\bpill\b') { Add-Value 'fragment' $n 'radius' 'pill' @{ Token = 'radius-pill' } }
                    } else {
                        foreach ($v in Get-Ints $sentence) { Add-Value 'fragment' $n 'space' "$v px" $null $v }
                    }
                }
            }
            'Depth' { Add-UnitValues 'fragment' $n $body 'elevation-px'; Add-LooseHexes 'fragment' $n $body @() }
            'Motion' { Add-UnitValues 'fragment' $n $body 'px'; Add-Easings 'fragment' $n $body; Add-LooseHexes 'fragment' $n $body @() }
            default { Add-UnitValues 'fragment' $n $body 'px'; Add-Easings 'fragment' $n $body; Add-LooseHexes 'fragment' $n $body @() }
        }
    }
}

function Split-Row([string]$Line) { @($Line.Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() }) }

function Read-Topic([string]$Path) {
    $lines = [IO.File]::ReadAllText($Path).Replace("`r", '').Split("`n")
    $section = ''; $header = $null; $inFront = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $n = $i + 1; $line = $lines[$i]
        if ($i -eq 0 -and $line -eq '---') { $inFront = $true; continue }
        if ($inFront) { if ($line -eq '---') { $inFront = $false }; continue }
        if ($line -match '^##\s+(?<h>.+)$') { $section = $Matches.h.Trim(); $header = $null; continue }
        if (-not $line.StartsWith('|')) {
            $header = $null
            # Prose and bullets.
            if ($line -match 'face:\s*(?<list>[^.]+)') {
                # The face list ends at the first item that is not a font name (a lower-case phrase).
                foreach ($f in [regex]::Split($Matches.list, ',\s*(?:then\s+)?|\s+then\s+')) {
                    $name = $f.Trim()
                    if ($name -cnotmatch '^(?:[\w-]+|[A-Z][\w-]*(?: [A-Z][\w-]*)+)$') { break }
                    Add-Value 'topic' $n 'font' $name
                }
            }
            foreach ($m in [regex]::Matches($line, '`(?<p>[a-z-]+):\s*(?<v>[\w-]+)`')) {
                if ($Model.Props.Contains($m.Groups['p'].Value)) { Add-Value 'topic' $n 'font-feature' "$($m.Groups['p'].Value): $($m.Groups['v'].Value)" }
            }
            if ($line -match 'Chart series' -and $line -match '\bdark\s+(?<d>[^;]+);\s*light\s+(?<l>[^.]+)') {
                $dark = @([regex]::Matches($Matches.d, $hexPattern)); $lite = @([regex]::Matches($Matches.l, $hexPattern))
                for ($k = 0; $k -lt $dark.Count; $k++) { Add-Hex 'topic' $n $dark[$k].Value 'dark' "color-chart-$($k + 1)" }
                for ($k = 0; $k -lt $lite.Count; $k++) { Add-Hex 'topic' $n $lite[$k].Value 'light' "color-chart-$($k + 1)" }
                continue
            }
            if ($section -eq 'Type') {
                foreach ($m in [regex]::Matches($line, '\b(?<t>[a-z]+)\s+(?<v>-?\d+(?:\.\d+)?em)\b')) { Add-Value 'topic' $n 'tracking' $m.Groups['v'].Value @{ Token = "tracking-$($m.Groups['t'].Value)" } }
                Add-UnitValues 'topic' $n $line 'text-size'
            } elseif ($section -eq 'Elevation') { Add-UnitValues 'topic' $n $line 'elevation-px' }
            else { Add-UnitValues 'topic' $n $line 'px' }
            Add-Easings 'topic' $n $line
            Add-LooseHexes 'topic' $n $line @()
            continue
        }
        $cells = Split-Row $line
        if ($null -eq $header) { $header = $cells; continue }
        if ($line -match '^\|\s*-') { continue }
        $taken = [System.Collections.Generic.List[string]]::new()
        $h0 = [string]$header[0]
        if ($section -match '^(Dark|Light) roles$' -and $header -contains 'Product token') {
            $mode = $Matches[1].ToLowerInvariant()
            $vi = [array]::IndexOf($header, 'Value'); $ti = [array]::IndexOf($header, 'Product token')
            $hex = [regex]::Match($cells[$vi], $hexPattern)
            if ($hex.Success) {
                $tokens = @([regex]::Matches($cells[$ti], '(?<!\()\bcolor-[\w-]+') | ForEach-Object { $_.Value })
                if ($cells[$ti].StartsWith('(')) { $tokens = @() }
                if ($tokens.Count -eq 0) { Add-Hex 'topic' $n $hex.Value '' '' }
                foreach ($t in $tokens) { Add-Hex 'topic' $n $hex.Value $mode $t }
                $taken.Add((Get-NormalHex $hex.Value))
            }
        } elseif ($h0 -eq 'Status' -and $cells.Count -ge 3) {
            $status = $cells[0].ToLowerInvariant()
            for ($c = 1; $c -lt $header.Count; $c++) {
                $col = ([string]$header[$c]).ToLowerInvariant()
                $hexes = @([regex]::Matches($cells[$c], $hexPattern))
                if ($col -in 'dark', 'light' -and $hexes.Count -ge 1) { Add-Hex 'topic' $n $hexes[0].Value $col "color-$status"; $taken.Add((Get-NormalHex $hexes[0].Value)) }
                elseif ($col -match '^(dark|light) tint' -and $hexes.Count -eq 2) {
                    $m = $Matches[1]
                    Add-Hex 'topic' $n $hexes[0].Value $m "color-$status-bg"; Add-Hex 'topic' $n $hexes[1].Value $m "color-$status-border"
                    $taken.Add((Get-NormalHex $hexes[0].Value)); $taken.Add((Get-NormalHex $hexes[1].Value))
                }
            }
        } elseif ($h0 -eq 'Role' -and $header.Count -ge 2) {
            $role = $cells[0].ToLowerInvariant()
            for ($c = 1; $c -lt $header.Count; $c++) {
                $col = ([string]$header[$c]).ToLowerInvariant()
                $hex = [regex]::Match($cells[$c], $hexPattern)
                if ($hex.Success -and $ThemeColumns.ContainsKey($col) -and $RoleTokens.ContainsKey($role)) {
                    Add-Hex 'topic' $n $hex.Value $ThemeColumns[$col] $RoleTokens[$role]; $taken.Add((Get-NormalHex $hex.Value))
                }
            }
        } elseif ($h0 -eq 'Step' -and $section -eq 'Type') {
            $steps = @($cells[0].Split(',') | ForEach-Object { $_.Trim() })
            $pairs = @([regex]::Matches($cells[1], '(\d+)\s*/\s*(\d+)'))
            for ($k = 0; $k -lt $pairs.Count; $k++) {
                $step = if ($k -lt $steps.Count) { $steps[$k] } else { '' }
                Add-Value 'topic' $n 'text-pair' "$($pairs[$k].Groups[1].Value)/$($pairs[$k].Groups[2].Value)" @{ Token = "text-$step" }
            }
            continue
        } elseif ($h0 -eq 'Space step') {
            if ($cells[0] -eq 'px') {
                for ($c = 1; $c -lt $cells.Count; $c++) { Add-Value 'topic' $n 'space' "$($cells[$c]) px" @{ Token = "space-$($header[$c])" } ([int]$cells[$c]) }
            }
            continue
        } elseif ($h0 -eq 'Radius' -and $cells.Count -ge 2 -and $cells[1] -match '^\d+$') {
            Add-Value 'topic' $n 'radius' "$($cells[1]) px" @{ Token = "radius-$($cells[0])" } ([int]$cells[1])
            continue
        } elseif ($h0 -eq 'Token' -and $section -eq 'Motion tokens') {
            $name = $cells[0]; $value = $cells[1]
            if ($value -match '^(\d+(?:\.\d+)?)\s*(ms|s)$') { Add-Value 'topic' $n 'duration' $value @{ Token = "motion-duration-$name" } (Get-Ms $Matches[1] $Matches[2]) }
            elseif ($value -match $easePattern) {
                $ease = if ($name.StartsWith('ease-', $ord)) { "motion-$name" } else { "motion-ease-$name" }
                Add-Value 'topic' $n 'easing' (Get-NormalEase $value) @{ Token = $ease }
            }
            continue
        } elseif ($h0 -eq 'Face' -and $section -eq 'Fonts') {
            Add-Value 'topic' $n 'font' $cells[0]
            continue
        }
        $kind = if ($section -eq 'Elevation') { 'elevation-px' } elseif ($section -eq 'Type') { 'text-size' } else { 'px' }
        Add-UnitValues 'topic' $n $line $kind
        Add-Easings 'topic' $n $line
        Add-LooseHexes 'topic' $n $line @($taken)
    }
}

# ---- Resolution -------------------------------------------------------------------------------------------------
function Get-FallbackPattern([string]$Kind, [string]$Value) {
    # Whole values only: a font or feature is a case-sensitive whole name ('Inter' is not in 'pointer'), a number
    # stands alone with its unit ('20 ms' is not in '120ms', '6 px' not in '16px'), a hex is not part of a longer hex.
    switch ($Kind) {
        'colour' { return "(?i)(?<![0-9A-F])$([regex]::Escape($Value))(?![0-9A-F])" }
        { $_ -in 'font', 'font-feature' } { return "(?<![\w-])$([regex]::Escape($Value))(?![\w-])" }
        { $_ -in 'duration', 'px', 'elevation-px' } {
            $u = [regex]::Match($Value, '^(?<n>\d+(?:\.\d+)?) (?<u>px|ms|s)$')
            if ($u.Success) { return "(?<![\d.])$([regex]::Escape($u.Groups['n'].Value))\s?$($u.Groups['u'].Value)\b" }
        }
    }
    $null
}
function Find-InFallback([string]$Kind, [string]$Value, $Number) {
    $pattern = Get-FallbackPattern $Kind $Value
    if (-not $pattern) { return $null }
    foreach ($doc in $Fallback.Keys) {
        if ([regex]::IsMatch($Fallback[$doc], $pattern)) { return $doc }
    }
    $null
}

function Resolve-Value($Rec) {
    $m = $Model
    if ($null -ne $Rec.Named -and $Rec.Kind -eq 'colour') {
        $decl = Get-Token $m $Rec.Named.Mode $Rec.Named.Token
        if ($null -eq $decl) { return @('miss', "no --$($Rec.Named.Token) in the $($Rec.Named.Mode) theme") }
        $hexes = @([regex]::Matches($decl.Value, $hexPattern) | ForEach-Object { Get-NormalHex $_.Value })
        if ($hexes.Count -eq 1 -and $decl.Value.Trim() -match "^$hexPattern$" -and $hexes[0] -eq $Rec.Value) { return @('found', "$($decl.File) --$($Rec.Named.Token) ($($Rec.Named.Mode))") }
        return @('miss', "--$($Rec.Named.Token) ($($Rec.Named.Mode), $($decl.File)) is $($decl.Value)")
    }
    switch ($Rec.Kind) {
        'colour' { if ($m.Colours.Contains($Rec.Value)) { return @('found', 'a colour of the token files') } }
        'font' { if ($m.Fonts.Contains($Rec.Value)) { return @('found', 'a font-family or --font-* value') } }
        'font-feature' {
            $p, $v = $Rec.Value.Split(':', 2) | ForEach-Object { $_.Trim() }
            foreach ($d in $m.All) { if ($d.Prop -ceq $p -and $d.Value.Contains($v, $ord)) { return @('found', "$($d.File) $p") } }
        }
        'text-size' {
            if ($m.TextSizes.Values -contains $Rec.Number) { return @('found', '--text-* size') }
            return @('miss', 'not a --text-* size')
        }
        'text-pair' {
            if ($null -ne $Rec.Named) {
                $step = $Rec.Named.Token.Substring(5)
                if ($m.TextPairs.ContainsKey($Rec.Value) -and $m.TextPairs[$Rec.Value] -ceq $step) { return @('found', "--text-$step and --text-$step-line") }
                $actual = if ($m.TextSizes.ContainsKey($step)) { "$($m.TextSizes[$step])/" + (@($m.TextPairs.Keys | Where-Object { $m.TextPairs[$_] -ceq $step }) -join '') } else { 'absent' }
                return @('miss', "--text-$step is $actual")
            }
            if ($m.TextPairs.ContainsKey($Rec.Value)) { return @('found', "--text-$($m.TextPairs[$Rec.Value]) and its -line") }
            return @('miss', 'no --text-* size and line pair')
        }
        'space' {
            if ($null -ne $Rec.Named) {
                $step = $Rec.Named.Token.Substring(6)
                if ($m.Space.ContainsKey($step) -and $m.Space[$step] -eq $Rec.Number) { return @('found', "--$($Rec.Named.Token)") }
                $actual = if ($m.Space.ContainsKey($step)) { "$($m.Space[$step])px" } else { 'absent' }
                return @('miss', "--$($Rec.Named.Token) is $actual")
            }
            if ($m.Space.Values -contains $Rec.Number) { return @('found', '--space-* step') }
            return @('miss', 'not a --space-* step')
        }
        'radius' {
            if ($null -ne $Rec.Named) {
                $name = $Rec.Named.Token.Substring(7)
                if ($Rec.Value -eq 'pill') { if ($m.Radius.ContainsKey('pill')) { return @('found', '--radius-pill') } else { return @('miss', 'no --radius-pill') } }
                if ($m.Radius.ContainsKey($name) -and $m.Radius[$name] -eq $Rec.Number) { return @('found', "--$($Rec.Named.Token)") }
                $actual = if ($m.Radius.ContainsKey($name)) { "$($m.Radius[$name])px" } else { 'absent' }
                return @('miss', "--$($Rec.Named.Token) is $actual")
            }
            foreach ($k in $m.Radius.Keys) { if ($k -ne 'pill' -and $m.Radius[$k] -eq $Rec.Number) { return @('found', "--radius-$k") } }
            return @('miss', 'not a --radius-* value')
        }
        'tracking' {
            $name = $Rec.Named.Token.Substring(9)
            if ($m.Tracking.ContainsKey($name) -and $m.Tracking[$name] -ceq $Rec.Value) { return @('found', "--$($Rec.Named.Token)") }
            return @('miss', "--$($Rec.Named.Token) is $(if ($m.Tracking.ContainsKey($name)) { $m.Tracking[$name] } else { 'absent' })")
        }
        'duration' {
            if ($null -ne $Rec.Named) {
                $name = $Rec.Named.Token.Substring(16)
                if ($m.Durations.ContainsKey($name) -and $m.Durations[$name] -eq $Rec.Number) { return @('found', "--$($Rec.Named.Token)") }
                return @('miss', "--$($Rec.Named.Token) is $(if ($m.Durations.ContainsKey($name)) { "$($m.Durations[$name])ms" } else { 'absent' })")
            }
            if ($m.DurationSet.Contains([double]$Rec.Number)) { return @('found', 'a duration of motion.css') }
        }
        'easing' {
            if ($null -ne $Rec.Named) {
                $name = $Rec.Named.Token -replace '^motion-(ease-)?', ''
                if ($m.Easings.ContainsKey($name) -and $m.Easings[$name] -ceq $Rec.Value) { return @('found', "--$($Rec.Named.Token)") }
                return @('miss', "--$($Rec.Named.Token) is $(if ($m.Easings.ContainsKey($name)) { $m.Easings[$name] } else { 'absent' })")
            }
            if ($m.EasingSet.Contains($Rec.Value)) { return @('found', 'an easing of motion.css') }
            return @('miss', 'not an easing of motion.css')
        }
        'elevation-px' { if ($m.ElevPx.Contains([int]$Rec.Number)) { return @('found', 'a --elev-* offset or blur') } }
        'px' { if ($m.AllPx.Contains([int]$Rec.Number)) { return @('found', 'a px value of the token files') } }
    }
    $doc = Find-InFallback $Rec.Kind $Rec.Value $Rec.Number
    if ($doc) { return @('fallback', $doc) }
    @('miss', 'not in the token files or the fallback documents')
}

# ---- Main -------------------------------------------------------------------------------------------------------
try {
    if (-not $FragmentPath) { $FragmentPath = Join-Path $RepoRoot 'build/agent-src/fragments/soul/21-sophon-default.md' }
    if (-not $TopicPath -and -not $NoTopic) { $TopicPath = Join-Path $RepoRoot 'build/craft-reference/topics/design/design-sophon-default.md' }
    if ($NoTopic) { $TopicPath = '' }
    $texts = @{}
    $Fallback = [ordered]@{}
    $pinLine = ''
    if ($TokenDir) {
        foreach ($name in $TokenFiles.Keys) {
            $p = Join-Path $TokenDir $name
            if (Test-Path -LiteralPath $p -PathType Leaf) { $texts[$name] = [IO.File]::ReadAllText($p) }
        }
        if ($texts.Count -eq 0) { throw "no token file in $TokenDir" }
        if ($FallbackDir) {
            foreach ($name in 'DESIGN-LANGUAGE.md', 'DESIGN.md') {
                $p = Join-Path $FallbackDir $name
                if (Test-Path -LiteralPath $p -PathType Leaf) { $Fallback[$name] = [IO.File]::ReadAllText($p) }
            }
        }
        $pinLine = "token files from $TokenDir"
    } else {
        $siblings = Resolve-SiblingRoot
        if (-not $SophonRepo) { $SophonRepo = Join-Path $siblings 'sophon' }
        if (-not (Test-Path -LiteralPath $SophonRepo -PathType Container)) {
            if ($Require) { Write-Host "FAIL: the sophon repository is not at $SophonRepo (pass -SophonRepo); -Require needs it"; exit 1 }
            Write-Host "SKIP: the sophon repository is not at $SophonRepo (pass -SophonRepo); nothing was checked"
            exit 0
        }
        foreach ($name in $TokenFiles.Keys) {
            $listed = @(& git -C $SophonRepo ls-tree --name-only $SophonCommit -- $TokenFiles[$name] 2>&1)
            if ($LASTEXITCODE -ne 0 -or $listed.Count -ne 1 -or "$($listed[0])" -cne $TokenFiles[$name]) { throw "$($TokenFiles[$name]) is not in $SophonRepo at $SophonCommit" }
            $texts[$name] = Read-GitFile $SophonRepo $SophonCommit $TokenFiles[$name]
        }
        if (-not $DesignLanguageRepo) {
            $wt = Join-Path $siblings 'sophon-wt/v3-main'
            $DesignLanguageRepo = if (Test-Path -LiteralPath $wt -PathType Container) { $wt } else { $SophonRepo }
        }
        if (-not $WebsiteRepo) { $WebsiteRepo = Join-Path $siblings 'sophon-website' }
        foreach ($f in @(@{ Name = 'DESIGN-LANGUAGE.md'; Repo = $DesignLanguageRepo; Commit = $DesignLanguageCommit; Path = 'docs/DESIGN-LANGUAGE.md' },
                         @{ Name = 'DESIGN.md'; Repo = $WebsiteRepo; Commit = $WebsiteCommit; Path = 'DESIGN.md' })) {
            if (-not (Test-Path -LiteralPath $f.Repo -PathType Container)) { Write-Host "note: fallback $($f.Name) skipped: no repository at $($f.Repo)"; continue }
            try { $Fallback[$f.Name] = Read-GitFile $f.Repo $f.Commit $f.Path } catch { Write-Host "note: fallback $($f.Name) skipped: $($_.Exception.Message)" }
        }
        $full = [string](@(& git -C $SophonRepo rev-parse "$SophonCommit^{commit}" 2>$null) | Select-Object -First 1)
        $pinLine = "sophon $SophonCommit ($($full.Substring(0, [Math]::Min(12, $full.Length))))"
    }
    $Model = New-TokenModel $texts

    if (-not (Test-Path -LiteralPath $FragmentPath -PathType Leaf)) { throw "no fragment at $FragmentPath" }
    Read-Fragment $FragmentPath
    $SourceLines = @{ fragment = [IO.File]::ReadAllText($FragmentPath).Replace("`r", '').Split("`n") }
    if ($TopicPath) {
        if (-not (Test-Path -LiteralPath $TopicPath -PathType Leaf)) { throw "no topic at $TopicPath" }
        Read-Topic $TopicPath
        $SourceLines['topic'] = [IO.File]::ReadAllText($TopicPath).Replace("`r", '').Split("`n")
    }

    $usedExplain = [System.Collections.Generic.HashSet[int]]::new()
    foreach ($rec in $records) {
        $status, $detail = Resolve-Value $rec
        if ($status -eq 'miss') {
            for ($k = 0; $k -lt $Explain.Count; $k++) {
                $e = $Explain[$k]
                $inContext = -not $e.ContainsKey('Context') -or $SourceLines[$rec.Source][$rec.Line - 1].Contains([string]$e.Context, $ord)
                if ($e.Source -ceq $rec.Source -and $e.Kind -ceq $rec.Kind -and $e.Value -ceq $rec.Value -and $inContext) {
                    $status = 'explained'; $detail = $e.Reason; [void]$usedExplain.Add($k)
                }
            }
        }
        $rec.Status = $status; $rec.Detail = $detail
    }

    $fallbackNames = if ($Fallback.Count -gt 0) { @($Fallback.Keys) -join ', ' } else { 'none' }
    Write-Host "Sophon digest: $pinLine; fallback documents: $fallbackNames"
    $labels = @{ found = 'ok  '; fallback = 'doc '; explained = 'expl'; miss = 'MISS' }
    foreach ($rec in $records) {
        if (-not $ShowAll -and $rec.Status -eq 'found') { continue }
        $named = if ($null -ne $rec.Named -and $rec.Named.ContainsKey('Mode') -and $rec.Named.Mode) { " ($($rec.Named.Mode) --$($rec.Named.Token))" } elseif ($null -ne $rec.Named) { " (--$($rec.Named.Token))" } else { '' }
        Write-Host ("  {0} {1}:{2}  {3} {4}{5}: {6}" -f $labels[$rec.Status], $rec.Source, $rec.Line, $rec.Kind, $rec.Value, $named, $rec.Detail)
    }
    for ($k = 0; $k -lt $Explain.Count; $k++) {
        if (-not $usedExplain.Contains($k) -and -not $TokenDir -and ($TopicPath -or $Explain[$k].Source -ne 'topic')) {
            Write-Host "  note: explain entry $($Explain[$k].Source) $($Explain[$k].Kind) $($Explain[$k].Value) matched nothing; delete it"
        }
    }
    $counts = @{}
    foreach ($s in 'found', 'fallback', 'explained', 'miss') { $counts[$s] = @($records | Where-Object { $_.Status -eq $s }).Count }
    foreach ($src in 'fragment', 'topic') {
        $mine = @($records | Where-Object { $_.Source -eq $src })
        if ($mine.Count -eq 0) { continue }
        Write-Host ("  {0}: {1} value(s): {2} in the tokens, {3} in a fallback document, {4} explained, {5} missed" -f $src, $mine.Count,
            @($mine | Where-Object Status -eq 'found').Count, @($mine | Where-Object Status -eq 'fallback').Count,
            @($mine | Where-Object Status -eq 'explained').Count, @($mine | Where-Object Status -eq 'miss').Count)
    }
    if ($counts['miss'] -gt 0) { Write-Host "FAIL: $($counts['miss']) value(s) missed"; exit 1 }
    Write-Host "OK: every value found or explained ($($records.Count) value(s))"
    exit 0
} catch {
    Write-Host "Compare-SophonDigest: $($_.Exception.Message) (line $($_.InvocationInfo.ScriptLineNumber))"
    exit 1
}
