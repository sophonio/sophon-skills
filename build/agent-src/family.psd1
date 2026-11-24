# Buildersoft development family: roster and shared values for agents/<id>/.
# Data only: loaded with Import-PowerShellDataFile, so no [ordered] and no expressions.
# Agents are kept in ordinal order by Id; consumers sort them with an ordinal comparer anyway.
# Fragments is each agent's list of top-level includes, in template order; the composer
# (build/Compose-AgentSouls.ps1) fails when a template's includes differ from it.
# Values are substituted for {{= Key}} in templates and fragments; never write them literally.
# READMEs are generated too: build/agent-src/readmes/<id>.md (plus fragments/readme/) composes agents/<id>/README.md;
# RosterOrder and each agent's Summary, Changes and Commits feed its {{# roster}} table.
# SoulCap (bytes of the composed SOUL.md; data only, not packaged), by tier, option A of the 3.0 ledger
# (docs/plans/2026-11-23-agents-v3-design.md, "Fragment matrix and byte ledger"): lead 62464; design writers
# (ui-ux-designer, frontend-developer, design-system-engineer, visual-designer) 51200; writers 44032; readers
# (software-architect, code-reviewer, security-reviewer, accessibility-reviewer) 28672; researcher and
# artifact-creator 22528. Each agent keeps at least 5% of its cap free: under 8% free warns (BUDGET-HEADROOM),
# under 5% fails a release build (Test-AgentSources.ps1 -Release), and over the cap always fails (BUDGET-SOUL).
# The platform limit is 65536. Raising a cap is a change to this file and this comment only.
# License: the family default (MIT, the root LICENSE). An agent may set License = 'Apache-2.0' (LICENSE copies
# build/licenses/Apache-2.0.txt); the frontend and design agents added in 2.1 are Apache-2.0 because they adapt
# Apache-2.0 upstream text.
# Id, RequiredTag, Category, CreditsSentence and ReadmeCaps are the family keys build/Test-AgentSources.ps1 reads
# (build/agent-src/families.psd1 lists every family; build/AgentFamily.psm1 documents the optional keys).
@{
  Id = 'development'
  FamilyMajor = 2
  FamilyVersion = '2.1.0'
  SophonCli = '^2\.2\.\d+'
  MinSophonVersion = '2.2.0'
  Author = 'Buildersoft LLC'
  License = 'MIT'
  Category = 'development'
  RequiredTag = 'development'
  Lead = 'lead-developer'
  # The README roster table, in table order (Artifact Creator is not in it). DOC-COUNT derives the table and companion
  # counts from it.
  RosterOrder = @(
    'lead-developer',
    'developer',
    'researcher',
    'software-architect',
    'code-reviewer',
    'qa-engineer',
    'debugger',
    'security-reviewer',
    'ui-ux-designer',
    'frontend-developer',
    'design-system-engineer',
    'visual-designer',
    'e2e-test-engineer',
    'accessibility-reviewer',
    'mcp-integration-engineer',
    'technical-writer'
  )
  CreditsSentence = 'Workflow patterns adapted, not copied, from obra/superpowers (MIT, © 2025 Jesse Vincent) and Anthropic''s Claude Code plugins (feature-dev, pr-review-toolkit, code-review, security-review, frontend-design; Apache-2.0).'
  ReadmeCaps = @{ Lead = 24576; Other = 12288 }
  # The optional Marketplace skill craft-reference (skills/craft-reference): every agent but artifact-creator
  # (Skills = @()) uses it, requires it in requires.skills, pins craft.read and includes the reference fragment;
  # its topic ids are checked against TopicIndex (LINT-TOPIC).
  SkillPolicy = @{
    Skills = @(
      @{ Name = 'craft-reference'; MinVersion = '1.0.0'; Fragment = '18-reference-topics'; TopicIndex = 'build/craft-reference/topics.index.json' }
    )
  }
  FragmentCaps = @{ '18-reference-topics' = 450 }
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
      Summary = 'WCAG 2.2 AA: audit / review'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
      Writer = $false
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'high'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'artifact-creator'
      DisplayName = 'Artifact Creator'
      SoulCap = 22528
      Writer = $false
      License = 'Apache-2.0'
      Category = 'productivity'
      RequiredTags = @('productivity')
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Skills = @()
      Fragments = @('13-data-hygiene')
      Credits = @()
    }
    @{
      Id = 'code-reviewer'
      DisplayName = 'Code Reviewer'
      Summary = 'review / refute / re-review / completeness'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
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
        '18-reference-topics',
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
      Summary = 'root cause first, then a fix when asked'
      Changes = 'fix + regression test, when asked'
      Commits = 'yes'
      SoulCap = 44032
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'design-system-engineer'
      DisplayName = 'Design System Engineer'
      Summary = 'audit / tokens / theme / playground / brand-check'
      Changes = 'tokens, themes, components'
      Commits = 'yes'
      SoulCap = 51200
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'developer'
      DisplayName = 'Developer'
      Summary = 'implementer: tdd / direct / debug'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 44032
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'e2e-test-engineer'
      DisplayName = 'E2E Test Engineer'
      Summary = 'browser end-to-end tests: write / visual / flake'
      Changes = 'e2e tests'
      Commits = 'yes'
      SoulCap = 44032
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'frontend-developer'
      DisplayName = 'Frontend Developer'
      Summary = 'UI implementer: component / direct / artifact / perf'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 51200
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'lead-developer'
      DisplayName = 'Lead Developer'
      Summary = 'orchestrator: sizes, plans, builds, verifies, commits'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 62464
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
        '18-reference-topics',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'mcp-integration-engineer'
      DisplayName = 'MCP Integration Engineer'
      Summary = 'MCP servers: design / build / evals'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 44032
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
    @{
      Id = 'qa-engineer'
      DisplayName = 'QA Engineer'
      Summary = 'verification gate, regression checks, tests'
      Changes = 'tests, when asked'
      Commits = 'yes'
      SoulCap = 44032
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'researcher'
      DisplayName = 'Researcher'
      Summary = 'codebase and web facts, every claim cited'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 22528
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'security-reviewer'
      DisplayName = 'Security Reviewer'
      Summary = 'exploitable vulnerabilities only'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
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
        '18-reference-topics',
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
      Summary = 'blueprint / ADR / greenfield / compare / critique'
      Changes = 'its plan or ADR file only'
      Commits = 'no'
      SoulCap = 28672
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'technical-writer'
      DisplayName = 'Technical Writer'
      Summary = 'documentation: draft / edit / reader-test'
      Changes = 'documentation files'
      Commits = 'yes'
      SoulCap = 44032
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'ui-ux-designer'
      DisplayName = 'UI/UX Designer'
      Summary = 'direction / build / critique / copy / judge'
      Changes = 'UI presentation files'
      Commits = 'yes'
      SoulCap = 51200
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic')
    }
    @{
      Id = 'visual-designer'
      DisplayName = 'Visual Designer'
      Summary = 'concept / art / generative / image / motion'
      Changes = 'asset files'
      Commits = 'yes'
      SoulCap = 51200
      Writer = $true
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      License = 'Apache-2.0'
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
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills')
    }
  )
}
