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
# (software-architect, code-reviewer, security-reviewer, accessibility-reviewer, product-manager, product-owner)
# 28672; researcher and artifact-creator 22528. Each agent keeps at least 5% of its cap free: under 8% free warns
# (BUDGET-HEADROOM), under 5% fails a release build (Test-AgentSources.ps1 -Release), and over the cap always
# fails (BUDGET-SOUL).
# The platform limit is 65536. Raising a cap is a change to this file and this comment only.
# RoleCap (bytes of souls/<id>.md without include and comment lines) is each agent's planned role text from the
# same ledger, rounded up to the next 100; over it fails (BUDGET-ROLE), and -Release requires it of every agent.
# License: the family default (MIT, the root LICENSE). An agent may set License = 'Apache-2.0' (LICENSE copies
# build/licenses/Apache-2.0.txt); the frontend and design agents added in 2.1 are Apache-2.0 because they adapt
# Apache-2.0 upstream text.
# Id, RequiredTag, Category, CreditsSentence and ReadmeCaps are the family keys build/Test-AgentSources.ps1 reads
# (build/agent-src/families.psd1 lists every family; build/AgentFamily.psm1 documents the optional keys).
@{
  Id = 'development'
  FamilyMajor = 3
  FamilyVersion = '3.0.0'
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
    'technical-writer',
    'product-manager',
    'product-owner',
    'release-engineer',
    'agent-engineer'
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
  # Where the tested rules live (docs/plans/2026-11-23-agents-v3-design.md, "The Method registry"): it drives
  # METHOD-CONTROLLER and METHOD-EXCUSES, the control arms (Compose-AgentSouls.ps1 -Omit <rule id>) and the
  # pressure coverage of the scenario lint. Only lead-developer delegates; every other agent but artifact-creator
  # carries the worker contract. An Anchor is a whole source line; the block it starts ends with the last row of
  # the first excuse table after it. The fragment rules arrived in M5; the role-text rules (root-cause,
  # premises-first, split-never-shrink, outward-gate, control-first) arrive in M6 with their text.
  Method = @{
    Controller = @{
      Fragments = @()
      Terms = @('\bagent\.delegate\b', '\bwaves?\b', '\bstand-ins?\b', '\bfan(?:s|ned|ning)? out\b', '\btasks\[')
      Allow = @(
        @{ Fragment = '03a-care-writer'; Term = '\bagent\.delegate\b'; Why = 'its card list names every gated tool' }
      )
    }
    Worker = @{
      Fragments = @('01-delegated-mode', '14-no-delegation')
      Exempt = @('artifact-creator')
    }
    Rules = @(
      @{ Id = 'test-first'; Fragment = '09b-test-first' }
      @{ Id = 'receiving-review'; Fragment = '09c-receiving-review' }
      @{ Id = 'test-integrity'; Fragment = '10c-test-integrity' }
      @{ Id = 'run-evidence'; Fragment = '10a-run-evidence'; Anchor = '- Before you write "should work", "probably", "seems fine" or "done" with no output from this turn behind it, run the check.' }
      @{ Id = 'discovery-gate'; Fragment = '07b-discovery'; Anchor = '6. Write what was agreed into the plan''s Context, Approach and Global constraints. Plan approval is the gate: nothing is built, scaffolded or installed before it, and agreement in chat covers only what you wrote down.' }
      @{ Id = 'root-cause'; Agent = 'debugger'; Anchor = '## Root cause first' }
      @{ Id = 'premises-first'; Agent = 'product-manager'; Anchor = 'No document is drafted before the premises are answered.' }
      @{ Id = 'split-never-shrink'; Agent = 'product-owner'; Anchor = '1. Story 01 is the thinnest path that runs end to end through every layer the requirements touch, even when it does very little.' }
      @{ Id = 'outward-gate'; Agent = 'release-engineer'; Anchor = '## The outward gate' }
      @{ Id = 'control-first'; Agent = 'agent-engineer'; Anchor = '1. Red first. Write the scenario that tempts the failure, and have the control arm run without the new text. A control that does not fail means there is nothing to write: say so and stop.' }
    )
  }
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
    caveman = 'JuliusBrussee/caveman (Apache-2.0, © 2026 Julius Brussee)'
    humanizer = 'blader/humanizer (MIT, © 2025 Siqi Chen)'
    compoundEngineering = 'EveryInc/compound-engineering-plugin (MIT, © 2025 Every)'
    addyosmani = 'addyosmani/agent-skills (MIT, © 2025 Addy Osmani)'
    anthropicSecurityGuidance = 'Anthropic''s security-guidance plugin, anthropics/claude-plugins-official (Apache-2.0)'
    anthropicSecurityReview = 'anthropics/claude-code-security-review (MIT, © 2025 Anthropic)'
    backendDesign = 'sheitabrk/backend-design (MIT, © sheitabrk and contributors)'
    baselineUi = 'baseline-ui from ibelick/ui-skills (MIT, © 2026 Julien Thibeaut)'
    bmadMethod = 'bmad-code-org/BMAD-METHOD (MIT, © 2025 BMad Code, LLC)'
    designMd = 'google-labs-code/design.md (Apache-2.0)'
    emilSkills = 'emilkowalski/skills (MIT, © 2026 Emil Kowalski)'
    gsdCore = 'open-gsd/gsd-core (MIT, © 2026 Open GSD)'
    gstack = 'garrytan/gstack (MIT, © 2026 Garry Tan)'
    impeccable = 'pbakaus/impeccable (Apache-2.0, © 2025 Paul Bakaus)'
    interfaceDesign = 'Dammyjay93/interface-design (MIT, © 2026 Damola Akinleye)'
    mattpocock = 'mattpocock/skills (MIT, © 2026 Matt Pocock)'
    nielsen = 'the names of Jakob Nielsen''s ten usability heuristics (cited by name only)'
    playwright = 'microsoft/playwright (Apache-2.0, portions © Microsoft Corporation and © 2017 Google Inc.)'
    pmSkills = 'phuryn/pm-skills (MIT, © 2026 Pawel Huryn)'
    specKit = 'github/spec-kit (MIT, © GitHub, Inc.)'
    systemDesignSkills = 'proyecto26/system-design-skills (MIT, © 2026 Proyecto 26)'
    tasteSkill = 'Leonxlnx/taste-skill (MIT, © 2026 Leonxlnx)'
    webDesignEngineer = 'web-design-engineer from ConardLi/garden-skills (MIT, © 2026)'
    webInterfaceGuidelines = 'vercel-labs/web-interface-guidelines (MIT, © 2025 Vercel Labs)'
  }
  Agents = @(
    @{
      Id = 'accessibility-reviewer'
      DisplayName = 'Accessibility Reviewer'
      Summary = 'WCAG 2.2 AA: audit / review'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 10000
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
        '25-browser-measure',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman')
    }
    @{
      Id = 'agent-engineer'
      DisplayName = 'Agent Engineer'
      Summary = 'agent instructions: design / rule / test / review / diagnose'
      Changes = 'agent and skill instruction files'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 5500
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '09c-receiving-review',
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
      Credits = @('superpowers', 'anthropic', 'caveman')
    }
    @{
      Id = 'artifact-creator'
      DisplayName = 'Artifact Creator'
      SoulCap = 22528
      RoleCap = 4500
      Writer = $false
      License = 'Apache-2.0'
      Category = 'productivity'
      RequiredTags = @('productivity')
      SubAgents = @{ enabled = $false; maxDepth = 0 }
      Effort = 'default'
      Skills = @()
      Fragments = @('13-data-hygiene', '17-prose-check')
      Credits = @()
    }
    @{
      Id = 'code-reviewer'
      DisplayName = 'Code Reviewer'
      Summary = 'review / refute / re-review / completeness'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 6500
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
        '09d-high-miss',
        '10b-cite-evidence',
        '10c-test-integrity',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'anthropicSecurityGuidance')
    }
    @{
      Id = 'debugger'
      DisplayName = 'Debugger'
      Summary = 'root cause first, then a fix when asked'
      Changes = 'fix + regression test, when asked'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 7100
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
        '08c-plan-card',
        '09b-test-first',
        '09c-receiving-review',
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
      Credits = @('superpowers', 'anthropic', 'caveman', 'mattpocock', 'backendDesign')
    }
    @{
      Id = 'design-system-engineer'
      DisplayName = 'Design System Engineer'
      Summary = 'audit / tokens / theme / playground / brand-check'
      Changes = 'tokens, themes, components'
      Commits = 'yes'
      SoulCap = 51200
      RoleCap = 7500
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '08d-save-document',
        '20-design-source',
        '21-sophon-default',
        '22-design-checks',
        '23-contrast',
        '25-browser-measure',
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
      Credits = @('superpowers', 'anthropic', 'anthropicSkills', 'caveman', 'designMd', 'interfaceDesign', 'emilSkills', 'webDesignEngineer', 'tasteSkill')
    }
    @{
      Id = 'developer'
      DisplayName = 'Developer'
      Summary = 'implementer: tdd / direct / debug'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 4200
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '09-quality-inline',
        '09b-test-first',
        '09c-receiving-review',
        '10a-run-evidence',
        '10d-sources',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'mattpocock', 'addyosmani')
    }
    @{
      Id = 'e2e-test-engineer'
      DisplayName = 'E2E Test Engineer'
      Summary = 'browser end-to-end tests: write / visual / flake'
      Changes = 'e2e tests'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 7400
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
        '08c-plan-card',
        '25-browser-measure',
        '09c-receiving-review',
        '10a-run-evidence',
        '10c-test-integrity',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills', 'caveman', 'playwright')
    }
    @{
      Id = 'frontend-developer'
      DisplayName = 'Frontend Developer'
      Summary = 'UI implementer: component / direct / artifact / perf'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 51200
      RoleCap = 7900
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '20-design-source',
        '21-sophon-default',
        '22-design-checks',
        '25-browser-measure',
        '09b-test-first',
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
      Credits = @('superpowers', 'anthropic', 'anthropicSkills', 'caveman', 'interfaceDesign', 'emilSkills', 'webDesignEngineer', 'tasteSkill', 'webInterfaceGuidelines')
    }
    @{
      Id = 'lead-developer'
      DisplayName = 'Lead Developer'
      Summary = 'orchestrator: sizes, plans, builds, verifies, commits'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 62464
      RoleCap = 19600
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
        '07b-discovery',
        '07c-design-note',
        '20-design-source',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '08d-save-document',
        '09-quality-inline',
        '09b-test-first',
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
      Credits = @('superpowers', 'anthropic', 'caveman', 'compoundEngineering')
    }
    @{
      Id = 'mcp-integration-engineer'
      DisplayName = 'MCP Integration Engineer'
      Summary = 'MCP servers: design / build / evals'
      Changes = 'yes'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 7500
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
        '08c-plan-card',
        '09b-test-first',
        '09c-receiving-review',
        '10a-run-evidence',
        '10d-sources',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'anthropicSkills', 'caveman', 'addyosmani', 'anthropicSecurityGuidance')
    }
    @{
      Id = 'product-manager'
      DisplayName = 'Product Manager'
      Summary = 'discover / analyst / brief / PRD / prioritise / pre-mortem'
      Changes = 'its product documents only'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 6600
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
        '08d-save-document',
        '10b-cite-evidence',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting',
        '17-prose-check'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'humanizer', 'gstack', 'bmadMethod', 'pmSkills')
    }
    @{
      Id = 'product-owner'
      DisplayName = 'Product Owner'
      Summary = 'spec / slice / refine / validate / accept / replan / triage'
      Changes = 'its requirements and story files only'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 7400
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
        '08d-save-document',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting',
        '17-prose-check'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'humanizer', 'bmadMethod', 'specKit', 'mattpocock', 'gsdCore')
    }
    @{
      Id = 'qa-engineer'
      DisplayName = 'QA Engineer'
      Summary = 'verification gate, regression checks, tests'
      Changes = 'tests, when asked'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 7500
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
        '08c-plan-card',
        '09c-receiving-review',
        '10a-run-evidence',
        '10c-test-integrity',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'addyosmani', 'gsdCore')
    }
    @{
      Id = 'release-engineer'
      DisplayName = 'Release Engineer'
      Summary = 'check / ship / deploy / watch / upgrade / rollback'
      Changes = 'version, changelog and dependency files'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 6500
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
        '08c-plan-card',
        '09c-receiving-review',
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
      Credits = @('superpowers', 'anthropic', 'caveman', 'gstack')
    }
    @{
      Id = 'researcher'
      DisplayName = 'Researcher'
      Summary = 'codebase and web facts, every claim cited'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 22528
      RoleCap = 3500
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
        '10d-sources',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'addyosmani')
    }
    @{
      Id = 'security-reviewer'
      DisplayName = 'Security Reviewer'
      Summary = 'exploitable vulnerabilities only'
      Changes = 'no'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 7600
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
        '09d-high-miss',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '15b-findings-block',
        '16-reporting'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'anthropicSecurityGuidance', 'anthropicSecurityReview')
    }
    @{
      Id = 'software-architect'
      DisplayName = 'Software Architect'
      Summary = 'blueprint / ADR / greenfield / compare / critique'
      Changes = 'its plan or ADR file only'
      Commits = 'no'
      SoulCap = 28672
      RoleCap = 5500
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
        '07b-discovery',
        '07c-design-note',
        '08a-plan-format',
        '08d-save-document',
        '10b-cite-evidence',
        '11-git-read',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting',
        '17-prose-check'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'humanizer', 'mattpocock', 'specKit', 'backendDesign', 'systemDesignSkills')
    }
    @{
      Id = 'technical-writer'
      DisplayName = 'Technical Writer'
      Summary = 'documentation: draft / edit / reader-test'
      Changes = 'documentation files'
      Commits = 'yes'
      SoulCap = 44032
      RoleCap = 7500
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
        '08c-plan-card',
        '09c-receiving-review',
        '10a-run-evidence',
        '11-git-read',
        '12a-git-commit',
        '12b-git-finish',
        '13-data-hygiene',
        '18-reference-topics',
        '14-no-delegation',
        '15a-status-block',
        '16-reporting',
        '17-prose-check'
      )
      Credits = @('superpowers', 'anthropic', 'caveman', 'humanizer', 'mattpocock')
    }
    @{
      Id = 'ui-ux-designer'
      DisplayName = 'UI/UX Designer'
      Summary = 'direction / build / critique / copy / judge'
      Changes = 'UI presentation files'
      Commits = 'yes'
      SoulCap = 51200
      RoleCap = 8100
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '08d-save-document',
        '20-design-source',
        '21-sophon-default',
        '22-design-checks',
        '23-contrast',
        '25-browser-measure',
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
      Credits = @('superpowers', 'anthropic', 'caveman', 'impeccable', 'designMd', 'interfaceDesign', 'emilSkills', 'webDesignEngineer', 'tasteSkill', 'nielsen')
    }
    @{
      Id = 'visual-designer'
      DisplayName = 'Visual Designer'
      Summary = 'concept / art / generative / image / motion'
      Changes = 'asset files'
      Commits = 'yes'
      SoulCap = 51200
      RoleCap = 7500
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
        '07b-discovery',
        '08a-plan-format',
        '08b-plan-run',
        '08c-plan-card',
        '20-design-source',
        '21-sophon-default',
        '22-design-checks',
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
      Credits = @('superpowers', 'anthropic', 'anthropicSkills', 'caveman', 'interfaceDesign', 'emilSkills', 'webDesignEngineer', 'tasteSkill')
    }
  )
}
