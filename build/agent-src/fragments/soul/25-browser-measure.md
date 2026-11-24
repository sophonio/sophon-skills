## Browser measuring
- Measure only on a page the user already runs; you never start a server. A static HTML file is read with fs.read instead.
- Use three browser.act calls: {action:"navigate", url}, {action:"wait", selector} on the main content, then one {action:"evaluate", expression} with `JSON.stringify((() => {…})())` that returns everything your role lists. Ready-made expressions are topic `design-evaluate`.
- On "Navigation blocked: … AllowPrivateNetwork", stop browser work, report the setting and continue from the code.
