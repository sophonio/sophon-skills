# Cases for the scenario lint (Test-AgentEvalData in tests/agents/evals/AgentEvals.psm1), run by section M of
# tests/agents/Test-AgentPackages.ps1 through Invoke-AgentEvalLintFixtures.
#
# Each case runs Rows as the scenarios of one tier file (Tier, default acceptance; Top adds top-level keys)
# against the small in-memory repository of New-AgentEvalTestContext: agents dev (carries 09b-test-first) and
# lead, family fam without a Method key, fixture repo-x with patch p1 (and gone, whose file is missing), brief
# b.md, and a corpus holding "the quick brown fox jumps over the lazy dog near the river bank today".
# Context replaces keys of that repository. Expect = 'ok' (no error) or @{ Level; Rule; Match }: a finding of
# that level and rule whose message matches Match (for a note, also no error).
@{
  Cases = @(
    @{ Name = 'acceptance-ok'; Expect = 'ok'
       Rows = @(@{ Id = 'ACC-01'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'repo-x'; Setup = @('p1'); Turns = @('Fix the slug.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Read = 'The test comes first.' }) }
    @{ Name = 'pressure-ok-without-method'; Tier = 'pressure'; Expect = @{ Level = 'note'; Rule = 'EVAL-COVERAGE'; Match = 'has no Method key' }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'pragmatic'); Fixture = 'repo-x'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'id-wrong-prefix'; Expect = @{ Level = 'error'; Rule = 'EVAL-ID'; Match = 'must start with ACC-' }
       Rows = @(@{ Id = 'PRS-01'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'id-duplicate'; Expect = @{ Level = 'error'; Rule = 'EVAL-ID'; Match = 'also used' }
       Rows = @(
         @{ Id = 'ACC-01'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }
         @{ Id = 'ACC-01'; Tier = 'acceptance'; Agent = 'lead'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }
       ) }
    @{ Name = 'smoke-duplicate-section'; Expect = @{ Level = 'error'; Rule = 'EVAL-ID'; Match = 'has two sections' }
       Smoke = @(@{ Id = 'L1'; Line = 3; Kind = 'heading' }, @{ Id = 'L1'; Line = 9; Kind = 'heading' }, @{ Id = 'L1'; Line = 1; Kind = 'row' })
       Rows = @() }
    @{ Name = 'smoke-bad-id'; Expect = @{ Level = 'error'; Rule = 'EVAL-ID'; Match = 'letters followed by digits' }
       Smoke = @(@{ Id = 'ACC-01'; Line = 3; Kind = 'heading' })
       Rows = @() }
    @{ Name = 'agent-unknown'; Expect = @{ Level = 'error'; Rule = 'EVAL-AGENT'; Match = "agent 'nobody' is in no roster" }
       Rows = @(@{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'nobody'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'agent-unknown-pending'; Expect = @{ Level = 'note'; Rule = 'EVAL-AGENT'; Match = 'pending M6' }
       Rows = @(@{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'nobody'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x'; Pending = 'M6' }) }
    @{ Name = 'pending-under-release'; Release = $true; Expect = @{ Level = 'error'; Rule = 'EVAL-PENDING'; Match = 'still Pending M6' }
       Rows = @(@{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'nobody'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x'; Pending = 'M6' }) }
    @{ Name = 'pending-resolved'; Expect = @{ Level = 'note'; Rule = 'EVAL-PENDING'; Match = 'can be deleted' }
       Rows = @(@{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x'; Pending = 'M5' }) }
    @{ Name = 'pending-bad-value'; Expect = @{ Level = 'error'; Rule = 'EVAL-PENDING'; Match = 'must be a milestone' }
       Rows = @(@{ Id = 'ACC-02'; Tier = 'acceptance'; Agent = 'nobody'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x'; Pending = 'later' }) }
    @{ Name = 'pressure-two-pressures'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-PRESSURE'; Match = 'exactly three' }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'pressure-unknown-pressure'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-PRESSURE'; Match = 'boredom' }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'boredom'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'pressure-no-control'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-CONTROL'; Match = 'must-fail' }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Read = 'x' }) }
    @{ Name = 'pressure-opt-out-phrase'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-OPTOUT'; Match = 'just build it' }
       Top = @{ OptOut = @{ Uses = @(@{ Text = 'just build it'; Fragment = '07b-discovery' }) } }
       Rows = @(@{ Id = 'PRS-DG1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('No time. Just build it now.'); Pass = @(@{ NoTool = 'fs.edit' }); Fail = @(@{ Tool = 'fs.edit' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'pressure-opt-out-phrase-quoted-text'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-OPTOUT'; Match = "'no questions'" }
       Top = @{ OptOut = @{ Pending = 'M5'; Uses = @(@{ Text = '"no questions"'; Fragment = '07b-discovery' }) } }
       Rows = @(@{ Id = 'PRS-DG1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('No time for this. Build it now, and no questions please.'); Pass = @(@{ NoTool = 'fs.edit' }); Fail = @(@{ Tool = 'fs.edit' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'rule-unregistered'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-RULE'; Match = "'made-up' is not registered" }
       Context = @{ Methods = @{ fam = @{ Rules = @(@{ Id = 'test-first'; Fragment = '09b-test-first' }) } } }
       Rows = @(
         @{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }
         @{ Id = 'PRS-XX1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'made-up'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }
       ) }
    @{ Name = 'rule-unregistered-pending'; Tier = 'pressure'; Expect = @{ Level = 'note'; Rule = 'EVAL-RULE'; Match = 'pending M6' }
       Context = @{ Methods = @{ fam = @{ Rules = @(@{ Id = 'test-first'; Fragment = '09b-test-first' }) } } }
       Rows = @(
         @{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }
         @{ Id = 'PRS-XX1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'made-up'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x'; Pending = 'M6' }
       ) }
    @{ Name = 'rule-not-carried'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-RULE'; Match = 'lead does not carry' }
       Context = @{ Methods = @{ fam = @{ Rules = @(@{ Id = 'test-first'; Fragment = '09b-test-first' }) } } }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'lead'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'rule-carried-in-role-text'; Tier = 'pressure'; Expect = 'ok'
       Context = @{ Methods = @{ fam = @{ Rules = @(@{ Id = 'root-cause'; Agent = 'dev'; Anchor = '## Root cause first' }) } } }
       Rows = @(@{ Id = 'PRS-RC1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'root-cause'; Pressures = @('time', 'economic', 'authority'); Fixture = 'none'; Turns = @('Production is down.'); Pass = @(@{ FirstTool = 'os.execute' }); Fail = @(@{ FirstTool = 'fs.edit' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'rule-without-scenario'; Tier = 'pressure'; Expect = @{ Level = 'error'; Rule = 'EVAL-COVERAGE'; Match = "'receiving-review' of family fam has no pressure scenario" }
       Context = @{ Methods = @{ fam = @{ Rules = @(@{ Id = 'test-first'; Fragment = '09b-test-first' }, @{ Id = 'receiving-review'; Fragment = '09c-receiving-review' }) } } }
       Rows = @(@{ Id = 'PRS-TF1'; Tier = 'pressure'; Agent = 'dev'; Rule = 'test-first'; Pressures = @('time', 'authority', 'social'); Fixture = 'none'; Turns = @('A demo soon.'); Pass = @(@{ FirstWrite = 'tests/**' }); Fail = @(@{ FirstWrite = 'src/**' }); Control = 'must-fail'; Read = 'x' }) }
    @{ Name = 'rule-on-acceptance-row'; Expect = @{ Level = 'error'; Rule = 'EVAL-SHAPE'; Match = 'only a pressure scenario' }
       Rows = @(@{ Id = 'ACC-03'; Tier = 'acceptance'; Agent = 'dev'; Rule = 'test-first'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'fixture-unknown'; Expect = @{ Level = 'error'; Rule = 'EVAL-FIXTURE'; Match = "fixture 'repo-y' does not exist" }
       Rows = @(@{ Id = 'ACC-04'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'repo-y'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'patch-not-declared'; Expect = @{ Level = 'error'; Rule = 'EVAL-FIXTURE'; Match = "has no patch 'p9'" }
       Rows = @(@{ Id = 'ACC-04'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'repo-x'; Setup = @('p9'); Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'patch-file-missing'; Expect = @{ Level = 'error'; Rule = 'EVAL-FIXTURE'; Match = 'gone.patch is missing' }
       Rows = @(@{ Id = 'ACC-04'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'repo-x'; Setup = @('gone'); Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'brief-missing'; Expect = @{ Level = 'error'; Rule = 'EVAL-FIXTURE'; Match = 'briefs/nope.md does not exist' }
       Rows = @(@{ Id = 'ACC-05'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Mode = 'delegated'; Brief = 'nope.md'; Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'delegated-without-brief'; Expect = @{ Level = 'error'; Rule = 'EVAL-SHAPE'; Match = 'needs a Brief' }
       Rows = @(@{ Id = 'ACC-05'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Mode = 'delegated'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'uses-text-missing'; Expect = @{ Level = 'error'; Rule = 'EVAL-USES'; Match = 'does not contain it' }
       Rows = @(@{ Id = 'ACC-06'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Be caveman.'); Uses = @(@{ Text = 'caveman'; Fragment = '16-reporting' }); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'uses-fragment-missing-pending'; Expect = @{ Level = 'note'; Rule = 'EVAL-USES'; Match = 'pending M5.*fragment 08d-save-document does not exist' }
       Rows = @(@{ Id = 'ACC-06'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Save it.'); Uses = @(@{ Text = 'Save (Recommended)'; Fragment = '08d-save-document' }); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x'; Pending = 'M5' }) }
    @{ Name = 'uses-role-text-ok'; Expect = 'ok'
       Rows = @(@{ Id = 'ACC-06'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Why?'); Uses = @(@{ Text = '## Root cause first'; Agent = 'dev' }, @{ Text = 'terse'; Fragment = '16-reporting' }); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'leak-in-turns'; Expect = @{ Level = 'error'; Rule = 'EVAL-LEAK'; Match = 'also occurs under agents/' }
       Rows = @(@{ Id = 'ACC-07'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Please note: the quick brown fox jumps over the lazy dog near the pond.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'leak-39-characters-is-fine'; Expect = 'ok'
       Rows = @(@{ Id = 'ACC-07'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('A quick brown fox jumps over the lazy cat, then sleeps all afternoon.'); Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'leak-in-brief-task'; Expect = @{ Level = 'error'; Rule = 'EVAL-LEAK'; Match = 'quick brown fox' }
       Context = @{ Briefs = @{ 'b.md' = "You are a delegated sub-agent working at depth 1 of 3.`n`nTask:`nGOAL: the quick brown fox jumps over the lazy dog near the river.`n" } }
       Rows = @(@{ Id = 'ACC-08'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Mode = 'delegated'; Brief = 'b.md'; Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'brief-opening-is-not-a-leak'; Expect = 'ok'
       Context = @{ Corpus = "the first message begins: You are a delegated sub-agent working at depth 1 of 3. Done.`n" }
       Rows = @(@{ Id = 'ACC-08'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Mode = 'delegated'; Brief = 'b.md'; Pass = @(@{ Says = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'event-unknown-kind'; Expect = @{ Level = 'error'; Rule = 'EVAL-EVENT'; Match = "unknown event kind 'FirstThing'" }
       Rows = @(@{ Id = 'ACC-09'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ FirstThing = 'x' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'event-unknown-tool'; Expect = @{ Level = 'error'; Rule = 'EVAL-EVENT'; Match = "'fs.grep', which is not a Sophon tool" }
       Rows = @(@{ Id = 'ACC-09'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ FirstTool = 'fs.grep' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'event-bad-regex'; Expect = @{ Level = 'error'; Rule = 'EVAL-EVENT'; Match = 'not a valid regex' }
       Rows = @(@{ Id = 'ACC-09'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = '(unclosed' }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'event-first-of-shape'; Expect = @{ Level = 'error'; Rule = 'EVAL-EVENT'; Match = 'FirstOf needs Tools' }
       Rows = @(@{ Id = 'ACC-09'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ FirstOf = @{ Tools = @('os.execute', 'fs.edit'); Is = 'fs.write' } }); Fail = @(@{ Tool = 'fs.write' }); Read = 'x' }) }
    @{ Name = 'acceptance-without-fail'; Expect = @{ Level = 'error'; Rule = 'EVAL-SHAPE'; Match = 'Fail must hold' }
       Rows = @(@{ Id = 'ACC-10'; Tier = 'acceptance'; Agent = 'dev'; Fixture = 'none'; Turns = @('Hi.'); Pass = @(@{ Says = 'x' }); Read = 'x' }) }
    @{ Name = 'same-run-unknown'; Tier = 'design'; Expect = @{ Level = 'error'; Rule = 'EVAL-SHAPE'; Match = "SameRunAs 'DSN-99'" }
       Rows = @(@{ Id = 'DSN-02'; Tier = 'design'; Agent = 'dev'; Fixture = 'none'; SameRunAs = 'DSN-99'; Pass = @(@{ Says = 'x' }); Read = 'x' }) }
    @{ Name = 'fixture-mentions-an-agent'; Expect = @{ Level = 'error'; Rule = 'EVAL-MENTION'; Match = "names 'dev-agent'" }
       Context = @{ Fixtures = @{ 'repo-x' = @{ Dir = ''; Base = ''; Test = ''; Error = ''; Patches = @{}; Files = @(@{ Path = 'files/AGENTS.md'; Text = "Ask the Dev-Agent first.`n" }) } } }
       Rows = @() }
  )
}
