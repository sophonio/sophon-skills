---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - agent.list
      - fs.info
      - session.history
      - web.scrape
  chat:
    pins:
      - agent.list
      - session.history
      - web.scrape
  coding.subagent:
    pins:
      - fs.read
      - fs.find
      - fs.search
      - fs.info
---
agent.list shows installed agents and their when-to-use text; fs.info measures files against the package limits; session.history reads a finished session for diagnose mode and for test arms; web.scrape reads platform documentation.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
