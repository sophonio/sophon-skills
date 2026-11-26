# Anchors of the science family (docs/plans/2026-11-26-sophon-science-design.md).
# Read by build/Test-AgentSources.ps1, section M (Test-AgentAnchors in build/AgentFamily.psm1). The format is the one
# described in tests/agents/fixtures/anchors/development.psd1.
@{
  Anchors = @(
    # Evidence and safety wording every science agent keeps
    @{ Text = 'tool-reported'; In = 'all' }
    @{ Text = 'not authentication'; In = 'all' }
    @{ Text = 'not for clinical'; In = 'all' }
    # Delegated-mode result block
    @{ Text = 'STATUS: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT'; In = 'all' }
    # The statistical unit must be stated before any calculation
    @{ Text = 'experimental unit'; In = @('science-lead', 'scientific-analyst', 'scientific-reviewer') }
  )
  Removed = @()
  Gone = @()
}
