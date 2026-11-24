# Design scenarios: the design-source rules (fragment 20-design-source, the Sophon default 21-sophon-default, the
# direction round of ui-ux-designer and the "Design" question of the other roles).
# docs/plans/2026-11-23-agents-v3-design.md, "Design scenarios".
#
# Markers are the values that count as "a Sophon value" in an attempted write (the NoMarker event): the page
# and primary colours, dark and light, and the two type names, each checked against 21-sophon-default.
# All scenarios run with the reference skill absent except DSN-12. DSN-02 and DSN-03 are scored from the run of
# DSN-01. The delegated message of DSN-08 is fixtures/briefs/component-no-design.md, which starts with the
# runtime's own sub-agent opening.
@{
  Tier = 'design'
  Markers = @{
    Uses = @(
      @{ Text = '#09071A'; Fragment = '21-sophon-default'; Kind = 'page, dark' }
      @{ Text = '#F8FAFC'; Fragment = '21-sophon-default'; Kind = 'page, light' }
      @{ Text = '#818CF8'; Fragment = '21-sophon-default'; Kind = 'primary, dark' }
      @{ Text = '#4F46E5'; Fragment = '21-sophon-default'; Kind = 'primary, light' }
      @{ Text = 'Outfit'; Fragment = '21-sophon-default'; Kind = 'interface type' }
      @{ Text = 'JetBrains Mono'; Fragment = '21-sophon-default'; Kind = 'numbers and code' }
    )
  }
  Scenarios = @(
    @{ Id = 'DSN-01'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Design the settings page. It is for team admins who change board defaults a few times a month; their job is to find one setting and change it fast. We have no design system yet.')
       Uses = @(@{ Text = 'header "Direction"'; Agent = 'ui-ux-designer' })
       Pass = @(@{ Tool = 'canvas.render' }, @{ MaxCalls = @{ Tool = 'canvas.render'; Max = 1 } }, @{ Question = 'Direction' })
       Read = 'A round of four directions with the same anatomy (the same specimen in each), shown in one canvas.render call, then one question under the header "Direction".' }

    @{ Id = 'DSN-02'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; SameRunAs = 'DSN-01'
       Pass = @(@{ FirstOption = '^Sophon.*\(Recommended\)$' })
       Read = 'The first option is the Sophon default and its label ends "(Recommended)"; the others are two alternatives and the plain standard.' }

    @{ Id = 'DSN-03'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; SameRunAs = 'DSN-01'
       Pass = @(@{ NoWrite = '**' }, @{ Says = 'nothing (was|is|has been) applied|not applied|applied nothing' })
       Read = 'With the question unanswered no file is written, and the reply says that nothing was applied.' }

    @{ Id = 'DSN-04'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-system'; Setup = @()
       Turns = @('Design the settings page. It is for team admins who change board defaults a few times a month.')
       Uses = @(@{ Text = 'A system someone chose is never a "default look".'; Fragment = '20-design-source' })
       Pass = @(@{ NoTool = 'canvas.render' }, @{ NoMarker = $true }, @{ Says = 'token|DESIGN\.md' })
       Fail = @(@{ Question = 'Direction' }, @{ NoMarker = $false })
       Read = 'No direction round: the proposal extends the tokens of DESIGN.md and src/styles/tokens.css (the serif face, the orange primary). No Sophon value in any attempted write.' }

    @{ Id = 'DSN-05'; Tier = 'design'; Agent = 'frontend-developer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Add a status badge component for boards: active, paused or archived.')
       Uses = @(@{ Text = '[Sophon design default (Recommended)] [Plain standard] [Direction round]'; Fragment = '20-design-source' })
       Pass = @(@{ Question = 'Design' }, @{ FirstOption = '^Sophon design default \(Recommended\)$' }, @{ NoMarker = $true })
       Fail = @(@{ NoMarker = $false })
       Read = 'One question with the header "Design" whose first option is "Sophon design default (Recommended)". No Sophon value in a write before the pick.' }

    @{ Id = 'DSN-06'; Tier = 'design'; Agent = 'design-system-engineer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('We need a light and a dark theme for this app.')
       Uses = @(@{ Text = '"Theme"'; Agent = 'design-system-engineer' }, @{ Text = 'For interface work, the first source that exists decides the look.'; Fragment = '20-design-source' })
       Pass = @(@{ Question = 'Theme' }, @{ FirstOption = 'Sophon.*\(Recommended\)' }, @{ NoWrite = '**' })
       Fail = @(@{ FirstWrite = '**/*.css' })
       Read = 'Three options side by side under the header "Theme", the Sophon default first and Recommended. No answer applies nothing.' }

    @{ Id = 'DSN-07'; Tier = 'design'; Agent = 'lead-developer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('Just build it: add a billing settings page.')
       Uses = @(@{ Text = '"Just build it" removes discovery questions, never this one.'; Fragment = '20-design-source' })
       Pass = @(@{ Question = 'Design' }, @{ NoMarker = $true })
       Fail = @(@{ ChatQuestion = $true }, @{ NoMarker = $false })
       Read = 'No discovery question, and the "Design" question is still asked. No look in the plan before a pick.' }

    @{ Id = 'DSN-08'; Tier = 'design'; Agent = 'frontend-developer'; Fixture = 'repo-ui-bare'; Setup = @()
       Mode = 'delegated'; Brief = 'component-no-design.md'
       Uses = @(@{ Text = 'return your options as text with STATUS NEEDS_CONTEXT'; Fragment = '20-design-source' })
       Pass = @(@{ Says = 'NEEDS_CONTEXT' }, @{ NoWrite = '**' })
       Fail = @(@{ Tool = 'fs.write' }, @{ Tool = 'fs.edit' })
       Read = 'Delegated with no DESIGN key on a project with no system: it builds nothing and returns its options as text with STATUS NEEDS_CONTEXT.' }

    @{ Id = 'DSN-09'; Tier = 'design'; Agent = 'lead-developer'; Fixture = 'repo-ui-bare'; Setup = @()
       Turns = @('no subagents: add an archive page that lists archived boards with a restore button.')
       Uses = @(@{ Text = 'every other role asks once, header "Design"'; Fragment = '20-design-source' })
       Pass = @(@{ Question = 'Design' }, @{ NoTool = 'agent.delegate' })
       Fail = @(@{ Tool = 'agent.delegate' }, @{ NoMarker = $false })
       Read = 'With a standing no to sub-agents the lead asks the "Design" question itself, before the plan.' }

    @{ Id = 'DSN-10'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; Setup = @(); Manual = $true
       Turns = @('Design the settings page. It is for team admins who change board defaults a few times a month; their job is to find one setting and change it fast. We have no design system yet.', 'Direction 2, please.')
       Uses = @(@{ Text = '- Design rules: DESIGN.md'; Fragment = '08d-save-document' })
       Pass = @(@{ Tool = 'info.request' })
       Fail = @(@{ FirstWrite = 'DESIGN.md' })
       Read = 'By hand: after the pick DESIGN.md is written only after the save question, holds the values of direction 2 and nothing the default bans, and the AGENTS.md line "- Design rules: DESIGN.md" is offered.' }

    @{ Id = 'DSN-11'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; Setup = @(); Mode = 'plan'
       Turns = @('Design the settings page. It is for team admins who change board defaults a few times a month; their job is to find one setting and change it fast. We have no design system yet.')
       Uses = @(@{ Text = 'Plan mode refuses the canvas'; Agent = 'ui-ux-designer' })
       Pass = @(@{ NoTool = 'canvas.render' }, @{ NoWrite = '**' }, @{ Question = 'Direction' })
       Fail = @(@{ Tool = 'canvas.render' }, @{ Tool = 'fs.write' })
       Read = 'In plan mode the round arrives as text with the question; no canvas call and nothing written.' }

    @{ Id = 'DSN-12'; Tier = 'design'; Agent = 'ui-ux-designer'; Fixture = 'repo-ui-bare'; Setup = @(); Skill = 'installed'
       Turns = @('Design the settings page. It is for team admins who change board defaults a few times a month; their job is to find one setting and change it fast. We have no design system yet.')
       Uses = @(@{ Text = 'If the tool is missing or refused, work from what you carry.'; Fragment = '18-reference-topics' })
       Pass = @(@{ Tool = 'canvas.render' }, @{ Question = 'Direction' })
       Read = 'DSN-01, DSN-04 and DSN-05 repeated with the reference skill installed: the same gates and the same first moves, and at most one read per topic.' }

    @{ Id = 'DSN-13'; Tier = 'design'; Agent = 'frontend-developer'; Fixture = 'repo-ui-bare'; Setup = @('styled')
       Turns = @('Add a status badge component for boards: active, paused or archived.')
       Uses = @(@{ Text = 'then the styles its screens already use'; Fragment = '20-design-source' })
       Pass = @(@{ NoMarker = $true })
       Fail = @(@{ Question = 'Design' }, @{ NoMarker = $false })
       Read = 'No "Design" question: the stylesheet the screens already use is the project''s system. The component extends it; no Sophon value in any attempted write.' }
  )
}
