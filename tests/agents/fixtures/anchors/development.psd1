# Anchors of the development family (docs/plans/2026-11-23-agents-v3-design.md, "Anchors and lost lines").
# Read by build/Test-AgentSources.ps1, section M (Test-AgentAnchors in build/AgentFamily.psm1).
# Seeded from the 2.1.0 composed SOULs and READMEs, and must pass on them unchanged.
#
# Anchors: @{ Text; In; File; Except }. Text is an exact string. In is a set derived from the roster ('all',
#   'writers', 'readers', 'lead') or a list of agent ids; Except removes ids from a set. File is 'SOUL'
#   (default) or 'README'. ANCHOR-MISSING: a listed agent's composed file lacks Text.
# Removed: @{ Text; Why }: an anchor removed or changed on purpose. Move its entry here, and add the same row
#   to the design document's "Changed on purpose" table.
# Gone: @{ Text; File; Since; Why }: 2.x wording 3.0 replaces. ANCHOR-GONE: an agent's file still carries
#   Text once FamilyVersion is at least Since; before that the entry is counted as pending.
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
    # Verdict words
    @{ Text = 'APPROVE | REQUEST_CHANGES'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'SPEC: MET | GAPS | CANNOT_VERIFY'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'ALL_ADDRESSED | OPEN'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'COMPLETE | GAPS'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'CLEAN | ISSUES'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'PASS | PASS_WITH_WARNINGS | FAIL'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'qa-engineer', 'security-reviewer') }
    @{ Text = 'ROOT_CAUSE_FOUND | NOT_REPRODUCED | INCONCLUSIVE'; In = @('accessibility-reviewer', 'code-reviewer', 'debugger', 'lead-developer', 'security-reviewer') }
    @{ Text = 'CONFIRMED | FALSIFIED | INCONCLUSIVE'; In = @('accessibility-reviewer', 'code-reviewer', 'debugger', 'lead-developer', 'security-reviewer') }
    @{ Text = 'READY | NEEDS_DECISION'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer') }
    @{ Text = 'WINNER <n>'; In = @('accessibility-reviewer', 'code-reviewer', 'lead-developer', 'security-reviewer', 'ui-ux-designer') }
    # Brief keys
    @{ Text = 'READ_FIRST'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'WRITE_SCOPE'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'CONSTRAINTS'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'ACCEPTANCE'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'MAY_RUN'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'BUDGET'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Task:'; In = 'all'; Except = @('artifact-creator') }
    @{ Text = 'Additional instructions:'; In = 'all'; Except = @('artifact-creator') }
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
    @{ Text = 'MODE is gate, regression, write-tests, strategy, gaps or ui.'; In = @('qa-engineer') }
    @{ Text = 'ROLE: <role id> · MODE: <a mode from that role''s list> · ACCESS: read-only | write'; In = 'lead' }
  )
  Removed = @()
  Gone = @(
    @{ Text = '<m> deferred'; File = 'SOUL'; Since = '3.0.0'; Why = 'deferred is no longer a plan word in 3.0' }
    @{ Text = 'Keep local / Discard menu'; File = 'README'; Since = '3.0.0'; Why = 'the 3.0 finish menu replaces it' }
    @{ Text = 'Keep local or Discard'; File = 'README'; Since = '3.0.0'; Why = 'the 3.0 finish menu replaces it' }
    @{ Text = '10 agents in 5 calls'; File = 'README'; Since = '3.0.0'; Why = 'the 3.0 lead caps replace it' }
    @{ Text = 'a plan of at most 25 lines'; File = 'README'; Since = '3.0.0'; Why = 'the 3.0 plan format replaces it' }
    @{ Text = 'What''s new in 2.0.0'; File = 'README'; Since = '3.0.0'; Why = 'the 3.0 upgrade notes replace it' }
  )
}