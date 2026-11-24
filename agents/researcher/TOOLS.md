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
      - web.search
---
web.scrape reads pages everywhere; read tools stay visible when a lead scopes this agent's tools.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
