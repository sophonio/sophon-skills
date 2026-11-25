## Tests that can fail
Keep a test only when you can name the break in the product that would turn it red, whether you write the test or review it.
- Tautology: the expected value comes from the code under test or its output. Take it from the spec, a hand-worked example or a recorded real response.
- Vacuity: a filter, loop, guard or mock leaves the assertion nothing to check. Assert first that the code under test ran.
- A red test turns green in two ways only: the product changes, or a wrong expectation is corrected; say which. A looser or deleted assertion, an added retry, a raised timeout or a skipped test is the user's decision: show the diff, ask (as a child: OPEN_QUESTIONS) and put the reason in the test. In a review, each one is a finding.

| Excuse | Reality |
|---|---|
| "The assertion is too strict." | A weaker one changes what the product promises; that is the user's call. |
| "A retry makes it stable." | A retry hides a race the user will meet; wait for the state the test needs. |
| "The test is wrong, not the code." | Then name the source of the right value and correct it openly. |
