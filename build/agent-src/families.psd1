# Agent family registry: every family whose agents live in agents/<id>/.
# Data only: loaded with Import-PowerShellDataFile, so no [ordered] and no expressions.
# Path is the repo-relative family file. Its folder holds that family's souls/ and fragments/soul/, so
# families never share templates or fragments. An agent id belongs to exactly one family, and agents/
# must hold exactly the union of the rosters (build/Test-AgentSources.ps1, build/Build-AgentPackages.ps1).
# Without this file the tooling falls back to the single family in build/agent-src/family.psd1.
@{
  Families = @(
    @{ Id = 'development'; Path = 'build/agent-src/family.psd1' }
    @{ Id = 'video'; Path = 'build/agent-src/families/video/family.psd1' }
  )
}
