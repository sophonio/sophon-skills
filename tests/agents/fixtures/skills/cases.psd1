# Skill-use fixtures (LINT-SKILL-FRAGMENT, LINT-SKILL-UNUSED, LINT-TOPIC), run by Invoke-AgentSkillUseFixtures in
# build/AgentFamily.psm1 from tests/agents/Test-AgentPackages.ps1 section M. Each case is a small family composed in
# memory: Base supplies SkillPolicy, Topics, Release, Agents and Fragments; a case replaces any of them, merges its
# Fragments over the Base ones and replaces single agent templates through Templates. An agent without a Skills key
# uses every policy skill; Skills = @() uses none. Paths in findings are souls/<id>.md and fragments/soul/<NN-id>.md;
# family-file findings report the path 'family'.
# Expect 'fail' passes when a finding that is not a note carries Rule (and, with Path and Line, at that place);
# 'note' when only notes are found and one carries Rule; 'pass' when nothing but notes is found.
@{
    Base = @{
        SkillPolicy = @{ Skills = @(@{ Name = 'kit'; Fragment = '18-reference-topics'; TopicIndex = 'kit/topics.index.json' }) }
        Topics = @(
            @{ id = 'design-rubric'; usedBy = @('dev'); sections = @('heuristics', 'severity') }
            @{ id = 'eng-checks'; usedBy = @('dev', 'rev'); sections = @('by-class') }
        )
        Release = $false
        Agents = @(
            @{ Id = 'dev'
               Template = @('# Dev', '{{> soul/18-reference-topics}}', 'Scoring sheet: topic `design-rubric`, section `severity`.', 'Checks: topics `eng-checks` and `design-rubric`.', '## Output', 'Report.') }
            @{ Id = 'rev'
               Template = @('# Rev', '{{> soul/18-reference-topics}}', 'Checks by class: topic `eng-checks`.', '## Output', 'Report.') }
            @{ Id = 'maker'; Skills = @()
               Template = @('# Maker', 'Make the file.', '## Output', 'Report.') }
        )
        Fragments = @{
            '18-reference-topics' = @('## Reference topics', 'Call kit.read with a topic id for long tables.', 'If the tool is missing or refused, work from what you carry.')
        }
    }
    Cases = @(
        # ---- pass ----
        @{ Name = 'the base family passes every skill-use check'; Expect = 'pass' }
        @{ Name = 'the base family passes under the release switch too'; Expect = 'pass'; Release = $true }
        @{ Name = 'a family without SkillPolicy is inert'; Expect = 'pass'; SkillPolicy = $null
           Templates = @{ dev = @('# Dev', '## Output', 'Report.'); rev = @('# Rev', '## Output', 'Report.') } }
        @{ Name = 'a policy skill without Fragment or TopicIndex checks only LINT-SKILL-UNUSED'; Expect = 'pass'
           SkillPolicy = @{ Skills = @(@{ Name = 'kit' }) }
           Templates = @{ dev = @('# Dev', '## Output', 'Report.'); rev = @('# Rev', '## Output', 'Report.') } }

        # ---- LINT-SKILL-FRAGMENT ----
        @{ Name = 'an agent that uses the skill without its fragment fails'; Expect = 'fail'; Rule = 'LINT-SKILL-FRAGMENT'; Path = 'family'
           Templates = @{ rev = @('# Rev', 'Checks by class: topic `eng-checks`.', '## Output', 'Report.') } }
        @{ Name = 'an agent that opts out but includes the fragment fails'; Expect = 'fail'; Rule = 'LINT-SKILL-FRAGMENT'; Path = 'family'
           Templates = @{ maker = @('# Maker', '{{> soul/18-reference-topics}}', '## Output', 'Report.') } }

        # ---- LINT-SKILL-UNUSED ----
        @{ Name = 'a policy skill no agent uses fails'; Expect = 'fail'; Rule = 'LINT-SKILL-UNUSED'; Path = 'family'
           Agents = @(@{ Id = 'maker'; Skills = @(); Template = @('# Maker', '## Output', 'Report.') }) }

        # ---- LINT-TOPIC ----
        @{ Name = 'an unknown topic id fails at its source line'; Expect = 'fail'; Rule = 'LINT-TOPIC'; Path = 'souls/rev.md'; Line = 3
           Templates = @{ rev = @('# Rev', '{{> soul/18-reference-topics}}', 'Checks by class: topic `eng-checks` or `eng-nothing`.', '## Output', 'Report.') } }
        @{ Name = 'an unknown section id fails'; Expect = 'fail'; Rule = 'LINT-TOPIC'; Path = 'souls/rev.md'; Line = 3
           Templates = @{ rev = @('# Rev', '{{> soul/18-reference-topics}}', 'Checks: topic `eng-checks`, section `nope`.', '## Output', 'Report.') } }
        @{ Name = 'a pointer in an opted-out agent fails'; Expect = 'fail'; Rule = 'LINT-TOPIC'; Path = 'souls/maker.md'; Line = 2
           Templates = @{ maker = @('# Maker', 'Rubric: topic `design-rubric`.', '## Output', 'Report.') } }
        @{ Name = 'a pointer in a shared fragment counts for every agent that includes it'; Expect = 'pass'
           Fragments = @{ '18-reference-topics' = @('## Reference topics', 'Call kit.read with a topic id for long tables.', 'Checks: topic `eng-checks`.', 'If the tool is missing or refused, work from what you carry.') }
           Templates = @{ rev = @('# Rev', '{{> soul/18-reference-topics}}', '## Output', 'Report.') }
           Topics = @(
               @{ id = 'design-rubric'; usedBy = @('dev'); sections = @('heuristics', 'severity') }
               @{ id = 'eng-checks'; usedBy = @('dev', 'rev'); sections = @('by-class') }
           ) }
        @{ Name = 'a skill user that names no topic is a note before release'; Expect = 'note'; Rule = 'LINT-TOPIC'
           Templates = @{ rev = @('# Rev', '{{> soul/18-reference-topics}}', '## Output', 'Report.') } }
        @{ Name = 'a skill user that names no topic fails under release'; Expect = 'fail'; Rule = 'LINT-TOPIC'; Path = 'family'; Release = $true
           Templates = @{ rev = @('# Rev', '{{> soul/18-reference-topics}}', '## Output', 'Report.') } }
        @{ Name = 'users that differ from usedBy are a note before release'; Expect = 'note'; Rule = 'LINT-TOPIC'
           Topics = @(
               @{ id = 'design-rubric'; usedBy = @('dev', 'rev'); sections = @('heuristics', 'severity') }
               @{ id = 'eng-checks'; usedBy = @('dev', 'rev'); sections = @('by-class') }
           ) }
        @{ Name = 'users that differ from usedBy fail under release'; Expect = 'fail'; Rule = 'LINT-TOPIC'; Path = 'kit/topics.index.json'; Release = $true
           Topics = @(
               @{ id = 'design-rubric'; usedBy = @('dev'); sections = @('heuristics', 'severity') }
               @{ id = 'eng-checks'; usedBy = @('rev'); sections = @('by-class') }
           ) }
        @{ Name = 'the word topic without a backticked id is not a pointer'; Expect = 'pass'
           Templates = @{ maker = @('# Maker', 'Pick a topic for the post; call it {topic:"x"}.', '## Output', 'Report.') } }
    )
}
