# Buildersoft development family: roster and shared values for agents/<id>/.
# Data only: loaded with Import-PowerShellDataFile, so no [ordered] and no expressions.
# Agents are kept in ordinal order by Id; consumers sort them with an ordinal comparer anyway.
# Fragments is each agent's list of top-level includes, in template order; the composer
# (build/Compose-AgentSouls.ps1) fails when a template's includes differ from it.
# Values are substituted for {{= Key}} in templates and fragments; never write them literally.
# SoulCap: lead 43008, writers 32768, ARC/CR/SEC 22528, RES 18432. The design set 36864/28672 for the lead and writers on an
# estimate of 17.5 KB of shared writer text; the mandated fragments measure about 25 KB, so those two caps were raised to fit
# them with about 1 KiB of headroom instead of cutting the runtime workarounds (design section 11, ruling on issue 3/37/64).
# License: the family default (MIT, the root LICENSE). An agent may set License + LicenseFile together to ship another
# license; the frontend and design agents added in 2.1 are Apache-2.0 because they adapt Apache-2.0 upstream text.
@{
  FamilyMajor = 2
  FamilyVersion = '2.1.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'development'
  Lead = 'lead-developer'
  Values = @{
    CommitTrailer = 'Co-Authored-By: Sophon <noreply@buildersoft.io>'
    PrFooter = '🤖 Generated with [Sophon](https://sophon.buildersoft.io)'
    PlanDir = 'docs/plans'
  }
  AllowedHosts = @(
    'sophon.buildersoft.io',
    'marketplace.sophon.buildersoft.io',
    'github.com'
  )
  Credits = @{
    superpowers = 'obra/superpowers (MIT, © 2025 Jesse Vincent)'
    anthropic = 'Anthropic''s Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0)'
    anthropicSkills = 'Portions adapted from Anthropic''s agent skills, anthropics/skills (Apache-2.0, © 2026 Anthropic, PBC), changed by Buildersoft LLC: rewritten for Sophon tools, with scripts and branding removed'
  }
  Agents = @(
    @{
      Id = 'accessibility-reviewer'
      DisplayName = 'Accessibility Reviewer'
      SoulCap = 22528
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03b-care-reader',
        '04-scope',
        '05-asking',
        '06-todo',
        '09-quality-inline',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'code-reviewer'
      DisplayName = 'Code Reviewer'
      SoulCap = 22528
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03b-care-reader',
        '04-scope',
        '05-asking',
        '06-todo',
        '09-quality-inline',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'debugger'
      DisplayName = 'Debugger'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'design-system-engineer'
      DisplayName = 'Design System Engineer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'developer'
      DisplayName = 'Developer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'e2e-test-engineer'
      DisplayName = 'E2E Test Engineer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'frontend-developer'
      DisplayName = 'Frontend Developer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'lead-developer'
      DisplayName = 'Lead Developer'
      SoulCap = 43008
      Writer = $true
      SubAgents = @{ enabled = $true; maxDepth = 1 }
      Effort = 'high'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '09-quality-inline',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'mcp-integration-engineer'
      DisplayName = 'MCP Integration Engineer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'qa-engineer'
      DisplayName = 'QA Engineer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'researcher'
      DisplayName = 'Researcher'
      SoulCap = 18432
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03b-care-reader',
        '04-scope',
        '05-asking',
        '06-todo',
        '09-quality-inline',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'security-reviewer'
      DisplayName = 'Security Reviewer'
      SoulCap = 22528
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03b-care-reader',
        '04-scope',
        '05-asking',
        '06-todo',
        '09-quality-inline',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'software-architect'
      DisplayName = 'Software Architect'
      SoulCap = 22528
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03b-care-reader',
        '04-scope',
        '05-asking',
        '06-todo',
        '08a-plan-format',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'technical-writer'
      DisplayName = 'Technical Writer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'ui-ux-designer'
      DisplayName = 'UI/UX Designer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'visual-designer'
      DisplayName = 'Visual Designer'
      SoulCap = 32768
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
      LicenseFile = 'build/agent-src/licenses/Apache-2.0.txt'
      Fragments = @(
        '01-delegated-mode',
        '02-tools-workspace',
        '03a-care-writer',
        '04-scope',
        '05-asking',
        '06-todo',
        '07-sizing',
        '08a-plan-format',
        '08b-plan-run',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
  )
}
