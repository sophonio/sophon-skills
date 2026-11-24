---
id: eng-perf-measure
summary: Measurement terms, fixing the conditions of a baseline, the A/A noise test, a reporting table, web vitals thresholds.
reviewed: 2026-11
---
# Measuring performance: baselines, noise, reporting

## Terms

| Term | Meaning |
|---|---|
| wall time | elapsed time a person waits, including I/O and waiting on locks |
| CPU time | time the processor spent on the work; lower than wall time when the work waits |
| latency | time for one operation; reported as percentiles |
| p50, p95, p99 | the value that 50, 95 or 99 percent of runs stay under; the tail matters to users more than the mean |
| throughput | operations per unit of time at a stated concurrency |
| cold and warm | first run (empty caches, JIT not done) against later runs; report which one |
| median | middle value of the runs; robust to one slow outlier, unlike the mean |
| spread | how far runs differ: the range (max - min) or the median absolute deviation |

## Baseline

Fix and write down, before the first run:

- operation: the exact command or request, and what counts as done;
- input: the data set and its size (rows, bytes, items);
- metric: wall time, p95 latency, peak memory, bundle bytes;
- machine: CPU, core count, memory, OS, power mode; the same machine for before and after;
- build: release or optimised mode, same flags, same runtime version;
- state: warm-up runs discarded (state how many), caches cleared or primed the same way each time;
- load: no other heavy process running; the same concurrency.

Run before and after alternately (A B A B ...) when possible, so drift in the machine affects both sides.

## Noise test

Run the baseline against itself (A/A): two sets of 5 runs of the same build. The gap between their medians is the noise floor. A before-and-after difference smaller than the A/A gap, or smaller than the spread of either set, is not a measured change. When the spread is above about 5 percent of the median, find the source (thermal throttling, background jobs, network) before comparing.

## Reporting

| Operation | Input | Metric | Before median (spread) | After median (spread) | Change | A/A gap |
|---|---|---|---|---|---|---|
| `npm run build` | full repo | wall time | 41.2 s (1.1 s) | 33.8 s (0.9 s) | -18% | 0.6 s |
| `GET /orders?limit=50` | 10k orders | p95 latency | 180 ms (12 ms) | 176 ms (14 ms) | -2%, within noise | 9 ms |

Each row names the runs (5 each), the machine and the commits compared.

## Web vitals {#web-vitals}

Field thresholds at the 75th percentile of page loads: Largest Contentful Paint at most 2.5 s, Interaction to Next Paint at most 200 ms, Cumulative Layout Shift at most 0.1. A lab run on one machine is evidence about a lab run; it is not field data.
