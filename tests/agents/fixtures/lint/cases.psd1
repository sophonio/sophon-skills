# Tool-name lint fixtures (design section 7.5 C), run by Invoke-AgentLintFixtures in build/AgentLint.psm1.
# Expect 'fail' passes when an issue carries Rule; Expect 'pass' passes when there is no issue at all.
# Kind is soul unless stated. Lines are joined with LF.
@{
    Cases = @(
        # ---- must fail ----
        @{ Name = 'web.fetch alone'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Text = 'Read the page with web.fetch.' }
        @{ Name = 'tool_search'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Text = 'Find the tool with tool_search first.' }
        @{ Name = 'agent_delegate wire form'; Expect = 'fail'; Rule = 'LINT-WIRE'
           Text = 'Start the children with agent_delegate.' }
        @{ Name = 'fs_read wire form'; Expect = 'fail'; Rule = 'LINT-WIRE'
           Text = 'Open the file with fs_read.' }
        @{ Name = 'fs.glob'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Text = 'List the sources with fs.glob.' }
        @{ Name = 'code.git push in prose'; Expect = 'fail'; Rule = 'LINT-GITOP'
           Text = 'Publish the branch with code.git push.' }
        @{ Name = 'code.git push operation'; Expect = 'fail'; Rule = 'LINT-GITOP'
           Text = 'Call code.git {operation:"push"} at the end.' }
        @{ Name = 'code.git operation by context'; Expect = 'fail'; Rule = 'LINT-GITOP'
           Lines = @('- `code.git {operation:"status"}` lists files.', '- `{operation:"rebase"}` rewrites history.') }
        @{ Name = 'code.git push operation unquoted in braces'; Expect = 'fail'; Rule = 'LINT-GITOP'
           Text = 'Then code.git {operation: push} the branch.' }
        @{ Name = 'bad stash_action'; Expect = 'fail'; Rule = 'LINT-GITOP'
           Text = 'Restore with code.git {operation:"stash", stash_action:"apply"}.' }
        @{ Name = 'Bash in backticks in a soul'; Expect = 'fail'; Rule = 'LINT-CLAUDE'
           Text = 'Run `Bash` to list the files.' }
        @{ Name = 'TodoWrite in backticks in TOOLS'; Kind = 'tools'; Expect = 'fail'; Rule = 'LINT-CLAUDE'
           Text = 'Track steps like `TodoWrite` does.' }
        @{ Name = 'Claude Code phrase in a soul'; Expect = 'fail'; Rule = 'LINT-CLAUDE'
           Text = 'Work the way Claude Code does.' }
        @{ Name = 'un-negated sessions.yield'; Expect = 'fail'; Rule = 'LINT-RESTRICTED'
           Text = 'End the turn with sessions.yield when you wait.' }
        @{ Name = 'un-negated code.test'; Expect = 'fail'; Rule = 'LINT-RESTRICTED'
           Text = 'Run the suite with code.test.' }
        @{ Name = 'un-negated workflow tool'; Expect = 'fail'; Rule = 'LINT-RESTRICTED'
           Text = 'Split the work with workflow.trigger.' }
        @{ Name = 'un-negated github.create_pull_request'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Text = 'Open the PR with github.create_pull_request.' }
        @{ Name = 'skill tool'; Expect = 'fail'; Rule = 'LINT-SKILL'
           Text = 'Read the table with airtable.list_records.' }
        @{ Name = 'unknown tool'; Expect = 'fail'; Rule = 'LINT-UNKNOWN'
           Text = 'Load the file with fs.readfile.' }
        @{ Name = 'negation two lines up does not count'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Lines = @('There is no shortcut.', 'Read files with fs.read.', 'Then read pages with web.fetch.') }
        @{ Name = 'Workspace heading'; Expect = 'fail'; Rule = 'LINT-HEADING'
           Lines = @('# Developer', '', '## Workspace rules', 'Keep edits small.') }
        @{ Name = 'Interaction heading in a readme'; Kind = 'readme'; Expect = 'fail'; Rule = 'LINT-HEADING'
           Text = '## Interaction' }
        @{ Name = 'denied name in manifest text'; Kind = 'manifest'; Expect = 'fail'; Rule = 'LINT-DENIED'
           Text = 'Reads pages with web.fetch and plans changes.' }
        @{ Name = 'memory.link, removed in v3'; Expect = 'fail'; Rule = 'LINT-V3'
           Text = 'Connect the two facts with memory.link.' }
        @{ Name = 'memory.traverse, removed in v3, even negated'; Expect = 'fail'; Rule = 'LINT-V3'
           Text = 'There is no memory.traverse; use memory.search.' }
        @{ Name = 'memory.graph in a readme'; Kind = 'readme'; Expect = 'fail'; Rule = 'LINT-V3'
           Text = 'It maps the project with memory.graph.' }
        @{ Name = 'memory.entity.list in a TOOLS body'; Kind = 'tools'; Expect = 'fail'; Rule = 'LINT-V3'
           Text = 'List people with memory.entity.list.' }

        # ---- must pass ----
        @{ Name = 'negated web.fetch'; Expect = 'pass'
           Text = 'There is no web.fetch; use web.scrape {operation:"readability", url}.' }
        @{ Name = 'negated sessions.yield'; Expect = 'pass'
           Text = 'Do not use sessions.yield: it ends your turn and nothing resumes you.' }
        @{ Name = 'negation on the previous line'; Expect = 'pass'
           Lines = @('Never name these as tools:', '- web.fetch, fs.glob or tool_search.') }
        @{ Name = 'negated code.git push'; Expect = 'pass'
           Text = 'There is no code.git push; run git push through os.execute.' }
        @{ Name = 'code.git has no push'; Expect = 'pass'
           Text = 'code.git has no push, add or rebase; selective commits go through os.execute.' }
        @{ Name = 'file names'; Expect = 'pass'
           Text = 'Write tools.json and data.json, then read manifest.json and README.md.' }
        @{ Name = 'marketplace host'; Expect = 'pass'
           Text = 'Packages are reviewed on marketplace.sophon.buildersoft.io before approval.' }
        @{ Name = 'github host'; Expect = 'pass'
           Text = 'Push to github.com over HTTPS.' }
        @{ Name = 'e.g. and i.e.'; Expect = 'pass'
           Text = 'Name the scratch file, e.g. sophon-scratch-pr.md, i.e. a root file.' }
        @{ Name = 'wire form beside its dotted name'; Expect = 'pass'
           Text = 'Your provider may show fs.read as fs_read.' }
        @{ Name = 'code.git operations by context'; Expect = 'pass'
           Lines = @('- `code.git {operation:"status"}` lists files.', '- `{operation:"log", count}` shows history.', '- `{operation:"stash", stash_action:"list"}` lists stashes.') }
        @{ Name = 'prose operation word after code.git'; Expect = 'pass'
           Lines = @('Never commit via code.git when a hook must run.', 'Ask first unless the user named the exact operation: deleting files or branches.') }
        @{ Name = 'single-segment tool call resets the context'; Expect = 'pass'
           Text = 'code.git {operation:"blame", file_path} costs a card; diff {operation:"text_diff", text_a, text_b} costs none.' }
        @{ Name = 'context switches to web.scrape'; Expect = 'pass'
           Text = 'After code.git {operation:"log"}, read docs with web.scrape {operation:"readability", url}.' }
        @{ Name = 'profile names are not tools'; Expect = 'pass'
           Text = 'The coding.subagent profile pins fs.read; coding.graphnode pins nothing.' }
        @{ Name = 'DOM properties are not tools'; Expect = 'pass'
           Text = 'The evaluate script returns document.title and document.body text.' }
        @{ Name = 'git config keys are not tools'; Expect = 'pass'
           Text = 'Read the remote with git config --get remote.origin.url.' }
        @{ Name = 'Claude Code names in a readme'; Kind = 'readme'; Expect = 'pass'
           Text = 'Like `Bash` and `TodoWrite` in Claude Code, os.execute and todo.write do the work.' }
        @{ Name = 'real tools'; Expect = 'pass'
           Text = 'Use fs.read, fs.find, fs.search, code.git, os.execute, todo.write, info.request, plan.propose, agent.delegate and web.search.' }
        @{ Name = 'versions and paths'; Expect = 'pass'
           Text = 'Needs Sophon 2.2.0; see docs/plans/2026-11-15-agents-v2.md and build/agent-src/family.psd1.' }
        @{ Name = 'heading that is not reserved'; Expect = 'pass'
           Lines = @('## Scope', '### Workspace check') }
        @{ Name = 'memory tools v3 keeps'; Expect = 'pass'
           Text = 'Recall with memory.search and save with memory.write {content, category:"preference", scope:"user"}.' }
        @{ Name = 'git commands through os.execute'; Expect = 'pass'
           Text = 'Run git push -u origin sophon/<slug> && gh pr create through os.execute.' }
    )
}
