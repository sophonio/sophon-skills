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
web.scrape reads external pages a doc links to or that you point it at; read tools stay visible under a lead's tool scope; documented commands are checked with os.execute only in harmless forms unless a run is allowed.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
