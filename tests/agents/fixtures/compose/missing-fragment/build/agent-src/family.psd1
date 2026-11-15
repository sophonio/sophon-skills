# Composer fixture: same schema as build/agent-src/family.psd1, tiny roster.
@{
  FamilyMajor = 2
  FamilyVersion = '2.0.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'development'
  Lead = 'alpha'
  Values = @{
    CommitTrailer = 'Co-Authored-By: Sophon <noreply@buildersoft.io>'
    PrFooter = '🤖 Generated with [Sophon](https://sophon.buildersoft.io)'
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
      Writer = $true
      SubAgents = @{ enabled = $true; maxDepth = 1 }
      Effort = 'high'
      Fragments = @('01-intro', '02-more')
      Credits = @('superpowers')
    }
    @{
      Id = 'beta'
      DisplayName = 'Beta'
      SoulCap = 2048
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @('01-intro', '02-more')
      Credits = @('superpowers')
    }
  )
}
