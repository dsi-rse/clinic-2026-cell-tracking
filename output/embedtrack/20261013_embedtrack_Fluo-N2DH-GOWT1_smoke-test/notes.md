# EmbedTrack smoke test: deviations and failed attempts

The 2021 EmbedTrack code needed these changes to run on the current stack (details in embedtrack_library_patches.diff):
- tifffile: `imsave` is gone, so use `imwrite`; the compression option format changed.
- numpy: `np.int`, `np.bool` and `np.object` were removed.
- Python: `collections.Iterable` moved to `collections.abc`.
- Preview-image plotting (visualize.py) breaks on current PyTorch with a CPU/GPU device mismatch. For the smoke test, previews are turned off (DISPLAY=False, DISPLAY_IT=None in train_gowt1.py).

Job failures before the successful run 2150626 (full list in slurm_jobs.txt):
- Missing package path (embedtrack not importable) and missing scikit-image.
- Read-only dataset folders (permissions).
- The code changes listed above, one per failed run.
- 2150611: node k003 had a faulty GPU (nvidia-smi showed ERR!, CUDA found no GPU). Resubmitted with --exclude=k003.
- 2148512 and 2148535 show COMPLETED in Slurm although Python had failed: the batch script did not yet pass Python's exit status through. It does now (exit $STATUS).
- 2150097 and 2150364 failed at about 1,000 iterations into epoch 0, in the preview plotting (visualize.py device mismatch). This is why previews are off for the smoke test.
