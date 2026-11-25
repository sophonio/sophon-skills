---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - os.info
      - diff
      - web.scrape
---
os.info records the environment, diff compares good and bad output without a card, web.scrape reads upstream issues.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
