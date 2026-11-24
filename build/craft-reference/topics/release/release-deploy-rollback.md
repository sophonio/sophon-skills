---
id: release-deploy-rollback
summary: Before, Do and After deploy items, health signals, watch loop forms, rollback options with their costs.
reviewed: 2026-11
---
# Deploy and rollback: checklists and health signals

## Before

| Item | Evidence that it holds |
|---|---|
| Checks green on the commit being deployed | the run's commit equals the deploy commit |
| Version and changelog in | the version the artifact will report |
| Migrations reviewed | the old code still runs against the new schema (add first, remove a release later) |
| New settings and variables exist in the target | listed by name, values never shown |
| A way back named | the last good version and where its artifact is kept |
| Baseline taken | error rate and latency of the last hour, written down |
| Stop condition agreed | for example: errors above twice the baseline for two rounds |

## Do

- Quote the exact command and its target environment; staging before production.
- Note the start time and the commit or artifact being deployed.
- Read the pipeline output to its end; a step that stays silent past its usual time is a signal.
- With a phased rollout (canary, percentage, ring), hold at the first step and read the signals.

## After

- The health address answers with success.
- The system reports the new version (a version endpoint, a header, the about page).
- One real request end to end: sign in, the main page, the changed feature.
- Errors and latency against the baseline; new error kinds in the logs.
- Then a bounded watch, and the end time written down.

## Health signals

| Signal | Where | Warning sign |
|---|---|---|
| Health check | the agreed address or command | any failure, or slower than baseline |
| Reported version | version endpoint or header | still the old one: the deploy did not land |
| Error rate | logs, metrics, status codes | above baseline; a new error message |
| Latency | p50 and p95 | p95 up while p50 holds: one slow path |
| Restarts | process or container counts | rising count: a crash loop |
| Queues and jobs | queue depth, failed jobs | depth grows and does not drain |
| Browser | console errors, failed assets | errors only on new pages |

## Watch loop forms

The total timeout is rounds times interval plus 60 seconds. `<url>` is the agreed health address.

bash:
```
for i in 1 2 3 4 5; do date +%T; curl -fsS -o /dev/null -w "%{http_code}\n" <url> || echo fail; [ $i -lt 5 ] && sleep 60; done
```
PowerShell (5.1 and 7):
```
1..5 | ForEach-Object { $c = try { (Invoke-WebRequest <url> -UseBasicParsing -TimeoutSec 10).StatusCode } catch { 'fail' }; "$(Get-Date -Format T) $c"; if ($_ -lt 5) { Start-Sleep 60 } }
```
cmd (`timeout` refuses redirected input, so `ping` waits; `%i` is `%%i` in a batch file):
```
for /L %i in (1,1,5) do @(time /t & curl -fsS -o NUL -w "%{http_code}\n" <url> || echo fail) & ping -n 61 127.0.0.1 >NUL
```

## Rollback options

| Option | Fits when | Cost |
|---|---|---|
| Redeploy the last good artifact | the artifact is kept and the schema is still compatible | minutes; fails after a destructive migration |
| Shift traffic back | blue-green or canary with the old side still running | seconds; needs that old side |
| Turn the feature off by its flag | the change is behind a flag | seconds; the code stays deployed |
| Revert the commits through a pull request | no kept artifact, or the history must show it | a full pipeline run |
| Roll forward with a fix | data or an outside contract already moved | a new change made under pressure |
| Restore data from a backup | data was damaged | loses writes since the backup |

Published packages rarely come back: registries allow a yank or a deprecation at most, so the repair is a new patch version. A mobile store release cannot be withdrawn; halt the phased rollout and ship a new build.

## Keeping the lesson

After the system is stable, keep what the failure taught in the cheapest form that stops a repeat: a check that fails (a test, a pipeline step), then a line in the project's instructions, then a line in the release checklist, then a note. Keep one lesson per incident, and none when the project already teaches it.
