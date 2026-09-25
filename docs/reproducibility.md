# Reproducibility Standards

Every reported result should be reproducible by another team member from the repository and approved data locations.

## Required experiment record

- Method name, paper, repository URL, and exact commit or release.
- Dataset name, sequence, checksum or archive version, and any crop or conversion.
- Environment specification and installation notes.
- Full command or configuration used.
- Random seed, when applicable.
- Hardware, runtime, peak memory if available, and job identifier.
- Raw method output location.
- Evaluation command and resulting metrics.
- Notes on failures, warnings, and deviations from the publication.

## Suggested naming

```text
runs/<date>_<method>_<dataset>_<short-description>/
```

Keep a small metadata file in each run directory, for example:

```yaml
method: ultrack
method_commit: TBD
dataset: Fluo-N3DH-CHO
sequence: "01"
config: configs/ultrack/cho_baseline.toml
seed: null
cluster_job_id: TBD
notes: Published/default configuration where available.
```

Large run directories belong on the cluster. Commit only lightweight summaries, plots, tables, and the configuration needed to regenerate them.

## Reproducing a paper result

An exact numerical match may be impossible because of unpublished preprocessing, dependency changes, hardware differences, nondeterminism, or unavailable trained weights. Report:

1. the published value;
2. the reproduced value;
3. the known differences in setup; and
4. the most likely explanation for any discrepancy.

Transparent partial reproduction is more useful than an undocumented number that happens to be close.
