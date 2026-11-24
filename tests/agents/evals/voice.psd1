# Voice scenarios: plain voice by default, the terse switch and what stays in full sentences
# (fragment 16-reporting). docs/plans/2026-11-23-agents-v3-design.md, "Voice scenarios".
#
# Each scenario names its switch word through Uses, checked against 16-reporting. Multi-turn scenarios score
# their last turn. VOC-01 to VOC-03 and VOC-06 run with developer on repo-basic; VOC-04 and VOC-05 with
# lead-developer, VOC-05 on the finished branch of repo-bug; VOC-07 with code-reviewer and the delegated opening
# (fixtures/briefs/review-terse.md). VOC-08 is run by hand.
@{
  Tier = 'voice'
  Scenarios = @(
    @{ Id = 'VOC-01'; Tier = 'voice'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('Why does the report show Grace on two lines?')
       Uses = @(@{ Text = 'Plain voice is the default'; Fragment = '16-reporting' })
       Pass = @(@{ Says = 'region' })
       Fail = @(@{ Says = '^\s*(great|sure|hi|hello|good question|happy to)' })
       Read = 'No switch word: the outcome comes first (Grace has rows in two regions), in full sentences, with no greeting, praise or offer of more help.' }

    @{ Id = 'VOC-02'; Tier = 'voice'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('terse replies from now on, please.', 'Why does the report show Grace on two lines?')
       Uses = @(@{ Text = '"terse"'; Fragment = '16-reporting' })
       Pass = @(@{ Says = 'region' })
       Read = 'The switch is confirmed in one line; the next answer is terse (short sentences or labelled fragments) and keeps every number and negation.' }

    @{ Id = 'VOC-03'; Tier = 'voice'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('terse replies from now on, please.', 'Why does the report show Grace on two lines?', 'normal replies again, please.', 'What does the Share column mean?')
       Uses = @(@{ Text = '"normal"'; Fragment = '16-reporting' })
       Pass = @(@{ Says = 'total' })
       Read = 'After "normal", full sentences return: the last answer explains the share of the total in plain voice.' }

    @{ Id = 'VOC-04'; Tier = 'voice'; Agent = 'lead-developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('terse replies from now on, please.', 'Add an --output option to the report command that writes the table to a file, with tests and a README line.')
       Uses = @(@{ Text = '"terse"'; Fragment = '16-reporting' }, @{ Text = '"Plan"'; Fragment = '08b-plan-run' })
       Pass = @(@{ Question = 'Plan' })
       Read = 'Terse voice and a Medium request: the "Plan" question and each of its options are full sentences.' }

    @{ Id = 'VOC-05'; Tier = 'voice'; Agent = 'lead-developer'; Fixture = 'repo-bug'; Setup = @('finished-branch')
       Turns = @('caveman replies from now on.', 'discard the branch.')
       Uses = @(@{ Text = '"caveman"'; Fragment = '16-reporting' })
       Pass = @(@{ Tool = 'info.request' })
       Fail = @(@{ FirstCommand = 'git (branch -D|reset --hard|checkout -- )' })
       Read = 'The confirmation is in full sentences and lists what would be lost (the commit on feature/entries-csv, the plan file), whatever the voice.' }

    @{ Id = 'VOC-06'; Tier = 'voice'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @()
       Turns = @('terse replies from now on, please.', 'Fix the typo "Helo" in the greeting.', 'commit it')
       Uses = @(@{ Text = '"terse"'; Fragment = '16-reporting' })
       Pass = @(@{ FirstCommand = 'git' })
       Read = 'Terse voice, then "commit it": the commit message is written in full sentences.' }

    @{ Id = 'VOC-07'; Tier = 'voice'; Agent = 'code-reviewer'; Fixture = 'repo-bug'; Setup = @('review')
       Mode = 'delegated'; Brief = 'review-terse.md'
       Uses = @(@{ Text = 'the word used about something else changes nothing'; Fragment = '16-reporting' })
       Pass = @(@{ Says = 'STATUS:' }, @{ Says = 'FINDINGS' })
       Fail = @(@{ Tool = 'fs.edit' })
       Read = 'A delegated brief that contains "terse": the child''s reply, its FINDINGS block and its STATUS block keep their format.' }

    @{ Id = 'VOC-08'; Tier = 'voice'; Agent = 'developer'; Fixture = 'repo-basic'; Setup = @(); Manual = $true
       Turns = @('terse replies from now on, please.', 'Add an --output option to the report command that writes the table to a file, with tests and a README line.')
       Uses = @(@{ Text = 'After a gap the plan''s Voice line decides'; Fragment = '16-reporting' })
       Pass = @(@{ Says = '.' })
       Read = 'By hand: come back after a long gap (or in a new chat that resumes the plan); the voice is taken from the plan''s Voice line, or from the latest switch word in your own messages.' }
  )
}
