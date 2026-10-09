# Reproducible incident replay evaluation

This repository includes eight small, synthetic incidents in
[`evals/incidents.json`](../evals/incidents.json). The labels and scenarios are authored for this
portfolio project and are fully inspectable. They contain no production logs.

The comparison answers one narrow question: does aggregating repeated evidence across the incident
outperform classifying only the first highest-severity event?

| Method | Diagnosis accuracy | Root-cause node accuracy |
|---|---:|---:|
| Single highest-severity event baseline | 5/8 (62.5%) | not reported as a target metric |
| Evidence-aggregation workflow | 8/8 (100%) | 8/8 (100%) |

Three cases contain an intentionally ambiguous critical symptom following two corroborating error
events. The baseline follows the critical symptom; the workflow ranks repeated evidence first and
then severity. The other five cases are direct matches, including one unknown case.

## Per-case results

| Case | Expected | Baseline | Workflow |
|---|---|---|---|
| heartbeat-control-plane | control-plane connectivity | correct | correct |
| authentication-clock | credential or clock | correct | correct |
| transport-loss | transport degradation | correct | correct |
| database-saturation | database saturation | correct | correct |
| unknown-software-fault | unknown | correct | correct |
| ambiguous-loss-before-heartbeat | transport degradation | wrong: control-plane | correct |
| ambiguous-auth-before-heartbeat | credential or clock | wrong: control-plane | correct |
| ambiguous-db-before-packet-loss | database saturation | wrong: transport | correct |

Reproduce the machine-readable report:

```bash
telecom-log-eval evals/incidents.json
```

## What this result does not establish

- It is not an evaluation on real carrier data or an independently labelled public benchmark.
- It does not measure LLM reasoning; both methods are deterministic.
- Exact runbook phrases appear in the synthetic messages.
- Eight cases are too few for a production accuracy claim.
- The test demonstrates a regression harness and an explainable comparison, not field performance.

A stronger follow-up should add paraphrases, partial observations, unseen failure classes, topology
ground truth, temporal windows, multiple human annotators, and a frozen holdout set.
