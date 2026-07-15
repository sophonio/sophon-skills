# Stripe (Read-Only)

Read-only reporting over the [Stripe](https://stripe.com) REST API. Inspect your account
balance, charges, customers, invoices, and subscriptions without any ability to mutate your
account. Implemented with the Python standard library only (no dependencies).

Every tool is a `GET` request. Connect this skill with a **restricted read key** (`rk_...`) so
it can never write to or modify your Stripe account, even in principle.

## Tools

| Name | Risk | Description |
| --- | --- | --- |
| `stripe.get_balance` | none | Get the current account balance (available and pending funds). |
| `stripe.list_charges` | none | List recent charges, optionally filtered by `customer`. |
| `stripe.list_customers` | none | List customers, optionally filtered by `email`. |
| `stripe.list_invoices` | none | List invoices, optionally filtered by `customer` and `status`. |
| `stripe.list_subscriptions` | none | List subscriptions, optionally filtered by `customer` and `status`. |
| `stripe.get_object` | none | Retrieve a single object by id from an allowlisted resource. |

`list_*` tools accept a `limit` (default 10, capped at 100). `stripe.get_object` accepts a
`resource` from the allowlist (`charges`, `customers`, `invoices`, `subscriptions`,
`payment_intents`, `payouts`, `products`, `prices`) and an object `id`.

## Connection

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `apiKey` | secret | yes | A **restricted read-only key** (`rk_...`). Create one at the [Stripe API keys dashboard](https://dashboard.stripe.com/apikeys). |

The key is sent as a `Bearer` token to `https://api.stripe.com/v1` and is never included in any
tool output.

## Trademarks

Stripe is a trademark of Stripe, Inc. This is an independent, unofficial integration and is not
affiliated with, endorsed by, or sponsored by Stripe, Inc.
