---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - browser.act
      - browser.screenshot
      - web.scrape
  coding.subagent:
    pins:
      - fs.read
      - fs.find
      - fs.search
---
browser.act needs Playwright and opens localhost only with AllowPrivateNetwork; screenshots reach only a person in the chat.
Read tools stay visible under a lead's tool scope; as a sub-agent it reads the diff file or the screens it is given.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
