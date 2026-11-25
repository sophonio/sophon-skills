---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - canvas.render
      - browser.act
      - browser.screenshot
      - web.scrape
      - fs.move
      - calculator.evaluate
  coding.subagent:
    pins:
      - calculator.evaluate
  chat:
    pins:
      - canvas.render
      - web.scrape
---
calculator.evaluate computes contrast ratios. Swatches, playground previews and screenshots reach only a person in the chat; browser.act needs Playwright and opens localhost only with AllowPrivateNetwork; fs.move renames token and theme files.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
