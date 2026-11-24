---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - fs.move
      - fs.delete
---
Renames and deletions go through path-specific cards instead of shell commands.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
