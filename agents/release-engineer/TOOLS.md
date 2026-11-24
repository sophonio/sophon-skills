---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - web.scrape
      - http.request
  chat:
    pins:
      - web.scrape
  coding.subagent:
    pins:
      - fs.read
      - fs.find
      - fs.search
---
web.scrape reads migration guides and release documentation; http.request makes one health request after a deploy, a card each; read tools stay visible when a lead scopes the release check.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
