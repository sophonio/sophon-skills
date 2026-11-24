---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - canvas.render
      - browser.screenshot
      - browser.act
      - web.scrape
  chat:
    pins:
      - canvas.render
      - web.scrape
---
Previews and screenshots reach only a person in the chat; browser.act needs Playwright and opens localhost only with AllowPrivateNetwork.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
