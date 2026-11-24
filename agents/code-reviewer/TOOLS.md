---
pins:
  - craft.read
profiles:
  coding.subagent:
    pins:
      - fs.read
      - fs.find
      - fs.search
---
Read tools stay visible under a lead's tool scope; as a sub-agent it reads the diff file it is given.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
