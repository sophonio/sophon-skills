# Currency Convert

Currency conversion and reference exchange rates through the keyless
[Frankfurter API](https://www.frankfurter.app/), which publishes the European Central Bank (ECB)
reference rates. Convert between currencies, fetch the latest rates for a base currency, look up
historical rates for a past date, and list supported currencies.

Runs in the sandbox with **network access but no credentials** — the Frankfurter API is keyless.
HTTP is handled with the standard-library `urllib`; there are no third-party dependencies.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `currency.convert` | none | Convert an amount from one currency to another at the latest rate; returns `{amount, from, to, rate, result, date}` |
| `currency.rates` | none | Latest ECB rates for a base currency (default EUR), optionally filtered to specific `symbols`; returns `{base, date, rates}` |
| `currency.historical` | none | Convert an amount at the rate for a specific past date (`YYYY-MM-DD`); returns `{amount, from, to, rate, result, date}` |
| `currency.list_currencies` | none | List every supported currency code mapped to its full name; returns `{currencies}` |

## Parameters

- `currency.convert` — `amount` (number), `from` (code), `to` (code). All required.
- `currency.rates` — `base` (code, default `EUR`), `symbols` (optional: comma-separated string like
  `"USD,GBP,JPY"` or an array of codes).
- `currency.historical` — `date` (`YYYY-MM-DD`), `from` (code), `to` (code), `amount` (number,
  default `1`).
- `currency.list_currencies` — no parameters.

Currency codes are 3-letter ISO codes and are matched case-insensitively (they are uppercased before
the request).

## Notes

- Data source is the **European Central Bank** via Frankfurter. The dataset covers roughly 30 major
  currencies and is updated on TARGET business days (weekdays) around 16:00 CET. Weekend and holiday
  dates resolve to the most recent published rates.
- **Unknown or unsupported currency codes** cause the API to return an error message, which this
  skill surfaces as `{"error": "..."}` rather than throwing.
- Converting a currency to itself short-circuits to a rate of `1.0` without a network call.
- Each tool prints a single JSON object to stdout.

## Trademarks

"European Central Bank" and "ECB" are names of the European Central Bank. Frankfurter is an
independent open-source project. This skill is an independent client of the public Frankfurter API
and is not affiliated with or endorsed by the European Central Bank or the Frankfurter project.
