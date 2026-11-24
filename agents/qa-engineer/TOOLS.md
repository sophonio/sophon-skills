---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - browser.act
      - browser.screenshot
---
Browser checks need Playwright Chromium on the Gateway host; browser.act opens localhost only when Sophon:Browser:AllowPrivateNetwork is on.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
