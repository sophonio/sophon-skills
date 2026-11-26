# Science family: isolated roster and policy for agents/<id>/.
@{
  Id = 'science'
  FamilyMajor = 1
  FamilyVersion = '1.0.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'ai'
  RequiredTag = 'science'
  Lead = 'science-lead'
  ReadmeCaps = @{ Lead = 12288; Other = 12288 }
  SkillPolicy = @{
    Skills = @(
      @{ Name = 'science-evidence'; MinVersion = '1.0.0' }
      @{ Name = 'science-literature'; MinVersion = '1.0.0' }
      @{ Name = 'science-statistics'; MinVersion = '1.0.0' }
    )
    ExtraRequiredTools = @()
  }
  Values = @{}
  AllowedHosts = @(
    'sophon.buildersoft.io',
    'marketplace.sophon.buildersoft.io',
    'github.com'
  )
  Credits = @{}
  Agents = @(
    @{
      Id = 'science-lead'
      DisplayName = 'Science Lead'
      SoulCap = 24576
      RoleCap = 8192
      Writer = $true
      SubAgents = @{ enabled = $true; maxDepth = 1 }
      Effort = 'default'
      Fragments = @(
        '01-science-ground-rules',
        '02-science-evidence',
        '03-science-data',
        '04-science-delegated',
        '05-science-reporting'
      )
      Credits = @()
    }
    @{
      Id = 'literature-researcher'
      DisplayName = 'Literature Researcher'
      SoulCap = 16384
      RoleCap = 4096
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Skills = @('science-evidence', 'science-literature')
      Fragments = @(
        '01-science-ground-rules',
        '02-science-evidence',
        '03-science-data',
        '04-science-delegated',
        '05-science-reporting'
      )
      Credits = @()
    }
    @{
      Id = 'scientific-analyst'
      DisplayName = 'Scientific Analyst'
      SoulCap = 16384
      RoleCap = 4096
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Skills = @('science-evidence', 'science-statistics')
      Fragments = @(
        '01-science-ground-rules',
        '02-science-evidence',
        '03-science-data',
        '04-science-delegated',
        '05-science-reporting'
      )
      Credits = @()
    }
    @{
      Id = 'scientific-reviewer'
      DisplayName = 'Scientific Reviewer'
      SoulCap = 16384
      RoleCap = 4096
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-science-ground-rules',
        '02-science-evidence',
        '03-science-data',
        '04-science-delegated',
        '05-science-reporting'
      )
      Credits = @()
    }
  )
}
