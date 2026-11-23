# Composed SOUL.md sizes (bytes) of the development family at the 2.1.0 release (tag agents-v2.1.0, the
# packages in tests/agents/fixtures/baseline/SHA256SUMS-2.1.0). Data only, never packaged. Read by
# build/Test-AgentSources.ps1 section E (the change against 2.1.0) and by the README composer
# ({{= SoulTokensDelta}}). An agent without an entry has no baseline. Never edit a value: it records a release.
@{
  Tag = 'agents-v2.1.0'
  Souls = @{
    'accessibility-reviewer' = 22240
    'artifact-creator' = 4853
    'code-reviewer' = 18243
    'debugger' = 31307
    'design-system-engineer' = 32368
    'developer' = 29860
    'e2e-test-engineer' = 32762
    'frontend-developer' = 32745
    'lead-developer' = 42471
    'mcp-integration-engineer' = 32737
    'qa-engineer' = 31915
    'researcher' = 14825
    'security-reviewer' = 19475
    'software-architect' = 18539
    'technical-writer' = 32712
    'ui-ux-designer' = 31915
    'visual-designer' = 32723
  }
}
