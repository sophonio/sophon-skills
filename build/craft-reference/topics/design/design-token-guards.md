---
id: design-token-guards
summary: Literal, parity and contrast guard tests in outline for common runners, and the allow-list format.
reviewed: 2026-11
---
# Token guards: literal, parity and contrast tests

Three guards, each a plain test in the runner the project already has (Vitest or Jest, pytest, or a Stylelint rule). Each guard reads files as text, so it needs no browser.

## Literal guard

Fails when a colour, radius or spacing literal appears outside the token file.

```ts
import { readFileSync } from "node:fs";
import { globSync } from "glob";            // or the runner's own file listing
import allow from "./token-allow.json";

const TOKEN_FILE = "src/styles/tokens.css";
const LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(|\b\d+px\b/g;

test("no literals outside the token file", () => {
  const hits = [];
  for (const file of globSync("src/**/*.{css,scss,tsx,jsx,vue,svelte}")) {
    if (file === TOKEN_FILE) continue;
    readFileSync(file, "utf8").split("\n").forEach((line, i) => {
      for (const m of line.match(LITERAL) ?? []) {
        if (!allow.some(a => a.file === file && a.value === m)) hits.push(`${file}:${i + 1} ${m}`);
      }
    });
  }
  expect(hits).toEqual([]);
});
```

- Narrow the px pattern to the properties the scale covers (`padding`, `margin`, `gap`, `border-radius`, `font-size`) when 1px borders are allowed.
- Stylelint alternative: `color-no-hex` plus a strict-value plugin rule for colour, radius and spacing properties, with the token file in its ignore list.

## Parity guard

Fails when a colour token has no dark value, or when the token block of DESIGN.md differs from the code tokens.

```python
import re, pathlib, yaml   # PyYAML, or the runner's YAML reader

css = pathlib.Path("src/styles/tokens.css").read_text()
light = dict(re.findall(r"--(color-[\w-]+):\s*([^;]+);", css.split(".dark")[0]))
dark = dict(re.findall(r"--(color-[\w-]+):\s*([^;]+);", css.split(".dark", 1)[1]))

def test_every_colour_has_a_dark_value():
    assert sorted(set(light) - set(dark)) == []

def test_design_md_equals_code():
    front = pathlib.Path("DESIGN.md").read_text().split("---")[1]
    block = yaml.safe_load(front)["colors"]
    for name, value in block["light"].items():
        assert light["color-" + name].strip().lower() == value.lower(), name
```

- Split on the project's real dark selector (`.dark`, `[data-theme="dark"]`, or the `prefers-color-scheme: dark` media block).
- Map DESIGN.md names to code names with one explicit table when they differ; never by guessing.

## Contrast guard

Fails when a declared text pair is below the floor, in either mode.

```ts
const PAIRS = [   // text, background, minimum
  ["text", "page", 4.5], ["text-muted", "page", 4.5], ["text-muted", "panel", 4.5],
  ["on-primary", "primary", 4.5], ["focus", "page", 3], ["field-edge", "page", 3],
];
const lin = c => (c /= 255) <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
const lum = hex => { const n = parseInt(hex.slice(1), 16);
  return 0.2126 * lin(n >> 16) + 0.7152 * lin((n >> 8) & 255) + 0.0722 * lin(n & 255); };
const ratio = (a, b) => { const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05); };

test.each(["light", "dark"])("contrast in %s", mode => {
  for (const [fg, bg, min] of PAIRS) {
    expect(ratio(tokens[mode][fg], tokens[mode][bg])).toBeGreaterThanOrEqual(min);
  }
});
```

- `tokens` is the parsed token file, by mode. A value with alpha is composited over its background first; a gradient or image background is listed as unknown, not tested.
- Large text (24 px, or 18.66 px bold) and UI parts use 3.

## Allow-list

Existing violations, so the guard can go green without hiding new ones.

```json
[
  { "file": "src/pages/legacy-report.tsx", "value": "#1C2430", "count": 14,
    "status": "existing", "since": "2026-11-24", "note": "replace with --surface-2" }
]
```

- Match on file and value, not line numbers, which move.
- `count` caps the occurrences (tally hits per file and value): a fifteenth `#1C2430` there fails.
- Every entry is marked "existing"; an entry is removed when its file is fixed, and the list only shrinks.
