# Design: Sophon Science

Status: approved
Approved: 2026-11-26 via info.request

Request: “We need to research on how claude science works, and lets create agents and skills to compete with it, lets analyze them deelpy and come with a plan on how to implement these skills and agents to allow science to happen in Sophon as well, using all the Sophon features as well.”

## Why

Claude combines scientific instructions and connectors with an execution runtime. Catalogue breadth alone cannot deliver reproducibility. Its reviewer does not rerun analyses or validate method choice ([reviewer documentation](https://claude.com/docs/claude-science/the-reviewer)).

## Goals

Assumption: serve computational biomedical researchers first, using cross-domain evidence foundations.

M1 delivers literature evidence, bounded tabular analysis and a replayable report. M2 adds biological workflows. M3 adds managed compute. M4 adds scientific artifact views. M5 adds opt-in monitoring and integrations.

## Non-goals

M1 excludes clinical/dosing decisions, wet-lab execution, GPU inference, arbitrary code, persistent kernels, new UI, publishing and claims of autonomous scientific validity.

## Constraints

Decision (2026-11-26): create an isolated science family; existing development/video packages remain unchanged (`docs/AGENTS.md:481–484,561–565`).

M1 agents are science-lead, literature-researcher, scientific-analyst and scientific-reviewer. Only the lead delegates, with at most two concurrent research tracks followed by review; solo remains available. Delegation allowlists require manual setup.

M1 skills are science-literature, science-statistics and science-evidence. They use standard-library single entrypoints, bounded payloads and no persistent-workspace assumption (`CONTRIBUTING.md:32–35`). No new dependencies.

Literature uses fixed HTTPS PubMed, Europe PMC and Crossref endpoints, validated redirects and no caller URLs. Limits are 100 records per request, a 10-second HTTP timeout and one HTTP attempt per call. Rate-limit responses return retry metadata. The lead serializes provider calls; aggregate rate enforcement requires runtime verification.

Numerical inputs are limited to 1 MiB, 5,000 rows and 64 columns per call. Methods are descriptives, two-group mean difference and Benjamini–Hochberg correction of supplied p-values. Units, missingness policy, experimental units and groups are explicit. Reject NaN/infinity, count nulls and flag repeated experimental units. Do not infer independence or causality.

Evidence records include schema/tool versions, source identifiers, retrieval dates, input/output hashes, parameters, observed interpreter version, results, claim-to-source spans, review findings and limitations. Unknown licences, retraction status and database releases remain unknown. Label preprints and retractions; identifier resolution is not claim support.

M1 provenance is tool-reported, not authenticated. Evidence verification checks consistency only. Numerical replay recomputes registered methods through science-statistics; it is not independent methodological validation. Separate reviewer checks and human acceptance of method suitability remain necessary.

Use public/synthetic data initially. Keep secrets, patient data and evidence out of shared memory. External notifications and paid compute require separate opt-in.

## Approaches and chosen

Choose bounded executable packages followed by runtime integration. Reject prompt-only breadth as insufficient evidence and runtime-first parity as dependent on another repository.

## Left to the builder

Each milestone needs its own approved plan with exact schemas, fixture oracles, paths and commands before implementation.

M3 requires app-source verification of kernels, persistence, approval and egress enforcement. Defaults are zero paid jobs and no sequence uploads. Job approvals must bind inputs, code and resources; submission idempotency, cancellation, reconnection and authoritative audit capture belong to runtime.
