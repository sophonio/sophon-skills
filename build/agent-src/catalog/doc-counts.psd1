# DOC-COUNT data (build/Test-AgentSources.ps1 section N, the repository pass). Data only, never packaged.
# The rule matches a number of 10 or more (digits or words such as "sixteen" or "twenty-one") directly before
# "agents", "packages" or "companions", with at most two qualifiers between them (development,
# development-family, agent, Marketplace, Sophon, `.sophon-agent`), and accepts it when it is a count derived from
# the rosters (all packages, each family roster, each RosterOrder table and the lead's companions in it) or a
# value in Allow. History lists exact phrases that state an older count on purpose; a match inside one is skipped.
# Documents are repository-relative; a '*' in the last segment is a wildcard. A missing document is skipped.
@{
  Documents = @(
    'README.md'
    'CLAUDE.md'
    'CONTRIBUTING.md'
    'docs/AGENTS.md'
    'docs/PUBLISHING.md'
    'tests/README.md'
    'tests/agents/evals/README.md'
    'tests/agents/evals/scenarios.md'
    'build/agent-src/readmes/*.md'
  )
  Allow = @(
    @{ Value = 20; Why = 'the 3.0 lead cap at Medium (20 agents in 10 delegate calls), not a roster count' }
    @{ Value = 44; Why = 'the 3.0 lead cap at Large (44 agents in 22 delegate calls), not a roster count' }
  )
  History = @()
}
