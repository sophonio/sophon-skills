# Assay comparison (synthetic)

A small synthetic project for a lab-style comparison. Nothing here is real data or a real study.

- `data/assay.csv`: 12 rows with the columns `unit` (experimental unit id), `group` (`A` or `B`) and `value`
  (assay reading, ug/mL). Unit `a3` appears twice, and one value (`b6`) is `NA`.
- `evidence/bundle-planted.json`: an evidence bundle for the question "is the group B mean higher?". Its
  analysis record is a real output of the statistics tool, and one claim states a number that differs from the
  analysis it cites.

No literature sources are bundled. Method choice, units and the missing-value policy are not decided yet.
