# Media family fixture

A second agent family for `tests/agents/Test-AgentPackages.ps1` section L. The test copies the repository to a
temporary folder, registers this family next to the development family, installs `skill/manifest.json` as
`skills/media-kit/manifest.json` and `agent/` as `agents/media-maker/`, composes the SOUL and runs the source
checks. It exercises a family with one agent, a SkillPolicy (requires.skills, skill-tool pins, an extra
required tool), AllowRestrictedMentions and no attribution values. Nothing here is built or published.

Layout: `family.psd1`, `souls/`, `fragments/soul/` (the family sources), `agent/` (the hand-written package
files) and `skill/` (the skill manifest the policy names).
