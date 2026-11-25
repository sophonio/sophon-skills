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
web.scrape reads the pages behind a product question; the read and search tools stay visible when a lead narrows this agent's tools.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
