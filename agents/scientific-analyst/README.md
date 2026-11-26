# Scientific Analyst

Runs bounded descriptive statistics and returns unchanged replayable analysis records for scientific tables.

## Install

Install science-evidence, science-literature and science-statistics first, then scientific-analyst. This agent requires science-evidence and science-statistics.

## Limits

Use public or synthetic data only. This agent gives no clinical, diagnostic, dosing or wet-lab instructions, starts no compute jobs and sends no notifications. Evidence is not stored in memory. Units, experimental-unit column, groups, missing-value policy and method must be stated before calculation. Repeated units are flagged; the methods treat rows as independent. The skill does not calculate p-values or confidence intervals, or establish causality. It can adjust supplied p-values.

Provenance is tool-reported. Verification checks consistency only; it does not authenticate execution or validate a method. A domain expert must accept method suitability. Agent behaviour has not yet been verified by live evaluation; this package is not published. Live evaluation is required before publishing.

Licensed under the MIT License; see LICENSE.
