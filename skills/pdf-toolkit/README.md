# PDF Toolkit

Local PDF operations for Sophon: merge, split, rotate, extract text and tables, read metadata,
and encrypt or decrypt PDF files. Everything runs offline in the sandbox — **no network access**
and no credentials required.

Built on [pypdf](https://pypi.org/project/pypdf/) for structural operations and
[pdfplumber](https://pypi.org/project/pdfplumber/) for table extraction.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `pdf.merge` | low | Merge several PDFs into one output file, in order |
| `pdf.split` | low | Split into one file per page, or per `ranges` (e.g. `1-3,5`) |
| `pdf.rotate` | low | Rotate pages clockwise by 90/180/270 degrees |
| `pdf.extract_text` | low | Extract full and per-page text |
| `pdf.extract_tables` | low | Extract detected tables per page (pdfplumber) |
| `pdf.metadata` | none | Read document metadata and page count |
| `pdf.encrypt` | medium | Password-protect a PDF |
| `pdf.decrypt` | medium | Remove password protection from a PDF |

## Files and paths

File inputs and outputs are passed as path strings. Relative paths are resolved against the
current working directory (`/workspace` in the sandbox), and outputs are written into that
directory. Each tool returns the resolved output path(s):

- `pdf.split` returns `outputs` — a list of paths. Filenames are derived from the input stem,
  e.g. `report_page_01.pdf` or `report_pages_1-3.pdf`.
- `pdf.merge`, `pdf.rotate`, `pdf.encrypt`, `pdf.decrypt` return the single `output` path.
- Page numbers in `pages` and `ranges` are **1-based**.

## Errors

- A missing input path returns `{"error": "input not found: <path>"}`.
- Any other failure (invalid range, wrong password, malformed PDF) returns
  `{"error": "..."}` with a short message — the skill never crashes with a traceback.

## Notes

- No authentication or connection is needed; this is a pure-local skill.
- `pdf.decrypt` requires the correct password for encrypted files; an incorrect password
  returns an error rather than a corrupt file.
