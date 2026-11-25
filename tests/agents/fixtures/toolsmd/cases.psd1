# TOOLS.md fixtures (docs/plans/2026-11-15-agents-v2-design.md section 7.5 G), run by Invoke-AgentLintFixtures in
# build/AgentLint.psm1.
# Each case is parsed with Read-ToolsMd (strict grammar plus agreement with the AgentToolPins.Parse port) and
# checked with Test-ToolsMdPins. Lines are joined with LF and end with one LF.
@{
    Cases = @(
        # ---- must pass ----
        @{ Name = 'lead-developer shape'; Expect = 'pass'
           Lines = @('---', 'profiles:', '  coding:', '    pins:', '      - agent.list', '      - web.scrape', '      - session.history',
                     '  chat:', '    pins:', '      - agent.list', '      - todo.write', '      - fs.find', '      - fs.search', '      - web.scrape',
                     '---', 'agent.list finds companions; web.scrape reads docs; session.history restores consent after a gap.', '') }
        @{ Name = 'global pin plus a child profile with core duplicates'; Expect = 'pass'
           Lines = @('---', 'pins:', '  - web.scrape', 'profiles:', '  coding.subagent:', '    pins:', '      - fs.read', '      - fs.find',
                     '      - fs.search', '      - web.search', '---', 'web.scrape reads pages; read tools stay visible under a lead''s tool scope.', '') }
        @{ Name = 'five body lines'; Expect = 'pass'
           Lines = @('---', 'profiles:', '  coding:', '    pins:', '      - fs.move', '---', 'One.', 'Two.', 'Three.', 'Four.', 'Five.', '') }

        # ---- must fail ----
        @{ Name = 'no frontmatter'; Expect = 'fail'; Rule = 'TOOLS-FRONTMATTER'
           Lines = @('pins:', '  - web.scrape', '') }
        @{ Name = 'no closing delimiter'; Expect = 'fail'; Rule = 'TOOLS-FRONTMATTER'
           Lines = @('---', 'pins:', '  - web.scrape', 'web.scrape reads pages.', '') }
        @{ Name = 'inline list'; Expect = 'fail'; Rule = 'TOOLS-GRAMMAR'
           Lines = @('---', 'pins: [web.scrape, agent.list]', '---', 'Inline lists are not canonical.', '') }
        @{ Name = 'unknown profile'; Expect = 'fail'; Rule = 'TOOLS-GRAMMAR'
           Lines = @('---', 'profiles:', '  coder:', '    pins:', '      - web.scrape', '---', 'Unknown profile name.', '') }
        @{ Name = 'wrong indentation'; Expect = 'fail'; Rule = 'TOOLS-GRAMMAR'
           Lines = @('---', 'pins:', '    - web.scrape', '---', 'Four-space item under a top-level key.', '') }
        @{ Name = 'tab indentation'; Expect = 'fail'; Rule = 'TOOLS-GRAMMAR'
           Lines = @('---', 'pins:', '{U+0009}- web.scrape', '---', 'Tabs are not allowed.', '') }
        @{ Name = 'blank line in frontmatter'; Expect = 'fail'; Rule = 'TOOLS-GRAMMAR'
           Lines = @('---', 'pins:', '  - web.scrape', '', 'profiles:', '  coding:', '    pins:', '      - fs.move', '---', 'A blank line.', '') }
        @{ Name = 'duplicate pin'; Expect = 'fail'; Rule = 'TOOLS-DUP'
           Lines = @('---', 'pins:', '  - web.scrape', '  - web.scrape', '---', 'Twice.', '') }
        @{ Name = 'profile without pins'; Expect = 'fail'; Rule = 'TOOLS-EMPTY'
           Lines = @('---', 'profiles:', '  coding:', '---', 'Nothing pinned.', '') }
        @{ Name = 'edit tool pinned'; Expect = 'fail'; Rule = 'TOOLS-PIN-EDIT'
           Lines = @('---', 'profiles:', '  coding.subagent:', '    pins:', '      - fs.edit', '---', 'Edit tools are never pinned.', '') }
        @{ Name = 'restricted pin'; Expect = 'fail'; Rule = 'TOOLS-PIN-RESTRICTED'
           Lines = @('---', 'profiles:', '  coding:', '    pins:', '      - code.test', '---', 'code.test cannot see the project.', '') }
        @{ Name = 'pin of a tool Sophon v3 removes'; Expect = 'fail'; Rule = 'TOOLS-PIN-V3'
           Lines = @('---', 'profiles:', '  coding.subagent:', '    pins:', '      - memory.graph', '---', 'Child notes.', '') }
        @{ Name = 'denied pin'; Expect = 'fail'; Rule = 'TOOLS-PIN-DENIED'
           Lines = @('---', 'pins:', '  - web.fetch', '---', 'There is no such tool.', '') }
        @{ Name = 'unknown pin'; Expect = 'fail'; Rule = 'TOOLS-PIN-UNKNOWN'
           Lines = @('---', 'pins:', '  - fs.readfile', '---', 'Not a tool.', '') }
        @{ Name = 'core duplicate in a root profile'; Expect = 'fail'; Rule = 'TOOLS-PIN-CORE'
           Lines = @('---', 'profiles:', '  coding:', '    pins:', '      - fs.read', '---', 'fs.read is already core.', '') }
        @{ Name = 'core duplicate as a global pin'; Expect = 'fail'; Rule = 'TOOLS-PIN-CORE'
           Lines = @('---', 'pins:', '  - web.search', '---', 'web.search is already core.', '') }
        @{ Name = 'nine pins'; Expect = 'fail'; Rule = 'TOOLS-PIN-COUNT'
           Lines = @('---', 'profiles:', '  coding:', '    pins:', '      - agent.list', '      - web.scrape', '      - session.history',
                     '      - fs.move', '      - fs.delete', '      - fs.copy', '      - fs.info', '      - os.info', '      - diff', '---',
                     'Too many pins.', '') }
        @{ Name = 'empty body'; Expect = 'fail'; Rule = 'TOOLS-BODY'
           Lines = @('---', 'pins:', '  - web.scrape', '---', '') }
        @{ Name = 'six body lines'; Expect = 'fail'; Rule = 'TOOLS-BODY'
           Lines = @('---', 'pins:', '  - web.scrape', '---', 'One.', 'Two.', 'Three.', 'Four.', 'Five.', 'Six.', '') }
        @{ Name = 'list in the body'; Expect = 'fail'; Rule = 'TOOLS-BODY'
           Lines = @('---', 'pins:', '  - web.scrape', '---', '- web.scrape reads pages.', '') }
    )
}
