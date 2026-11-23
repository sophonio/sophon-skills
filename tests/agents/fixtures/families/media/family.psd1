# Test fixture (tests/agents/Test-AgentPackages.ps1 section L): a second family with a skill policy.
# Data only: loaded with Import-PowerShellDataFile.
@{
  Id = 'media'
  FamilyMajor = 1
  FamilyVersion = '1.0.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'ai'
  RequiredTag = 'media'
  Lead = 'media-maker'
  ReadmeCaps = @{ Lead = 12288; Other = 12288 }
  SkillPolicy = @{
    Skills = @(
      @{ Name = 'media-kit'; MinVersion = '1.0.0' }
    )
    ExtraRequiredTools = @('media.video')
  }
  AllowRestrictedMentions = @('message.send')
  Values = @{
    SkillName = 'media-kit'
  }
  AllowedHosts = @(
    'sophon.buildersoft.io',
    'marketplace.sophon.buildersoft.io',
    'github.com'
  )
  Credits = @{
    mediakit = 'example/media-kit (MIT)'
  }
  Agents = @(
    @{
      Id = 'media-maker'
      DisplayName = 'Media Maker'
      SoulCap = 8192
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-media-rules'
      )
      Credits = @('mediakit')
    }
  )
}
