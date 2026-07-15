# DNS Tools

DNS and WHOIS diagnostics built entirely on the Python standard library (`urllib`, `ipaddress`).
Queries run over DNS-over-HTTPS (Google's `dns.google` JSON API) and RDAP (the modern WHOIS, via
`rdap.org`). No dependencies and no credentials — every tool is a keyless read.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `dns.lookup` | none | Resolve A/AAAA/MX/TXT/NS/CNAME/SOA/CAA records for a hostname |
| `dns.reverse` | none | Reverse (PTR) lookup for an IPv4 or IPv6 address |
| `dns.mail_records` | none | MX (sorted by preference), SPF, and DMARC records for a domain |
| `dns.whois` | none | Domain registrar, status, nameservers, and registration/expiry dates via RDAP |

## Details

- **`dns.lookup`** — `name` is required; `type` defaults to `A`. Returns
  `{ name, type, answers: [{ data, ttl }], status }` where `status` is the DNS RCODE name
  (`NOERROR`, `NXDOMAIN`, ...). TXT record data is unquoted.
- **`dns.reverse`** — `ip` is required. Builds the `in-addr.arpa` (IPv4) / `ip6.arpa` (IPv6)
  name and does a PTR lookup, returning `{ ip, arpa, hostnames, status }`.
- **`dns.mail_records`** — `domain` is required. Fetches MX (sorted by preference), extracts the
  SPF policy (the apex TXT record beginning `v=spf1`), and the DMARC policy (TXT at
  `_dmarc.<domain>` beginning `v=DMARC1`). Returns `{ domain, mx, spf, dmarc }`; missing records
  come back as `null`/empty.
- **`dns.whois`** — `domain` is required. Queries RDAP and returns
  `{ domain, registrar, status, nameservers, events }`. `events` maps RDAP actions
  (`registration`, `expiration`, `last changed`, ...) to ISO dates. Unknown domains return a clean
  `{ "error": "domain not found: ..." }`.

## Notes

- `sandbox.network` is `true`; the only hosts contacted are `dns.google` and `rdap.org`.
- NXDOMAIN and not-found responses are returned as clean JSON (empty answers or an `error` field),
  never as exceptions.

## Trademarks

Google and DNS-over-HTTPS are trademarks of Google LLC. RDAP data is served by `rdap.org` and the
respective domain registries. This skill is not affiliated with or endorsed by any of them.
