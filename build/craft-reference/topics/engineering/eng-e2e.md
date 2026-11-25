---
id: eng-e2e
summary: Locator order with examples, waits that hold and their replacements, per-test data, failure causes with repairs.
reviewed: 2026-11
---
# Browser end-to-end tests: locators, waits, healing

Examples use Playwright Test for JavaScript; the ideas carry over to other runners.

## Locators

| Order | Locator | Example | Fine when |
|---|---|---|---|
| 1 | role and accessible name | `page.getByRole('button', { name: 'Save' })` | almost always; it also proves the control is named |
| 2 | label | `page.getByLabel('Email')` | form fields |
| 3 | visible text or placeholder | `page.getByText('No orders yet')` | static text; use a regex for dynamic parts: `/Order #\d+ placed/` |
| 4 | test id | `page.getByTestId('cart-total')` | no stable role or text exists, such as a canvas or a number with no label |
| 5 | CSS | `page.locator('table.orders tbody tr')` | the structure is the contract; scope it inside a located parent |

Narrow by chaining, not by position: `page.getByRole('row', { name: /Invoice 1042/ }).getByRole('button', { name: 'Pay' })` instead of `nth(3)`. Text in a translated app comes from the same translation file the app uses.

## Waits

| Instead of | Use |
|---|---|
| `page.waitForTimeout(2000)` | a web-first assertion: `await expect(locator).toBeVisible()` |
| a check that reads once, such as `expect(await locator.isVisible()).toBe(true)` | `await expect(locator).toBeVisible()`, which retries until its timeout |
| `waitForLoadState('networkidle')` | wait for the element or response the step needs |
| polling a value in a loop | `await expect.poll(() => getCount()).toBe(3)` |
| a click, then reading the result of a request | `const res = page.waitForResponse('**/api/orders'); await click; await res;` |
| a longer global timeout | find the condition that is slow and wait for it |

Network-idle waits suit a throwaway script that inspects a page once; in committed tests they make runs slow and flaky.

## Test data

- Each test creates what it needs, through the API or a fixture, not through the UI of another feature.
- Unique values per test (a suffix from the worker index and time), so parallel runs do not collide.
- Sign in once per worker and reuse the stored session state; one test per file signs in through the form.
- Freeze or set the clock for dates and timers (`page.clock`), never wait for real time to pass.
- Mock only third-party services with `page.route`; our own backend stays real.
- Clean up in an after hook, or make data disposable by using a fresh tenant or user.

## Failure causes

| Cause | Signs | Repair |
|---|---|---|
| locator | "strict mode violation" (several matches), or a timeout waiting for a locator; the element exists under another name | a role or label locator that matches one element; scope it to its parent |
| timing | passes on rerun; a fixed sleep; reads straight after an action | wait for the state the next step needs |
| data | depends on records made by another test or a previous run; a unique-constraint error | own data per test; unique values |
| environment | only in CI; browser or OS version; viewport; fonts; time zone; a missing service | set them in the config; match CI locally; check the service is up first |
| app defect | the app does what the trace shows and the assertion states what the spec says | none in the test: the test stays red and the defect is described |

Healing changes how a test reaches and waits for the state, never what it asserts. Read the trace (`--trace on`) for the failing step: the snapshot before and after, the console and the network.
