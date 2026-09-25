# Evaluation and Annotation

## CTC evaluation

CTC separates segmentation quality from detection and temporal linking:

- **SEG** evaluates cell or nucleus boundaries using reference instance masks.
- **DET** evaluates whether the correct objects were detected.
- **TRA** evaluates track identity, temporal links, and lineage relationships.

Use the [official CTC evaluation methodology and software](https://celltrackingchallenge.net/evaluation-methodology/) for reproduced benchmark results. A Python implementation is available at [CellTrackingChallenge/py-ctcmetrics](https://github.com/CellTrackingChallenge/py-ctcmetrics).

## Fair parameter experiments

- Define the evaluation sequences before tuning.
- Keep a fixed evaluation subset.
- Start from published/default parameters.
- Change only a small number of interpretable parameters.
- Preserve every configuration and random seed.
- Report runtime and failures, not only the best score.

Avoid repeatedly tuning on the same small test subset and then presenting that subset as an unbiased evaluation.

## UChicago data validation

Full CTC-quality annotation of an entire 3D movie is outside the project scope. Use a tiered plan:

1. **Qualitative review:** overlay tracks on the raw movie and document obvious failures.
2. **Tracking-focused annotation:** in selected regions and time windows, mark cell centers or compact regions, maintain identities through time, and record divisions when present.
3. **Segmentation-focused annotation:** draw complete masks for a smaller set of cells and frames only if boundary accuracy matters.

Possible failure categories include missed cells, false detections, merged or split instances, identity switches, broken tracks, incorrect links, and incorrect division events.

Select representative regions before comparing method outputs. Record who annotated or reviewed each subset and preserve annotation provenance. The exact size should be chosen after inspecting cell density and annotation difficulty; it should not be promised in advance.

## Reporting

For every method/dataset pair, report:

- CTC metrics when available;
- dataset and sequence identifiers;
- parameter configuration;
- runtime and hardware;
- qualitative examples;
- major failure modes;
- whether the result used published weights, retraining, or parameter adaptation.
