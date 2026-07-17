# Skill integration tests

Offline mock-HTTP integration tests for the skills in `skills/`. No network and no credentials:
`skills/mockhttp.py` patches `urllib` so every HTTP call a skill makes is served from a scripted
response queue while the full request (method, URL, headers, body) is recorded for byte-exact
assertions — auth header composition, token flows, pagination, error surfacing, and
security probes (path-injection quoting, no secret leakage in output).

```bash
# run everything
python tests/skills/run_all.py

# run one skill's tests
python tests/skills/test_okta.py
```

Each `test_<skill>.py` is a plain script (no pytest dependency) that prints `ok/FAIL` lines via
`mockhttp.check()` and exits non-zero on any failure. When adding a skill, add a matching test
file covering: auth exactness, happy-path response shaping, one write-tool body, 401/429 error
paths, and the skill's quirks (see existing files for the pattern).

The sandbox parity smoke (`run_all_container.py`) exercises the unknown-tool and
missing-credential paths inside `python:3.13-alpine` — the image the Sophon runtime actually
uses per tool call:

```bash
docker run --rm --memory=256m -v "<repo>:/repo:ro" \
  python:3.13-alpine python /repo/tests/skills/run_all_container.py
```
