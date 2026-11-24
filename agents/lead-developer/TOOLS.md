---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - agent.list
      - web.scrape
      - session.history
  chat:
    pins:
      - agent.list
      - todo.write
      - fs.find
      - fs.search
      - web.scrape
---
agent.list finds companions; web.scrape reads docs; session.history restores consent after a gap. Unbound chats get read and planning tools only.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
