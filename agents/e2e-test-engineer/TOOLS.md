---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - browser.act
      - browser.screenshot
      - web.scrape
  chat:
    pins:
      - web.scrape
---
Screenshots reach only a person in the chat; browser.act needs Playwright and opens localhost only with AllowPrivateNetwork.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
