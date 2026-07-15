# Units Convert

Offline unit conversion built entirely on the Python standard library. Every conversion is pure
local arithmetic — no dependencies, no network, and no credentials. Each dimension defines a base
unit and a factor table; temperature is handled separately with offset formulas.

## Tools

| Tool | Risk | Description |
|------|------|-------------|
| `units.convert` | none | Convert a value between two units of the same dimension |
| `units.list_units` | none | List supported units, all or for one dimension |

## Details

- **`units.convert`** — takes `value`, `from`, and `to`. The two units must belong to the same
  dimension; otherwise it returns `{ "error": "incompatible units: <from> and <to>" }`. Returns
  `{ "value", "from", "to", "dimension", "result" }` with canonical unit symbols. Temperature
  (`C`/`F`/`K`) uses offset formulas rather than scale factors.
- **`units.list_units`** — with no `category`, returns every unit grouped by dimension. With a
  `category` (one of the dimensions below), returns just that dimension's units and its base unit.

Unit inputs are tolerant of common aliases and case, e.g. `meter`/`metre`/`m`, `pound`/`lbs`/`lb`,
`km/h`/`kph`/`kmh`. Note that `b` (bit) and `B` (byte) are distinguished by case.

## Supported dimensions

| Dimension | Base | Units |
|-----------|------|-------|
| length | m | m, km, cm, mm, mi, yd, ft, in, nmi |
| mass | kg | kg, g, mg, lb, oz, st, t |
| volume | l | l, ml, m3, gal, qt, pt, cup, floz |
| area | m2 | m2, km2, cm2, ft2, in2, ac, ha |
| speed | mps | mps, kmh, mph, kn, fps |
| time | s | s, min, h, day, week |
| data | B | b, B, KB, MB, GB, TB, KiB, MiB, GiB, TiB |
| pressure | pa | pa, kpa, bar, psi, atm |
| energy | j | j, kj, cal, kcal, wh, kwh |
| angle | rad | rad, deg, grad |
| temperature | — | C, F, K |

Volume and area imperial/US units use US customary definitions (US gallon, quart, pint, cup, fluid
ounce; international acre). Data units follow SI decimal prefixes (`KB` = 1000 bytes) and IEC binary
prefixes (`KiB` = 1024 bytes).

## Notes

- No authentication and no network access — `sandbox.network` is `false`.
- Pure compute over the standard library; the only import is `json` for output.
