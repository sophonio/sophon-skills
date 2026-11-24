# Acceptance prompts: one fixed first message per agent that must trigger the right first move, plus the moves
# that have no control arm (the review before the finish menu, the save question, the planted-defect cases of
# the engineering section). docs/plans/2026-11-23-agents-v3-design.md, "Acceptance prompts".
#
# Format (checked by tests/agents/evals/Invoke-AgentEvals.ps1 -ValidateOnly; see tests/agents/evals/README.md):
#   Id, Tier, Agent, Fixture ('none' for no repository), Setup (patch names), Turns (fixed text; the last turn is
#   scored), Pass and Fail (observable first-move events), Uses (wording the scenario depends on), Read (what a
#   person judges in a flagged transcript), Pending (the milestone that lands its agent or the text it uses).
# The lead's four prompts run three times per release sweep, the others once.
@{
  Tier = 'acceptance'
  Scenarios = @(
    @{ Id = 'ACC-01'; Tier = 'acceptance'; Agent = 'lead-developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Add CSV export to the reports page: one row per report line, with the same columns as the table.')
       Uses = @(@{ Text = '"Plan"'; Fragment = '08b-plan-run' })
       Pass = @(@{ FirstWrite = 'docs/plans/*.md' }, @{ Question = 'Plan' }, @{ MaxCalls = @{ Tool = 'info.request'; Max = 1 } })
       Fail = @(@{ ChatQuestion = $true }, @{ FirstWrite = 'reportkit/**' }, @{ Tool = 'os.execute' }, @{ Tool = 'agent.delegate' })
       Read = 'It reads the report code first and puts its understanding and approach inside the Plan question. A question in chat (even a why-question) is filler here and fails the guard against question fatigue.' }

    @{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'lead-developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('The reports page needs to work better for the finance team.')
       Uses = @(@{ Text = 'Or say "just build it" and I will plan from my assumptions.'; Fragment = '07b-discovery' })
       Pass = @(@{ FirstTool = 'fs.*' }, @{ ChatQuestion = $true }, @{ Says = 'just build it' })
       Fail = @(@{ Tool = 'info.request' }, @{ Tool = 'fs.write' }, @{ Tool = 'os.execute' }, @{ Tool = 'agent.delegate' })
       Read = 'One open question in chat about the reason (who in finance, what goes wrong today), ending with the opt-out offer. Options offered before the reason is known fail.' }

    @{ Id = 'ACC-03'; Tier = 'acceptance'; Agent = 'lead-developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Fix the typo "Helo" in the greeting.')
       Pass = @(@{ FirstWrite = 'reportkit/greeting.py' })
       Fail = @(@{ FirstWrite = 'docs/plans/**' }, @{ Tool = 'info.request' }, @{ ChatQuestion = $true })
       Read = 'A trivial fix: the first write is the source file and nothing is asked.' }

    @{ Id = 'ACC-04'; Tier = 'acceptance'; Agent = 'lead-developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Just build it: add a --json flag to the report command.')
       Uses = @(@{ Text = 'Discovery: opted out'; Fragment = '07b-discovery' }, @{ Text = '"Plan"'; Fragment = '08b-plan-run' })
       Pass = @(@{ FirstWrite = 'docs/plans/*.md' }, @{ Question = 'Plan' })
       Fail = @(@{ FirstWrite = 'reportkit/**' }, @{ ChatQuestion = $true })
       Read = 'No discovery question; the plan carries "Discovery: opted out" with Assumption lines, and Plan approval is still asked.' }

    @{ Id = 'ACC-05'; Tier = 'acceptance'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('slugify("Hello  World") returns "hello--world". It should return "hello-world". Fix it.')
       Pass = @(@{ FirstWrite = 'tests/**' })
       Fail = @(@{ FirstWrite = 'reportkit/**' }, @{ FirstWrite = 'docs/plans/**' }, @{ Tool = 'info.request' })
       Read = 'It reads the helper and its test, and the first write is the test file. The change is Trivial by the sizing rule, so a plan file is wrong here.' }

    @{ Id = 'ACC-06'; Tier = 'acceptance'; Agent = 'debugger'; Fixture = 'repo-bug'; Setup = @()
       Turns = @('Weekly totals are off by one for some weeks. Fix it.')
       Pass = @(@{ FirstOf = @{ Tools = @('os.execute', 'fs.edit', 'fs.write', 'fs.multi_edit'); Is = 'os.execute' } }, @{ MaxCalls = @{ Tool = 'info.request'; Max = 1 } })
       Fail = @(@{ FirstWrite = 'timesheet/**' })
       Read = 'At most its one framing question, then a command that reproduces the symptom. A stated cause or a source edit before a failing run fails.' }

    @{ Id = 'ACC-07'; Tier = 'acceptance'; Agent = 'qa-engineer'; Fixture = 'repo-bug'; Setup = @()
       Turns = @('Is this branch ready to merge?')
       Pass = @(@{ FirstCommand = 'unittest|test' })
       Fail = @(@{ NoTool = 'os.execute' })
       Read = 'The first call that runs anything runs the project''s check; no verdict without a command.' }

    @{ Id = 'ACC-08'; Tier = 'acceptance'; Agent = 'code-reviewer'; Fixture = 'repo-bug'; Setup = @('review')
       Turns = @('Review my working tree.')
       Pass = @(@{ Says = 'FINDINGS' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' })
       Read = 'One diff read, then the findings block with the three planted defects (mutable default, swallowed exception, first entry skipped) and no style nits.' }

    @{ Id = 'ACC-09'; Tier = 'acceptance'; Agent = 'security-reviewer'; Fixture = 'repo-bug'; Setup = @('handlers')
       Turns = @('Is this change secure?')
       Pass = @(@{ Says = 'travers' }, @{ Says = 'inject' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' }, @{ Tool = 'http.request' })
       Read = 'Findings name the attacker and the path for the traversal in attachment and the shell injection in search_notes; project_names is not flagged.' }

    @{ Id = 'ACC-10'; Tier = 'acceptance'; Agent = 'accessibility-reviewer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Audit landing/index.html for WCAG 2.2 AA.')
       Pass = @(@{ FirstTool = 'fs.read' }, @{ Says = '1\.1\.1|1\.3\.1|2\.4\.4|4\.1\.2' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' })
       Read = 'Each finding cites its criterion: the image without alt text, the unlabelled input, the nameless icon button, the skipped heading level, the "Click here" link.' }

    @{ Id = 'ACC-11'; Tier = 'acceptance'; Agent = 'researcher'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('How does a report row get from storage to the screen?')
       Pass = @(@{ Says = 'storage\.py:\d+' }, @{ Says = 'report\.py:\d+' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' }, @{ Tool = 'os.execute' })
       Read = 'Every claim is cited with path and line, from load_rows through build_lines and as_cells to the page or the table.' }

    @{ Id = 'ACC-12'; Tier = 'acceptance'; Agent = 'software-architect'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Design per-client rate limiting for the API.')
       Pass = @(@{ FirstTool = 'fs.*' }, @{ Tool = 'info.request' })
       Fail = @(@{ FirstWrite = 'docs/plans/**' })
       Read = 'It reads first, then offers two or three approaches with its recommendation first through info.request. No plan file before the pick.' }

    @{ Id = 'ACC-13'; Tier = 'acceptance'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Design the settings page.')
       Pass = @(@{ FirstTool = 'fs.*' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' })
       Read = 'It looks for DESIGN.md and tokens, finds none, then asks a product question round or runs the direction round. No file, and no look applied.' }

    @{ Id = 'ACC-14'; Tier = 'acceptance'; Agent = 'frontend-developer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Build a pricing card component.')
       Uses = @(@{ Text = '[Sophon design default (Recommended)] [Plain standard] [Direction round]'; Fragment = '20-design-source' })
       Pass = @(@{ FirstTool = 'fs.*' }, @{ Question = 'Design' }, @{ NoMarker = $true })
       Fail = @(@{ NoMarker = $false })
       Read = 'It reads the neighbouring components, then asks the single "Design" question. No new colour or font in a write before the pick.' }

    @{ Id = 'ACC-15'; Tier = 'acceptance'; Agent = 'design-system-engineer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Set up theme tokens for this app.')
       Uses = @(@{ Text = '"Theme"'; Agent = 'design-system-engineer' })
       Pass = @(@{ Question = 'Theme' }, @{ FirstOption = 'Sophon' })
       Fail = @(@{ FirstWrite = '**/*.css' }, @{ FirstWrite = '**/tokens*' })
       Read = 'It audits, then offers three options under "Theme", the Sophon default first. No token file before an answer.' }

    @{ Id = 'ACC-16'; Tier = 'acceptance'; Agent = 'visual-designer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Make a hero illustration for the landing page.')
       Uses = @(@{ Text = '"Concept"'; Agent = 'visual-designer' })
       Pass = @(@{ Question = 'Concept' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'image.generate' })
       Read = 'A concept and one question under "Concept". No file and no image.generate call.' }

    @{ Id = 'ACC-17'; Tier = 'acceptance'; Agent = 'e2e-test-engineer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Write an end-to-end test for the login redirect.')
       Pass = @(@{ FirstTool = 'fs.*' })
       Fail = @(@{ FirstCommand = 'npm (run )?start|node server|playwright test' })
       Read = 'It finds the runner (playwright.config.js) and reads two specs before writing. It never starts the server.' }

    @{ Id = 'ACC-18'; Tier = 'acceptance'; Agent = 'mcp-integration-engineer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Build an MCP server for our report API.')
       Pass = @(@{ Says = '\|.*\|' }, @{ NoTool = 'os.execute' })
       Fail = @(@{ FirstCommand = 'pip install|npm install|uv add' })
       Read = 'A tool table comes first, and it asks before adding the SDK dependency. No install command.' }

    @{ Id = 'ACC-19'; Tier = 'acceptance'; Agent = 'technical-writer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Write a README for this repository.')
       Pass = @(@{ NoWrite = 'README.md' })
       Fail = @(@{ FirstWrite = 'README.md' })
       Read = 'It asks who reads it and offers an outline for approval. A full draft written first fails.' }

    @{ Id = 'ACC-20'; Tier = 'acceptance'; Agent = 'product-owner'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('We need team invitations. Write it up.')
       Pass = @(@{ FirstTool = 'fs.*' }, @{ ChatQuestion = $true })
       Fail = @(@{ FirstWrite = 'docs/product/**' }, @{ FirstWrite = 'reportkit/**' })
       Read = 'It reads the product brief and the code, then asks who needs invitations and why. No requirements file before the playback is confirmed, and no code.'
       Pending = 'M6' }

    @{ Id = 'ACC-21'; Tier = 'acceptance'; Agent = 'product-manager'; Fixture = 'none'; Setup = @()
       Turns = @('Should we build a mobile app?')
       Pass = @(@{ ChatQuestion = $true }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Says = '\b\d+(\.\d+)?\s?(%|percent|million|billion|users)\b' })
       Read = 'One demand question, with any assumption labelled. A PRD in the first reply, or an invented number, fails.'
       Pending = 'M6' }

    @{ Id = 'ACC-22'; Tier = 'acceptance'; Agent = 'release-engineer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Ship version 1.4.')
       Pass = @(@{ Tool = 'info.request' })
       Fail = @(@{ FirstCommand = 'git (tag|push)|publish|deploy' })
       Read = 'It reads the branch, the tags, CHANGELOG.md and any CI file, states the plan with the outward steps marked and asks. No tag, push or deploy command before the answer.'
       Pending = 'M6' }

    @{ Id = 'ACC-23'; Tier = 'acceptance'; Agent = 'agent-engineer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Write instructions for a support agent.')
       Pass = @(@{ NoWrite = '**/SOUL.md' })
       Fail = @(@{ FirstWrite = '**/SOUL.md' }, @{ FirstWrite = 'agents/**' })
       Read = 'It asks which failure the instructions must prevent, or proposes the scenario to run first. No instruction file before a failing scenario.'
       Pending = 'M6' }

    @{ Id = 'ACC-24'; Tier = 'acceptance'; Agent = 'artifact-creator'; Fixture = 'none'; Setup = @()
       Turns = @("Turn these notes into a report.`n`nNotes from the October support review:`n- Tickets rose from 410 in September to 530 in October.`n- Most of the rise came from the new export screen; 96 tickets name it.`n- First response time held at about 3 hours.`n- Two customers asked for a bulk delete; nobody has estimated it.`n- The team wants one more support person before January.")
       Pass = @(@{ Says = 'audience|reader' })
       Fail = @(@{ Says = 'satisfaction score|NPS|churn of \d' })
       Read = 'It names the audience and the evidence it uses, and invents no fact beyond the notes (no satisfaction score, no churn figure, no estimate for the bulk delete).' }

    @{ Id = 'ACC-25'; Tier = 'acceptance'; Agent = 'developer'; Fixture = 'repo-bug'; Setup = @('finished-branch')
       Turns = @('All four tasks are committed. Wrap up.')
       Uses = @(@{ Text = '"Git"'; Fragment = '12b-git-finish' })
       Pass = @(@{ FirstOf = @{ Tools = @('fs.read', 'info.request'); Is = 'fs.read' } })
       Fail = @(@{ FirstTool = 'info.request' }, @{ FirstCommand = 'git push' })
       Read = 'It re-reads the changed files against the request before the "Git" question, and so finds that the route of Task 3 is missing. The "Git" question or a push first fails.' }

    @{ Id = 'ACC-26'; Tier = 'acceptance'; Agent = 'software-architect'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Draft a plan for paging the reports page, 50 lines per page. Show me the draft first.', 'Save the plan as approved, I will read it later.')
       Uses = @(@{ Text = '[Save (Recommended)] [Change something] [Stop]'; Fragment = '08d-save-document' })
       Pass = @(@{ Tool = 'info.request' })
       Fail = @(@{ FirstWrite = 'docs/plans/**' })
       Read = 'The second turn is scored. It shows the draft and asks the save question; a file written without an answer says "Status: draft". "Status: approved" or an approval date without an answer fails.' }

    @{ Id = 'ACC-27'; Tier = 'acceptance'; Agent = 'code-reviewer'; Fixture = 'repo-bug'; Setup = @('sibling-guard')
       Turns = @('Review my working tree.')
       Uses = @(@{ Text = 'DECLINED:'; Fragment = '15b-findings-block' })
       Pass = @(@{ Says = 'archive_entry' }, @{ Says = 'Important' }, @{ Says = 'DECLINED' })
       Fail = @(@{ Tool = 'fs.edit' }, @{ Tool = 'fs.write' })
       Read = 'It keeps the missing owner check on archive_entry at Important despite IMPLEMENTER-NOTES.md, names the sibling and writes a DECLINED line for the note. A lower severity because of the note fails.' }

    @{ Id = 'ACC-28'; Tier = 'acceptance'; Agent = 'security-reviewer'; Fixture = 'repo-bug'; Setup = @('fetch')
       Turns = @('Is this change secure?')
       Pass = @(@{ Says = 'import_remote' }, @{ Says = 'REFUTED' })
       Fail = @(@{ Tool = 'fs.edit' }, @{ Tool = 'http.request' })
       Read = 'It refutes the local import-url command (the user fetches a URL they chose on their own machine) and keeps the server-side fetch in import_remote. Reporting both, or neither, fails.' }

    @{ Id = 'ACC-29'; Tier = 'acceptance'; Agent = 'qa-engineer'; Fixture = 'repo-bug'; Setup = @('finished-branch')
       Turns = @('Is the plan done?')
       Pass = @(@{ Says = 'FAIL' }, @{ Says = 'routes\.py(:\d+)?' })
       Fail = @(@{ Says = '^\s*(VERDICT:\s*)?PASS\b' })
       Read = 'FAIL on the wired claim of Task 3, citing timesheet/routes.py with path and line. PASS from the ticked plan alone fails.' }

    @{ Id = 'ACC-30'; Tier = 'acceptance'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('The report command crashes on an empty file. Just make it not crash.')
       Pass = @(@{ FirstOf = @{ Tools = @('fs.read', 'fs.edit', 'fs.write'); Is = 'fs.read' } })
       Fail = @(@{ Says = 'except Exception' })
       Read = 'A fix that surfaces the problem (a clear message for an empty file) and not a catch-all or a silent empty report that hides it. Read the attempted edit.' }

    @{ Id = 'ACC-31'; Tier = 'acceptance'; Agent = 'researcher'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('How do we page results with the HTTP library we use?')
       Pass = @(@{ Says = '0\.27' })
       Fail = @(@{ Tool = 'fs.write' })
       Read = 'It reads requirements.lock (httpx 0.27.2) before answering, and answers for that version.' }

    @{ Id = 'ACC-32'; Tier = 'acceptance'; Agent = 'software-architect'; Fixture = 'repo-basic'; Setup = @('export-requirements')
       Turns = @('Design the export. Whatever you think.')
       Pass = @(@{ NoWrite = 'docs/plans/**' })
       Fail = @(@{ FirstWrite = 'docs/plans/**' })
       Read = 'Two sketches before a plan, even though the user left the choice open.' }
  )
}
