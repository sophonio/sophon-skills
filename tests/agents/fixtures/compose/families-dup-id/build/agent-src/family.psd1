# Composer fixture: one family of a two-family registry (build/agent-src/families.psd1).
@{
  Id = 'one'
  FamilyMajor = 2
  FamilyVersion = '2.0.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'development'
  Lead = 'alpha'
  Values = @{
    PlanDir = 'docs/plans'
  }
  AllowedHosts = @('sophon.buildersoft.io', 'marketplace.sophon.buildersoft.io', 'github.com')
  Credits = @{
    superpowers = 'obra/superpowers (MIT, © 2025 Jesse Vincent)'
  }
  Agents = @(
    @{
      Id = 'alpha'
      DisplayName = 'Alpha'
      SoulCap = 2048
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @('01-intro')
      Credits = @('superpowers')
    }
  )
}
