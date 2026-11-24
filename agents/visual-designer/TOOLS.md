---
pins:
  - craft.read
profiles:
  coding:
    pins:
      - canvas.render
      - image.generate
      - media.image
      - browser.screenshot
      - web.scrape
      - fs.move
  chat:
    pins:
      - canvas.render
      - image.generate
      - media.image
      - web.scrape
---
Previews, screenshots and generated images reach only a person in the chat; image.generate needs an image provider configured and raises a card each time.
craft.read comes from the optional craft-reference skill; without it the agent works from what its instructions carry.
