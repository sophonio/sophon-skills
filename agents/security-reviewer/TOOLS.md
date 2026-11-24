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
web.scrape reads public advisories; the reviewer never sends requests to the application under review.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
