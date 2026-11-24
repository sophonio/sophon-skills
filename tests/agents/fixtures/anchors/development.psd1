# Anchors of the development family (docs/plans/2026-11-23-agents-v3-design.md, "Anchors and lost lines").
# Read by build/Test-AgentSources.ps1, section M (Test-AgentAnchors in build/AgentFamily.psm1).
# Seeded from the 2.1.0 composed SOULs and READMEs, and must pass on them unchanged.
#
# Anchors: @{ Text; In; File; Except }. Text is an exact string. In is a set derived from the roster ('all',
#   'writers', 'readers', 'lead') or a list of agent ids; Except removes ids from a set. File is 'SOUL'
#   (default) or 'README'. ANCHOR-MISSING: a listed agent's composed file lacks Text.
# Removed: @{ Text; Why }: an anchor removed or changed on purpose. Move its entry here, and add the same row
#   to the design document's "Changed on purpose" table.
# Gone: @{ Text; File; Since; Pending; Why }: 2.x wording 3.0 replaces. ANCHOR-GONE: an agent's file still
#   carries Text once FamilyVersion is at least Since; before that the entry is counted as pending.
#   Pending = 'M<n>' is the milestone that rewrites the text (M4 sets FamilyVersion 3.0.0 before M5 and M8
#   rewrite it): until then the entry is pending too, and -Release fails while the key remains. Delete the key
#   in the commit that rewrites the text.
#
# New 3.0 strings (the CHANGE and DESIGN keys, "parked", "Merge into", the new verdict words) are added here
# as they land.
@{
  Anchors = @(
    # Runtime strings the SOULs match on
    @{ Text = 'You are a delegated sub-agent.'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'You are a delegated sub-agent working at depth'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'You are executing one step of a larger plan.'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Tool ''<name>'' execution rejected by approval gate.'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'PLAN_MODE'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = '[The user did not respond within 15 minutes.'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Answer: (skipped)'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'You cannot ask the user here.'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Exit Code:'; In = 'writers' }
    @{ Text = 'Command timed out after N seconds.'; In = 'writers' }
    @{ Text = 'Nothing to commit — no staged changes after staging all.'; In = 'writers' }
    @{ Text = 'Note: the user edited this command before approving it; it ran as:'; In = 'writers' }
    @{ Text = 'The user is currently communicating via <x>.'; In = 'all'; Except = @('artifact-creator') }
    # STATUS keys and words
    @{ Text = 'STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'VERDICT:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'SUMMARY:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'FILES_CHANGED:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'COMMANDS_RUN:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'EVIDENCE:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'ASSUMPTIONS:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'OPEN_QUESTIONS:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'NOT_REVIEWED'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'QUALITY_FLOOR'; In = 'all'; Except = @('artifact-creator') }
    # FINDINGS keys, severities and vote words
    @{ Text = 'FINDINGS'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Claim:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'Fails when:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'Fix:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'POSSIBLE:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'NOT_CHECKED:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'Critical'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'researcher', 'security-reviewer') }
    @{ Text = 'Important'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'researcher', 'security-reviewer') }
    @{ Text = 'Minor'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'CONFIRMED | REFUTED'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'REFUTED (unsure)'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'ADDRESSED | NOT_ADDRESSED'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'predates: yes|no'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    # Verdict words: since 3.0 each role states its own (15b no longer lists them); the lead's table is its role text
    @{ Text = 'APPROVE | REQUEST_CHANGES'; In = @('code-reviewer') }
    @{ Text = 'SPEC: MET | GAPS | CANNOT_VERIFY'; In = @('code-reviewer') }
    @{ Text = 'ALL_ADDRESSED | OPEN'; In = @('code-reviewer') }
    @{ Text = 'COMPLETE | GAPS'; In = @('code-reviewer') }
    @{ Text = 'VERDICT CLEAN or ISSUES'; In = @('security-reviewer') }
    @{ Text = 'CONFORMS | GAPS'; In = @('accessibility-reviewer') }
    @{ Text = 'PASS | PASS_WITH_WARNINGS | FAIL'; In = @('qa-engineer') }
    @{ Text = 'ROOT_CAUSE_FOUND | NOT_REPRODUCED | INCONCLUSIVE'; In = @('debugger') }
    @{ Text = 'CONFIRMED | FALSIFIED | INCONCLUSIVE'; In = @('debugger') }
    @{ Text = 'VERDICT READY or NEEDS_DECISION'; In = @('software-architect') }
    @{ Text = 'WINNER <n>'; In = @('ui-ux-designer') }
    # 3.0 findings-block lines (15b-findings-block)
    @{ Text = 'CANNOT_VERIFY:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'DECLINED:'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    # Brief keys
    @{ Text = 'READ_FIRST'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'WRITE_SCOPE'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'CONSTRAINTS'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'ACCEPTANCE'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'MAY_RUN'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'BUDGET'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Task:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Additional instructions:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'CHANGE names the change to read'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'CHANGE "working tree"'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'DESIGN (the design source for UI work)'; In = 'all'; Except = @('artifact-creator') }
    # Consent words and question labels
    @{ Text = '(Recommended)'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Push + open PR (Recommended)'; In = 'writers' }
    @{ Text = 'Keep local'; In = 'writers' }
    @{ Text = 'Keep local'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'technical-writer', 'ui-ux-designer', 'visual-designer'); File = 'README' }
    @{ Text = 'Discard'; In = 'writers' }
    @{ Text = 'Discard'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'technical-writer', 'ui-ux-designer', 'visual-designer'); File = 'README' }
    @{ Text = 'Keep them out of my commits (Recommended)'; In = 'writers' }
    # Attribution
    @{ Text = 'Co-Authored-By: Sophon <noreply@buildersoft.io>'; In = 'writers' }
    @{ Text = 'Co-Authored-By: Sophon <noreply@buildersoft.io>'; In = @('developer', 'lead-developer', 'qa-engineer'); File = 'README' }
    @{ Text = '🤖 Generated with [Sophon](https://sophon.buildersoft.io)'; In = 'writers' }
    @{ Text = '🤖 Generated with [Sophon](https://sophon.buildersoft.io)'; In = 'lead'; File = 'README' }
    # Plan header fields, status values and section names
    @{ Text = '## Plan files'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Status: draft'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Goal'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Context'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Approach'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Out of scope'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Verification'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Orchestration'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Tasks'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '### Task 1: <imperative title>'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Risks'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Progress'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    # 3.0 plan header lines, sections, task lines and the plan word (08a-plan-format)
    @{ Text = 'Spec:'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Discovery:'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Voice:'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Global constraints'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = '## Review focus'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Covers:'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Interfaces:'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'parked'; In = @('debugger', 'design-system-engineer', 'developer', 'e2e-test-engineer', 'frontend-developer', 'lead-developer', 'mcp-integration-engineer', 'qa-engineer', 'software-architect', 'technical-writer', 'ui-ux-designer', 'visual-designer') }
    # Discovery, the design note, the finish menu and voice (07b, 07c, 12b, 16)
    @{ Text = 'just build it'; In = @('design-system-engineer', 'developer', 'frontend-developer', 'lead-developer', 'software-architect', 'ui-ux-designer', 'visual-designer') }
    @{ Text = 'Design note'; In = @('lead-developer', 'software-architect') }
    @{ Text = 'Merge into'; In = 'writers' }
    @{ Text = 'Discard is never on the menu.'; In = 'writers' }
    @{ Text = 'terse'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'caveman'; In = 'all'; Except = @('artifact-creator') }
    # Mode words of every role
    @{ Text = 'MODE is audit | review; at root, review when the request names a change, otherwise audit.'; In = @('accessibility-reviewer') }
    @{ Text = 'MODE is review | refute | re-review | completeness; at root, review unless asked otherwise.'; In = @('code-reviewer') }
    @{ Text = 'MODE in a brief: investigate | hypothesis | fix. At root, a "Live incident" answer adds incident handling.'; In = @('debugger') }
    @{ Text = 'MODE in a brief: audit | tokens | theme | playground | brand-check. Unstated: audit when asked to check, tokens when asked to change.'; In = @('design-system-engineer') }
    @{ Text = 'MODE in a brief: write | visual | flake.'; In = @('e2e-test-engineer') }
    @{ Text = 'MODE in a brief: component | direct | artifact | perf. component is the default when the project has a test runner and behaviour changes.'; In = @('frontend-developer') }
    @{ Text = 'MODE in a brief: design | build | evals.'; In = @('mcp-integration-engineer') }
    @{ Text = '- MODE: codebase | external | both. Both = codebase first, then the web for the version in use.'; In = @('researcher') }
    @{ Text = 'MODE is review | verify; at root, review.'; In = @('security-reviewer') }
    @{ Text = '- MODE: blueprint | adr | greenfield | compare | critique. At root, blueprint unless the user asks for another.'; In = @('software-architect') }
    @{ Text = 'MODE in a brief: draft | edit | reader-test. Docs are the asked-for change here.'; In = @('technical-writer') }
    @{ Text = 'MODE in a brief: direction | build | critique | copy | judge.'; In = @('ui-ux-designer') }
    @{ Text = 'MODE in a brief: concept | art | generative | image | motion. None given: infer it from the request and record a Ruling; as a sub-agent, under ASSUMPTIONS.'; In = @('visual-designer') }
    @{ Text = 'MODE is tdd, direct or debug'; In = @('developer') }
    @{ Text = 'MODE is gate, regression, write-tests, strategy, gaps, ui, perf or probe.'; In = @('qa-engineer') }
    @{ Text = 'ROLE: <role id> · MODE: <a mode from that role''s list> · ACCESS: read-only | write'; In = 'lead' }
    # The lead's controller text (3.0): verdicts it acts on, brief keys, modes from each companion's whenToUse
    @{ Text = '| code-reviewer | `APPROVE` with `SPEC: MET`; `ALL_ADDRESSED`; `COMPLETE` | `REQUEST_CHANGES`; `SPEC: GAPS`; `OPEN`; `GAPS` |'; In = 'lead' }
    @{ Text = 'Any other role: its FINDINGS and SUMMARY decide, not the verdict word.'; In = 'lead' }
    @{ Text = 'CHANGE: <diff file path | "working tree">, reviews only'; In = 'lead' }
    @{ Text = 'DESIGN: <DESIGN.md path | "sophon-default" | "plain">, UI work only'; In = 'lead' }
    @{ Text = 'its when-to-use text ends "Modes: … Brief keys: …"'; In = 'lead' }
  )
  Removed = @(
    @{ Text = 'MODE is gate, regression, write-tests, strategy, gaps or ui.'; Why = 'qa-engineer gains the perf and probe modes in 3.0; every 2.1.0 mode word stays, and the new list is anchored instead' }
    @{ Text = 'CLEAN | ISSUES'; Why = 'the all-roles VERDICT line of 15b-findings-block goes in 3.0; security-reviewer states its words as "VERDICT CLEAN or ISSUES", which is anchored instead' }
    @{ Text = 'READY | NEEDS_DECISION'; Why = 'the all-roles VERDICT line of 15b-findings-block goes in 3.0; software-architect states its words as "VERDICT READY or NEEDS_DECISION", which is anchored instead' }
  )
  Gone = @(
    @{ Text = '<m> deferred'; File = 'SOUL'; Since = '3.0.0'; Why = 'deferred is no longer a plan word in 3.0' }
    @{ Text = '- "Discard": "'; File = 'SOUL'; Since = '3.0.0'; Why = 'Discard is no longer a finish-menu label; it runs only when the user asks for it' }
    @{ Text = 'Ask everything at once'; File = 'SOUL'; Since = '3.0.0'; Why = 'the 3.0 question discipline asks only what is open, one open question per message' }
    @{ Text = 'researcher, developer, UX n/a'; File = 'SOUL'; Since = '3.0.0'; Why = 'the all-roles VERDICT line of 15b-findings-block goes; each role states its own verdict words' }
    @{ Text = 'per the verdict table'; File = 'SOUL'; Since = '3.0.0'; Why = 'code-reviewer states its verdict words in its Output section' }
    @{ Text = 'Modes · role keys:'; File = 'SOUL'; Since = '3.0.0'; Why = 'the lead reads modes and brief keys from each companion''s whenToUse "Modes:" line' }
    @{ Text = 'counts as a v2 install'; File = 'SOUL'; Since = '3.0.0'; Why = 'a local match reports no version, and a missing version counts as current' }
    @{ Text = 'at most 10 agents in 5 delegate calls'; File = 'SOUL'; Since = '3.0.0'; Why = 'the 3.0 lead caps are 20 in 10 and 44 in 22' }
    @{ Text = '[Review panel (Recommended)]'; File = 'SOUL'; Since = '3.0.0'; Why = 'the 3.0 Medium options are Build inline then review, Team per task and Solo' }
    @{ Text = '[Full team (Recommended)]'; File = 'SOUL'; Since = '3.0.0'; Why = 'the 3.0 Large options put Team per task first' }
    @{ Text = 'Never delegate understanding'; File = 'SOUL'; Since = '3.0.0'; Why = 'the Understand gate says it: read the 5-10 key files yourself' }
    @{ Text = 'never os.execute or code.git diff'; File = 'SOUL'; Since = '3.0.0'; Why = 'a child reviewer reads the change CHANGE names, which for "working tree" is one code.git diff call (fragment 11)' }
    @{ Text = '- No fix before a reproduction'; File = 'SOUL'; Since = '3.0.0'; Why = 'the debugger''s Root cause first block (rule root-cause) states it' }
    @{ Text = '- No fixing by suppression'; File = 'SOUL'; Since = '3.0.0'; Why = 'the debugger''s Root cause first block (rule root-cause) states it' }
    @{ Text = '- repeated stale-file refusals;'; File = 'SOUL'; Since = '3.0.0'; Why = 'developer''s ten-item halt list becomes one sentence; 03a-care-writer, 04-scope and 01-delegated-mode carry the shared stop rules' }
    @{ Text = '- Never weaken a test: no added retries'; File = 'SOUL'; Since = '3.0.0'; Why = 'e2e-test-engineer points at Tests that can fail (10c-test-integrity), which makes weakening a test the user''s decision' }
    @{ Text = '- a PLAN_MODE refusal as a child.'; File = 'SOUL'; Since = '3.0.0'; Why = 'developer''s ten-item halt list becomes one sentence; 03a-care-writer, 04-scope and 01-delegated-mode carry the shared stop rules' }
    @{ Text = 'Keep local / Discard menu'; File = 'README'; Since = '3.0.0'; Pending = 'M8'; Why = 'the 3.0 finish menu replaces it' }
    @{ Text = 'Keep local or Discard'; File = 'README'; Since = '3.0.0'; Pending = 'M8'; Why = 'the 3.0 finish menu replaces it' }
    @{ Text = '10 agents in 5 calls'; File = 'README'; Since = '3.0.0'; Pending = 'M8'; Why = 'the 3.0 lead caps replace it' }
    @{ Text = 'a plan of at most 25 lines'; File = 'README'; Since = '3.0.0'; Pending = 'M8'; Why = 'the 3.0 plan format replaces it' }
    @{ Text = 'What''s new in 2.0.0'; File = 'README'; Since = '3.0.0'; Pending = 'M8'; Why = 'the 3.0 upgrade notes replace it' }
  )
}