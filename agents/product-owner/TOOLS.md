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
web.scrape reads an issue or page a request points at; read tools stay visible under a lead's tool scope, so an acceptance check can cite path:line.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
