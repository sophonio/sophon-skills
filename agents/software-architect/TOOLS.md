---
pins:
  - craft.read
  - web.scrape
profiles:
  coding.subagent:
    pins:
      - fs.read
      - fs.find
      - fs.search
---
web.scrape reads library and standards pages; read tools stay visible under a lead's tool scope.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
