# repo-ui-system: repo-ui-bare with a design system of its own: DESIGN.md, a token file with a distinct look (a
# serif face, an orange primary), a stylesheet built on the tokens, and the AGENTS.md line "- Design rules:
# DESIGN.md". The files below are copied over the repo-ui-bare files.
@{
  Description = 'repo-ui-bare plus DESIGN.md, design tokens and the AGENTS.md design-rules line'
  Base = 'repo-ui-bare'
  Test = 'node --test'
  Patches = @{}
}
