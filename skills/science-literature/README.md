# science-literature

Keyless, read-only literature lookups for Sophon Science: PubMed through NCBI E-utilities, Europe
PMC, and Crossref DOI resolution. Every result carries the provenance a `science-evidence` bundle
source needs.

No credentials. Python standard library only.

## Tools

| Tool | Source | What it returns |
|------|--------|-----------------|
| `scilit.pubmed_search` | PubMed (esearch, then esummary) | Citation records for up to 100 hits, optional publication-date range |
| `scilit.pubmed_abstracts` | PubMed (efetch) | Abstracts and citation details for up to 100 PMIDs |
| `scilit.europepmc_search` | Europe PMC | Citation records, including preprints, with cursor paging |
| `scilit.crossref_work` | Crossref | The record behind one DOI |

Each record holds `provider`, `pmid`, `pmcid`, `doi`, `title`, `journal`, `year`,
`publication_types`, `publication_kind` (`journal_article`, `preprint`, `unknown`),
`retraction_status` (`retracted`, `not_flagged`, `unknown`), `license` and `url`. Each result holds
`retrieval`: provider, request URL, UTC retrieval time and the SHA-256 of the raw response (with each
step when a tool makes two requests).

`not_flagged` means the provider's data carries no retraction notice for the work. It is not a
statement that the work is sound. `unknown` means the provider gave no publication-type or update
data to decide from.

## Network and limits

- Only `https://eutils.ncbi.nlm.nih.gov`, `https://www.ebi.ac.uk` and `https://api.crossref.org`.
  Callers never pass a URL, and a redirect to any other host or to plain HTTP is refused.
- 10-second timeout per request, responses up to 5 MiB, at most 100 records per call.
- One attempt per request and no retries. An HTTP 429 returns `code: RATE_LIMITED` with the server's
  `retry_after` value when the server sends a number of seconds or an HTTP date, so the agent can wait.
- XML responses must be UTF-8; a response that declares another encoding or any XML entity is
  refused (`UNSAFE_XML`).
- Provider limits: NCBI E-utilities allow 3 requests per second without an API key; Crossref's public
  pool allows 5 DOI lookups and 1 query per second. Make one call at a time.
- Europe PMC permits automated bulk download of its open-access content only. Use these tools for
  targeted searches, not for harvesting.
- E-utilities requests identify the tool as `sophon-science-literature`. No e-mail address is sent.

## Error codes

`INVALID_ARGUMENT` (nothing is requested), `RATE_LIMITED`, `NOT_FOUND`, `HTTP_ERROR`, `NETWORK_ERROR`,
`TIMEOUT`, `RESPONSE_TOO_LARGE`, `BAD_RESPONSE`, `UNSAFE_XML` (an XML response that declares
entities), `UNSAFE_REDIRECT`, `UNKNOWN_TOOL`.

## What a result does not mean

Citation resolution is not claim support. A record that exists, with a DOI that resolves, says
nothing about whether it supports the sentence it is cited for. A reviewer reads the quoted passage.
PubMed holds abstracts, not full text.

## Trademarks and data terms

PubMed and NCBI are services of the U.S. National Library of Medicine; Europe PMC is run by EMBL-EBI;
Crossref is a trademark of Crossref. This skill is not affiliated with them. Each provider's terms
of use apply to the data you retrieve, and individual records can carry their own licences.

## License

MIT © Buildersoft LLC. See `LICENSE`.
