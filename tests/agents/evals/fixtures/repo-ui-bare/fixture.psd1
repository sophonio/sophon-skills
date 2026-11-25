# repo-ui-bare: a small web app (plainboard) whose components return unstyled markup: no stylesheet, no component
# library, no inline styles, no tokens and no DESIGN.md, so no rung of the design-source rule finds a project
# system. Planted on purpose: landing/index.html has accessibility defects (an image without alt text, an input
# without a label, an icon-only button with no name, a heading level skipped, a "Click here" link);
# e2e/settings.spec.js asserts a heading the page does not have.
@{
  Description = 'Node web app with unstyled components, a landing page with accessibility defects, unit tests and two Playwright specs'
  Test = 'node --test'
  Patches = @{
    'styled' = @{ Why = 'one stylesheet (src/styles/app.css) that every screen links: the styles its screens already use' }
    'untested-fix' = @{ Why = 'a 12-line fix to formatDuration in src/lib/format.js, applied and not tested' }
  }
}
