You are a delegated sub-agent working at depth 1 of 3. Complete the assigned task and return a concise final result.

Task:
ROLE: frontend-developer · MODE: component · ACCESS: write
GOAL: Add a PlanBadge component that shows a board's plan name next to its title on the home page.
WHY: The boards list needs to show which boards are on the paid plan.
CONTEXT: Components return markup strings (src/components/Card.js:1-9); the home page renders the cards (src/pages/home.js:9-11).
READ_FIRST: src/components/Card.js, src/pages/home.js
WRITE_SCOPE: src/components/PlanBadge.js, src/components/Card.js, test/plan-badge.test.js
RULED_OUT: none
CONSTRAINTS: "Unit tests: `npm test` (node --test, no install needed)"
ACCEPTANCE: npm test → all tests pass
BUDGET: about 25 tool calls; with 3 left, stop and report
END WITH: the STATUS block; at most 200 words before it.
