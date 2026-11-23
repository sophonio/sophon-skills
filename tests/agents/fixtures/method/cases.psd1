# Method registry fixtures (METHOD-CONTROLLER, METHOD-EXCUSES, METHOD-REFERENCE), run by Invoke-AgentMethodFixtures in
# build/AgentFamily.psm1 from tests/agents/Test-AgentPackages.ps1 section M. Each case is a small family composed in
# memory: Base supplies Method, SkillPolicy, SkillTools, Agents and Fragments; a case replaces any of them, merges its
# Fragments over the Base ones and replaces single agent templates through Templates. Paths in findings are
# souls/<id>.md and fragments/soul/<NN-id>.md; family-file findings report the path 'family'.
# Expect 'fail' passes when a finding carries Rule (and, with Path and Line, at that place); 'pass' when there is none.
@{
    Base = @{
        Method = @{
            Controller = @{
                Fragments = @('08x-dispatch')
                Terms = @('\bagent\.delegate\b', '\bwaves?\b', '\bstand-ins?\b', '\bfan(?:s|ned|ning)? out\b', '\btasks\[')
                Allow = @(
                    @{ Fragment = '03a-care-writer'; Term = '\bagent\.delegate\b'; Why = 'its card list names every gated tool' }
                )
            }
            Worker = @{
                Fragments = @('01-delegated-mode', '14-no-delegation')
                Exempt = @('maker')
            }
            Rules = @(
                @{ Id = 'test-first'; Fragment = '09b-test-first' }
                @{ Id = 'root-cause'; Agent = 'dbg'; Anchor = '## Root cause first' }
            )
        }
        SkillPolicy = @{ Skills = @(@{ Name = 'kit'; Fragment = '18-reference-topics' }) }
        SkillTools = @{ kit = @('kit.read', 'kit.topics') }
        Agents = @(
            @{ Id = 'lead'; SubAgents = @{ enabled = $true; maxDepth = 1 }
               Template = @('# Lead', '{{> soul/01-delegated-mode}}', '{{> soul/03a-care-writer}}', '{{> soul/08x-dispatch}}', '## Output', 'Report the result.') }
            @{ Id = 'dev'; SubAgents = @{ enabled = $false; maxDepth = 0 }
               Template = @('# Dev', '{{> soul/01-delegated-mode}}', '{{> soul/03a-care-writer}}', '{{> soul/09b-test-first}}', '{{> soul/14-no-delegation}}', '{{> soul/18-reference-topics}}', '## Output', 'Report the result.') }
            @{ Id = 'dbg'; SubAgents = @{ enabled = $false; maxDepth = 0 }
               Template = @('# Dbg', '{{> soul/01-delegated-mode}}', '{{> soul/14-no-delegation}}', '## Root cause first', 'No fix before one red run of the symptom.', '',
                            '| Excuse | Reality |', '|---|---|', '| "The cause is obvious." | Then the loop takes a minute. |', '| "There is no time." | A fix without a red run is a guess. |', '| "A retry hides it." | It hides the report, not the defect. |',
                            '', '## Output', 'Report the cause.') }
            @{ Id = 'maker'; SubAgents = @{ enabled = $false; maxDepth = 0 }
               Template = @('# Maker', '## Output', 'Report the file.') }
        )
        Fragments = @{
            '01-delegated-mode' = @('## If you were delegated', 'Work from the brief and answer with the STATUS block.')
            '03a-care-writer' = @('## Approvals and care', 'Cards show for fs.write, os.execute and agent.delegate calls.')
            '08x-dispatch' = @('## Dispatch', 'Start the implementers in waves with agent.delegate.')
            '09b-test-first' = @('## Test first', 'Write the failing test before the code.', '',
                                 '| Excuse | Reality |', '|---|---|', '| "It is too small to test." | Small code breaks too. |', '| "I will test after." | A test written after passes for the wrong reason. |', '| "The suite is slow." | Run the one test. |')
            '14-no-delegation' = @('## Sub-agents', 'You run no sub-agents; there is no agent.delegate for you.')
            '18-reference-topics' = @('## Reference topics', 'Call kit.read with a topic id for long tables.', 'If the tool is missing or refused, work from what you carry.')
        }
    }
    Cases = @(
        # ---- pass ----
        @{ Name = 'the base family passes every method check'; Expect = 'pass' }
        @{ Name = 'a controller term on a negated worker line passes'; Expect = 'pass'
           Templates = @{ maker = @('# Maker', 'You never fan out work.', '## Output', 'Report the file.') } }
        @{ Name = 'a family without Method and without a reference fragment is inert'; Expect = 'pass'
           Method = $null; SkillPolicy = @{ Skills = @(@{ Name = 'kit' }) }
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "x" | y. |') } }

        # ---- METHOD-CONTROLLER ----
        @{ Name = 'a controller term without a negation in a worker fails'; Expect = 'fail'; Rule = 'METHOD-CONTROLLER'; Path = 'souls/dev.md'; Line = 7
           Templates = @{ dev = @('# Dev', '{{> soul/01-delegated-mode}}', '{{> soul/03a-care-writer}}', '{{> soul/09b-test-first}}', '{{> soul/14-no-delegation}}', '{{> soul/18-reference-topics}}', 'Split the work into waves.', '## Output', 'Report the result.') } }
        @{ Name = 'an allowed term fails once its Allow entry is gone'; Expect = 'fail'; Rule = 'METHOD-CONTROLLER'; Path = 'fragments/soul/03a-care-writer.md'; Line = 2
           Method = @{
               Controller = @{ Fragments = @('08x-dispatch'); Terms = @('\bagent\.delegate\b') }
               Worker = @{ Fragments = @('01-delegated-mode', '14-no-delegation'); Exempt = @('maker') }
               Rules = @(@{ Id = 'test-first'; Fragment = '09b-test-first' }, @{ Id = 'root-cause'; Agent = 'dbg'; Anchor = '## Root cause first' })
           } }
        @{ Name = 'a worker that includes a controller fragment fails'; Expect = 'fail'; Rule = 'METHOD-CONTROLLER'; Path = 'family'
           Templates = @{ dev = @('# Dev', '{{> soul/01-delegated-mode}}', '{{> soul/03a-care-writer}}', '{{> soul/08x-dispatch}}', '{{> soul/09b-test-first}}', '{{> soul/14-no-delegation}}', '{{> soul/18-reference-topics}}', '## Output', 'Report the result.') } }
        @{ Name = 'a worker without a worker fragment fails'; Expect = 'fail'; Rule = 'METHOD-CONTROLLER'
           Templates = @{ dbg = @('# Dbg', '{{> soul/01-delegated-mode}}', '## Root cause first', 'No fix before one red run of the symptom.', '',
                                  '| Excuse | Reality |', '|---|---|', '| "The cause is obvious." | Then the loop takes a minute. |', '| "There is no time." | A fix without a red run is a guess. |', '| "A retry hides it." | It hides the report, not the defect. |',
                                  '', '## Output', 'Report the cause.') } }

        # ---- METHOD-EXCUSES ----
        @{ Name = 'a table with 2 rows fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'fragments/soul/09b-test-first.md'
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| "c" | d. |') } }
        @{ Name = 'a table with 7 rows fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'fragments/soul/09b-test-first.md'
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| "c" | d. |', '| "e" | f. |', '| "g" | h. |', '| "i" | j. |', '| "k" | l. |', '| "m" | n. |') } }
        @{ Name = 'an unquoted first cell fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'fragments/soul/09b-test-first.md'; Line = 5
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| c | d. |', '| "e" | f. |') } }
        @{ Name = 'a reality cell without a full stop fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'fragments/soul/09b-test-first.md'; Line = 6
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| "c" | d. |', '| "e" | f |') } }
        @{ Name = 'a row over 200 bytes fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'fragments/soul/09b-test-first.md'; Line = 4
           Fragments = @{ '09b-test-first' = @('## Test first', '| Excuse | Reality |', '|---|---|', '| "This excuse is long on purpose, so that the row passes the two hundred byte limit of the table rule." | And this reality cell is long on purpose as well, to push the whole row well past the two hundred byte limit of a row. |', '| "c" | d. |', '| "e" | f. |') } }
        @{ Name = 'an unregistered excuse table fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'souls/maker.md'; Line = 2
           Templates = @{ maker = @('# Maker', '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| "c" | d. |', '| "e" | f. |', '## Output', 'Report the file.') } }
        @{ Name = 'an anchor found twice fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'souls/dbg.md'
           Templates = @{ dbg = @('# Dbg', '{{> soul/01-delegated-mode}}', '{{> soul/14-no-delegation}}', '## Root cause first', 'No fix before one red run.', '## Root cause first',
                                  '| Excuse | Reality |', '|---|---|', '| "a" | b. |', '| "c" | d. |', '| "e" | f. |', '## Output', 'Report the cause.') } }
        @{ Name = 'an anchor that matches no line fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'souls/dbg.md'
           Templates = @{ dbg = @('# Dbg', '{{> soul/01-delegated-mode}}', '{{> soul/14-no-delegation}}', '## Output', 'Report the cause.') } }
        @{ Name = 'a fragment rule that no agent includes fails'; Expect = 'fail'; Rule = 'METHOD-EXCUSES'; Path = 'family'
           Templates = @{ dev = @('# Dev', '{{> soul/01-delegated-mode}}', '{{> soul/03a-care-writer}}', '{{> soul/14-no-delegation}}', '{{> soul/18-reference-topics}}', '## Output', 'Report the result.') } }

        # ---- METHOD-REFERENCE ----
        @{ Name = 'a skill tool outside the reference fragment fails'; Expect = 'fail'; Rule = 'METHOD-REFERENCE'; Path = 'souls/maker.md'; Line = 2
           Templates = @{ maker = @('# Maker', 'Look the table up with kit.topics first.', '## Output', 'Report the file.') } }
        @{ Name = 'a reference fragment without the fallback sentence fails'; Expect = 'fail'; Rule = 'METHOD-REFERENCE'; Path = 'fragments/soul/18-reference-topics.md'
           Fragments = @{ '18-reference-topics' = @('## Reference topics', 'Call kit.read with a topic id for long tables.') } }
    )
}
