---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - web.scrape
  chat:
    pins:
      - web.scrape
---
web.scrape reads API and SDK documentation; builds and self-checks run through os.execute, and no server is left running.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
