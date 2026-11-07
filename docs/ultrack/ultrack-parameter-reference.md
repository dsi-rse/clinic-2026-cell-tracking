# Ultrack parameter reference

This document is the master reference for parameters in the project's
segmentation-to-tracking workflow. It explains what each parameter controls,
where its default comes from, and the documented numerical limits when those
limits exist.

Experimental settings and results belong in
[Ultrack parameter analysis](ultrack-parameter-analysis.md). This reference
should describe parameters independently of whether the project has tested
them yet.

## Scope and versioning

Parameter defaults can change between package versions, and some pretrained
models load their own defaults. Every table in this document should therefore
identify which of these sources provides a default:

- **Package default:** the value in the documented Python API for the recorded
  package version.
- **Model default:** a value stored with a particular pretrained model.
- **Project default:** the value explicitly supplied by this project's scripts.
- **Dataset-specific value:** a value selected from image metadata or measured
  cell properties; this is not a universal default.

The current project environments use:

| Component | Project version or model | Evidence |
| --- | --- | --- |
| Ultrack | 0.8.0 | [`environments/ultrack.yaml`](../../environments/ultrack.yaml) |
| Cellpose 2D | Cellpose 3.1.1.3 with `cyto2` | [`environments/ultrack-cellpose.yaml`](../../environments/ultrack-cellpose.yaml) and [`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py) |
| Cellpose 3D | Cellpose 4.2.1.1 with `cpsam` | [`run_3d_cellpose.py`](../../scripts/ultrack/run_3d_cellpose.py) |
| StarDist 2D | StarDist 0.9.2 with `2D_versatile_fluo` | [`environments/ultrack-stardist.yaml`](../../environments/ultrack-stardist.yaml) and [`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py) |
| Watershed | SciPy and scikit-image implementation used by the project | [`ultrack_2d.py`](../../src/cell_tracking/ultrack_2d.py) |

When a package, model, or project default differs, the table should record all
relevant values instead of presenting one of them as universal.

## Workflow

The project uses the following sequence:

```text
raw image
    |
    v
segmentation method
    |  instance-label image
    v
label-to-contour conversion
    |  foreground and contour maps
    v
Ultrack segmentation
    |  candidate segment hypotheses for each frame
    v
Ultrack linking
    |  candidate links between adjacent frames
    v
Ultrack tracking solver
    |  selected segments, tracks, and divisions
    v
optional track post-processing
```

These stages should be kept separate. For example, Cellpose's
`cellprob_threshold` changes the masks supplied to Ultrack, while Ultrack's
`segmentation_config.threshold` binarizes Ultrack's foreground map. Their
similar names do not mean they operate on the same values.

## How to read the parameter tables

Each subsection will use this table format:

| Parameter | What it does | Default and source |  Minimum |  Maximum | Effect| Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `example_parameter` | One sentence describing the parameter's direct role. | Package, model, project, or dataset-specific value | Smallest accepted value, if documented | Largest accepted value, if documented | Expected lower-versus-higher trade-off | Untested, tested, or fixed |

The minimum and maximum columns mean **documented accepted limits**, not the
smallest and largest values that are sensible for every dataset.

- Use **Not documented** when the authoritative documentation does not state a
  bound.
- Use **No finite maximum documented** when a parameter is constrained only on
  one side.
- Use **Not applicable** for Boolean, categorical, path, or model-name
  parameters.
- Do not convert a typical value, a paper setting, or one project's search
  range into an API limit.
- Record a practical search range separately in the experiment plan; practical
  ranges depend on cell size, movement, image spacing, and error type.

## 1. Segmentation methods

Segmentation-method parameters act before Ultrack. They determine which cell
pixels and instances are available to the later hierarchy and tracking stages.
Ultrack cannot recover a cell that is completely absent from its foreground
input.

### 1.1 Cellpose 2D

The project uses the high-level Cellpose 3.1.1.3 `Cellpose` class with the
pretrained `cyto2` model. Each HeLa or GOWT1 frame is segmented independently,
and the resulting instance labels are saved before Ultrack processing.

#### Primary segmentation parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `model_type` | Selects the pretrained network and its learned representation of cell appearance. | Cellpose class default: `cyto3`; project: `cyto2`. | Not applicable | Not applicable | Changing the model changes the learned image features and can have a larger effect than adjusting a post-processing threshold. | Fixed to `cyto2` for the current HeLa and GOWT1 runs; models have not been compared in the parameter analysis. |
| `diameter` | Supplies the expected object diameter in pixels, which Cellpose uses to rescale the image before inference. | Cellpose class default: `30`; `None` or `0` requests automatic estimation; project: `None`. | `0` requests automatic estimation | No finite maximum documented | A value below the true diameter can split cells, while a value above it can merge cells; automatic estimation runs the network twice. | Automatic estimation used; fixed diameters have not been tested. |
| `channels[0]` | Selects the image channel to segment. | Cellpose and project: `0`, meaning grayscale. | `0` | `3` | Values select grayscale, red, green, or blue rather than changing a numerical threshold. | Fixed to grayscale because the CTC inputs are single-channel images. |
| `channels[1]` | Selects an optional nuclear channel used alongside the primary channel. | Cellpose and project: `0`, meaning no second channel. | `0` | `3` | A nonzero value supplies an additional red, green, or blue nuclear channel when the model and data support one. | Fixed to no second channel. |
| `flow_threshold` | Rejects masks whose reconstructed flows disagree with the network's predicted flows by more than this error threshold. | Cellpose and project: `0.4`. | `0`, which disables this quality-control step | No finite maximum documented | Lower positive values reject more inconsistent masks; higher values retain more masks, including potentially ill-shaped ones. | Baseline value recorded but not swept. |
| `cellprob_threshold` | Keeps pixels whose pre-sigmoid cell score is strictly greater than this threshold for mask dynamics. | Cellpose and project: `0.0`. | No finite bound documented | No finite bound documented | Lower values admit more pixels and can produce more or larger masks; higher values exclude uncertain or dim pixels and can produce fewer or smaller masks. | Default and implementation meaning verified; threshold has not been swept. |
| `min_size` | Removes completed masks smaller than this number of pixels. | Cellpose API default: `15`; project inherits `15`. | `-1`, which disables removal | No finite maximum documented | Higher values remove more small masks; an excessively high value can remove real small cells. | Inherited package default; not exposed by the current 2D runner. |
| `max_size_fraction` | Removes masks larger than this fraction of the complete image. | Cellpose API default: `0.4`; project inherits `0.4`. | No finite bound documented | No finite bound documented | Lower values reject more very large masks; values that are too low can remove real large cells or merged regions that should be inspected. | Inherited package default; not exposed by the current 2D runner. |
| `niter` | Sets the number of flow-dynamics iterations used to group pixels into masks. | Cellpose API and project: `None`, which chooses a value proportional to diameter. | `0` or `None` selects the automatic value | No finite maximum documented | More iterations can help long objects converge but increase runtime; too few can leave incomplete masks. | Automatic value inherited; not exposed by the current 2D runner. |

At `cellprob_threshold=0`, Cellpose does not accept zero-probability pixels or
disable filtering. The network output is a score supplied to a sigmoid, and
the implementation uses pixels whose score is strictly greater than zero.
Mask formation still depends on the flow dynamics, flow-quality filtering,
and size filtering.

#### Fixed and operational settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `gpu` | Selects GPU execution when a supported device is available. | Cellpose and project CLI default: `False`; enabled with `--cellpose-gpu`. | Not applicable | Not applicable | Primarily changes runtime and available memory rather than the intended segmentation method. | GPU execution is optional and recorded for each run. |
| `do_3D` | Chooses true volumetric inference instead of independent 2D segmentation. | Cellpose and project: `False`. | Not applicable | Not applicable | Enabling it changes the dimensional algorithm and makes several 2D settings behave differently. | Fixed to 2D in this workflow. |
| `normalize` | Scales each image channel using its first and ninety-ninth intensity percentiles before inference. | Cellpose API and project: `True`. | Not applicable | Not applicable | Disabling normalization makes inference depend directly on the input intensity scale; changing percentiles alters contrast. | Inherited package default; not exposed by the current 2D runner. |
| `invert` | Inverts normalized intensities for images containing dark cells on a bright background. | Cellpose API and project: `False`. | Not applicable | Not applicable | Enabling it reverses bright and dark structures before inference. | Fixed implicitly to `False`. |
| `resample` | Runs mask dynamics on flows resampled to the original image size. | Cellpose API and project: `True`. | Not applicable | Not applicable | `True` generally gives smoother boundaries at additional cost; `False` can be faster for large objects. | Fixed implicitly to `True`. |
| `batch_size` | Controls how many image patches are evaluated together. | Cellpose API and project: `8`. | No bound documented | No finite maximum documented | Larger batches may improve throughput but require more memory; this should not intentionally change segmentation. | Fixed implicitly to `8`. |
| `augment` | Uses overlapping flipped tiles during inference. | Cellpose API and project: `False`. | Not applicable | Not applicable | Enabling it increases computation and may reduce tile-edge artifacts. | Fixed implicitly to `False`. |
| `tile_overlap` | Sets the fractional overlap between inference tiles. | Cellpose API and project: `0.1`. | `0.05` effective minimum | `0.5` effective maximum | More overlap adds redundant context and computation; too little overlap can make tile boundaries more visible. Values outside the effective range are clamped by Cellpose. | Fixed implicitly to `0.1`. |
| `bsize` | Sets the square inference-tile size in pixels for Cellpose 3 models. | Cellpose API and project: `224`. | No bound documented | No finite maximum documented | The documentation recommends retaining the training tile size; changing it affects memory and tiling context. | Fixed implicitly to `224`. |
| `interp` | Interpolates the predicted flow field during 2D mask dynamics. | Cellpose API and project: `True`. | Not applicable | Not applicable | Disabling interpolation changes how pixels move through the flow field and can make boundaries less smooth. | Fixed implicitly to `True`. |
| `compute_masks` | Determines whether Cellpose converts predicted flows and cell scores into instance masks. | Cellpose API and project: `True`. | Not applicable | Not applicable | `False` returns network outputs without the masks needed by this workflow. | Required and fixed to `True`. |

Sources for this subsection are the exact Cellpose 3.1.1.3 wheel, the official
[Cellpose 3 settings guide](https://cellpose.readthedocs.io/en/v3.1.1.1/settings.html),
the version-matched [Cellpose API](https://cellpose.readthedocs.io/en/v3.1.1.1/api.html),
and the project's [`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py)
and [`ultrack_2d.py`](../../src/cell_tracking/ultrack_2d.py).

### 1.2 Cellpose 3D

The project uses Cellpose 4.2.1.1 `CellposeModel` with the pretrained `cpsam`
model. Each CTC `ZYX` time point is processed independently using true 3D
inference. The project adds a singleton channel axis, identifies the `Z` and
channel axes explicitly, and normalizes across the complete volume. Cellpose 4
pads the project's single image channel with zero-valued channels to form the
three-channel input expected by the model.

Cellpose 2D and 3D are separate subsections because they use different major
versions, models, dimensional settings, and project scripts.

#### Primary segmentation parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `pretrained_model` | Selects the Cellpose 4 network weights used to predict flows and cell scores. | Cellpose 4.2.1.1 package default: `cpsam_v2`; project: `cpsam`. | Not applicable | Not applicable | Changing the model changes the learned representation and may change both missed cells and spurious masks. | Fixed to the mentor's `cpsam` approach; model variants have not been compared. |
| `diameter` | Supplies the expected XY cell diameter in pixels and determines the image rescaling relative to a 30-pixel model diameter. | Cellpose API default: `None`; project: required dataset-specific value. | Greater than `0` in the project runner | No finite maximum documented | A smaller supplied diameter increases the rescaling factor and can encourage smaller or split masks; a larger value can encourage larger or merged masks. | Required but not yet systematically tuned; should be measured from each dataset. |
| `anisotropy` | Supplies the ratio of Z spacing to XY spacing so the volume can be rescaled for 3D inference. | Cellpose API default: `None`; project: required dataset-specific value. | Greater than `0` in the project runner | No finite maximum documented | Values above one upsample a more coarsely sampled Z axis relative to XY; an incorrect ratio distorts 3D shape and distance. | Required and taken from image metadata; sensitivity has not been tested. |
| `cellprob_threshold` | Keeps voxels whose cell score is strictly above the threshold for 3D mask dynamics. | Cellpose and project: `0.0`. | No finite bound documented | No finite bound documented | Lower values admit more voxels and can recover dim regions while adding background; higher values are more selective and can fragment or remove dim cells. | Baseline value used; not yet tuned for the 3D datasets. |
| `flow3D_smooth` | Applies Gaussian smoothing to the predicted 3D flow field in Z, Y, and X before mask construction. | Cellpose API and project: `0`, meaning no flow smoothing. | `0` | No finite maximum documented | Increasing it can reduce Z fragmentation or ring artifacts but can blur real motion boundaries; a three-value list controls ZYX independently. | Important candidate for 3D fine-tuning, but the current runner does not expose it. |
| `min_size` | Removes completed 3D masks smaller than this number of voxels. | Cellpose and project: `15`. | Cellpose supports `-1` to disable; project runner requires `0` or greater | No finite maximum documented | Higher values remove more small masks and debris but can remove real small cells. | Exposed by the project runner; only the default is documented so far. |
| `max_size_fraction` | Removes masks larger than this fraction of the complete volume. | Cellpose API default: `0.4`; project inherits `0.4`. | No finite bound documented | No finite bound documented | Lower values reject more very large masks; a value that is too low can remove real large or temporarily merged cells. | Inherited package default; not exposed by the current 3D runner. |
| `niter` | Sets the number of flow-dynamics iterations used to form masks from the 3D flows. | Cellpose API and project: `None`, which chooses an automatic value based on rescaling. | `0` or `None` selects the automatic value | No finite maximum documented | More iterations may help elongated cells converge but increase runtime; too few can leave incomplete masks. | Automatic value inherited; not exposed by the current 3D runner. |
| preprocessing `sigma` | Applies Gaussian smoothing to the raw ZYX volume before it is passed to Cellpose. | Project default: `[0, 0, 0]`, meaning no smoothing. This is a project preprocessing parameter, not `CellposeModel.eval`. | `0` for each axis | No finite maximum documented | Increasing one axis suppresses noise along that axis but can erase small structures or merge nearby cells. | Exposed by the project runner; default used in the completed MDA231 run. |
| `tile_norm_blocksize` | Enables local tiled intensity normalization using a window of this many pixels when greater than zero. | Cellpose and project: `0`, meaning no tiled normalization. | `0` | No finite maximum documented | Smaller positive windows normalize more locally; larger windows approach global normalization, while zero disables tiling. | Exposed by the project runner; default used so far. |
| `norm3D` | Chooses one normalization across the full Z stack instead of normalizing slices independently. | Cellpose 4 and project: `True`. | Not applicable | Not applicable | `True` preserves relative intensity differences across Z; slice-wise normalization can brighten weak planes independently. | Explicitly fixed to `True` by the project. |
| normalization percentiles | Set the lower and upper intensity percentiles mapped to the normalized range. | Cellpose defaults inherited by the project: first and ninety-ninth percentiles. | `0` | `100` | Moving the bounds inward increases contrast and clipping; moving them outward preserves more extreme intensities. | Inherited defaults; not exposed by the current runner. |
| `flow_threshold` | Normally removes masks with inconsistent predicted and reconstructed flows. | Cellpose API default: `0.4`; project does not pass a value. | `0` disables the check | No finite maximum documented | Cellpose does not apply this flow-quality filter during true 3D mask construction, so changing it should not affect this workflow. | Not a 3D tuning parameter for the current `do_3D=True` workflow. |

The raw-image preprocessing `sigma` and Cellpose's `flow3D_smooth` operate at
different points. The former blurs input intensities before inference; the
latter smooths the network's predicted flow field before mask dynamics. They
should be documented and tested separately.

#### Fixed and operational settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `do_3D` | Activates true volumetric inference and 3D mask dynamics. | Cellpose API default: `False`; project: `True`. | Not applicable | Not applicable | Enabling it changes the algorithm from independent 2D masks to volumetric flow prediction and mask construction. | Required and fixed to `True`. |
| `channel_axis` | Identifies the input axis containing image channels. | Cellpose API default: `None`; project: `-1`. | Not applicable | Not applicable | An incorrect axis changes how the volume is interpreted and can invalidate inference. | Explicitly fixed to the last axis. |
| `z_axis` | Identifies the input depth axis. | Cellpose API default: `None`; project: `0`. | Not applicable | Not applicable | An incorrect axis prevents Cellpose from treating the volume as ZYX data. | Explicitly fixed to the first axis. |
| `gpu` | Selects GPU execution when a supported device is available. | Cellpose and project CLI default: `False`; enabled with `--gpu`. | Not applicable | Not applicable | Primarily changes runtime and memory capacity; it should not intentionally change the method. | Optional, validated against CUDA availability, and recorded in `run.json`. |
| `use_bfloat16` | Loads compatible model weights and performs network inference with 16-bit brain floating-point precision instead of 32-bit precision. | Cellpose 4.2.1.1 and project: `True`. | Not applicable | Not applicable | Reduces accelerator memory and may improve throughput, with small numerical differences from 32-bit inference. | Inherited package default; not exposed by the current runner. |
| `batch_size` | Controls how many 256-pixel image patches are evaluated together. | Cellpose API signature: `8`; project: `1`. | `1` in the project runner | No finite maximum documented | Larger values may increase throughput but consume more accelerator memory; this should not intentionally change masks. | Reduced to `1` for the project's 3D memory requirements. |
| `normalize` | Enables intensity normalization before network inference. | Cellpose and project: `True`. | Not applicable | Not applicable | Disabling it makes inference depend directly on the source intensity scale and bypasses `norm3D` and tiled normalization. | Explicitly enabled through the normalization dictionary. |
| `resample` | Resamples predicted flows and cell scores to the original image shape before mask dynamics. | Cellpose API and project: `True`. | Not applicable | Not applicable | `True` retains mask construction at the original resolution at additional cost. | Fixed implicitly to `True`. |
| `augment` | Uses overlapping flipped tiles during network inference. | Cellpose API and project: `False`. | Not applicable | Not applicable | Enabling it increases computation and may reduce tile-edge artifacts. | Fixed implicitly to `False`. |
| `tile_overlap` | Sets the fractional overlap between network inference tiles. | Cellpose API and project: `0.1`. | `0.05` effective minimum | `0.5` effective maximum | More overlap increases redundant context and computation; too little overlap can expose tile boundaries. Values outside the effective range are clamped by Cellpose. | Fixed implicitly to `0.1`. |
| `bsize` | Selects the network tile size; `cpsam` requires 256-pixel tiles. | Cellpose API: `None`, resolved to `256` for `cpsam`; project inherits this behavior. | `256` for `cpsam` | `256` for `cpsam` | Cellpose 4.2.1.1 raises an error if a different size is requested for the SAM backbone. | Fixed by the selected model. |
| `stitch_threshold` | Enables a separate workflow that segments planes in 2D and stitches overlapping masks across Z. | Cellpose and project: `0.0`. | `0` disables stitching | No finite maximum documented | Positive values apply 2D stitching, but that is a different approach from the project's true `do_3D=True` inference. | Fixed to the inactive default and not part of this workflow. |
| `compute_masks` | Determines whether Cellpose converts flows and scores into instance masks. | Cellpose and project: `True`. | Not applicable | Not applicable | `False` returns network predictions without the instance labels required by Ultrack. | Required and fixed to `True`. |

Sources for this subsection are the exact Cellpose 4.2.1.1 wheel, the official
[Cellpose 4 API](https://cellpose.readthedocs.io/en/latest/api.html), the
[Cellpose 4 CLI reference](https://cellpose.readthedocs.io/en/latest/cli.html),
and the project's [`run_3d_cellpose.py`](../../scripts/ultrack/run_3d_cellpose.py)
and [`cellpose_3d.py`](../../src/cell_tracking/cellpose_3d.py).

### 1.3 StarDist 2D

The project uses StarDist 0.9.2 with the pretrained `2D_versatile_fluo`
model. Each frame is first normalized with Ultrack, then segmented independently
with `StarDist2D.predict_instances_big`. StarDist predicts an object-probability
score and radial distances to the boundary at each candidate point, converts
them into star-convex polygons, and uses non-maximum suppression to remove
overlapping duplicate candidates.

#### Primary segmentation and preprocessing parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `model_name` | Selects the pretrained network and the cell appearance and shapes learned during training. | Project: `2D_versatile_fluo`, a StarDist model trained for single-channel fluorescent nuclei. | Not applicable | Not applicable | Changing the model changes the learned image representation and can have a larger effect than changing a post-processing threshold. | Fixed to `2D_versatile_fluo`; pretrained models have not been compared. |
| `prob_thresh` | Admits only candidate points whose predicted object probability is strictly greater than this threshold. | `2D_versatile_fluo` model default: `0.479071`; StarDist fallback when no valid model threshold is available: `0.5`; the standard project runner inherits the model value. | `0` on the probability scale; a stored model default must be greater than `0` | `1` on the probability scale; a stored model default must be less than `1` | Lower values admit more uncertain candidates and may recover missed cells while adding false detections; higher values admit fewer candidates and may miss dim cells. NMS means the final object count need not change monotonically. | HeLa `0.4`, `0.479071`, and `0.6` sweep complete on both sequences; GOWT1 sweep pending. |
| `nms_thresh` | Sets the overlap above which a lower-scoring candidate polygon is suppressed as a duplicate of a higher-scoring polygon. | `2D_versatile_fluo` model default: `0.3`; StarDist fallback when no valid model threshold is available: `0.4`; the standard project runner inherits the model value. | `0` on the overlap scale; a stored model default must be greater than `0` | `1` on the overlap scale; a stored model default must be less than `1` | Lower values suppress overlaps more aggressively and can remove nearby real cells; higher values permit more overlap and can retain duplicate detections. | Independent `0.2`, `0.3`, and `0.4` sweep planned for HeLa and GOWT1; no results reported yet. |
| preprocessing `gamma` | Raises Ultrack-normalized intensities to this power before StarDist inference. | `ultrack.imgproc.normalize` requires a value; project: `1.0`, which leaves normalized intensities unchanged. This is not a StarDist model parameter. | No bound documented | No finite bound documented | For intensities between zero and one, values below one brighten intermediate intensities and values above one darken them; invalid or extreme exponents can produce unusable inputs. | Fixed to `1.0`; not exposed by the current runner. |
| preprocessing `lower_q` | Selects the lower image-intensity quantile that is mapped to zero during Ultrack normalization. | Ultrack 0.8.0 and project: `0.001`. | `0` | `1` | Increasing it clips more dark pixels and background but can remove dim cell signal; decreasing it retains more of the dark tail. | Inherited Ultrack default; not exposed or tested. |
| preprocessing `upper_q` | Selects the upper image-intensity quantile that is mapped to one during Ultrack normalization. | Ultrack 0.8.0 and project: `0.9999`. | `0` | `1` | Decreasing it saturates more bright pixels and increases contrast below the cutoff; increasing it gives bright outliers more influence. It should remain above `lower_q`. | Inherited Ultrack default; not exposed or tested. |
| `scale` | Optionally rescales the image internally before inference and rescales the predicted polygons back to the original coordinates. | StarDist and project: `None`, meaning no internal rescaling. | Greater than `0` when supplied | No finite maximum documented | Values below one make cells appear smaller to the model and values above one make them appear larger, while also changing memory use and detail. | Fixed implicitly to `None`; object-size rescaling has not been tested. |

`prob_thresh` and `nms_thresh` are separate controls. The first decides which
candidate points can enter polygon construction; the second resolves overlap
among the candidates that entered. The values loaded from `thresholds.json`
belong specifically to `2D_versatile_fluo`. They are not universal StarDist
defaults and are not thresholds on raw fluorescence intensity. They also act
before the later Ultrack segmentation, linking, and tracking stages.

The project's parameter-analysis runner can explicitly override both
thresholds. The ordinary benchmark runner passes neither one, so StarDist uses
the loaded model values. StarDist's console message calls both cases “default
values”; this document distinguishes the pretrained model values from the
package fallbacks.

#### Large-image and fixed inference settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `axes` | Declares the meaning and order of the input image axes. | Required by `predict_instances_big`; project: `YX`. | Not applicable | Not applicable | An incorrect value makes StarDist interpret dimensions incorrectly. | Fixed to `YX` for each single-channel 2D frame. |
| `block_size` | Sets the height and width of the blocks processed by `predict_instances_big`. | No package default because the argument is required; project: `560` pixels on both axes. | Must be greater than `min_overlap + 2 * context` and compatible with the model grid | The corresponding image-axis length | Larger blocks reduce block boundaries but require more memory; smaller blocks use less memory and create more overlap work. When the blocking assumptions hold, this setting should not intentionally change segmentation. | Fixed to `560`; not tested as a scientific parameter. |
| `min_overlap` | Guarantees this much overlap between adjacent blocks and must exceed the size of every predicted object. | No package default because the argument is required; project: `96` pixels on both axes. | `0` | Less than `block_size - 2 * context` | More overlap supports larger objects crossing block boundaries but increases repeated computation; too little overlap violates StarDist's assembly assumption and can raise an error or mishandle large objects. | Fixed to `96`; adequacy should be checked against the largest predicted cells. |
| `context` | Adds image context around each block and discards that margin when assembling the output. | StarDist and project: `None`, which requests the model's automatic receptive-field estimate. | `0` when supplied | Less than `(block_size - min_overlap) / 2` | More context reduces prediction-edge effects but leaves a smaller writable region and requires more computation. | Automatic estimate inherited; not exposed by the current runner. |
| `normalizer` | Optionally applies a CSBDeep normalizer inside StarDist before prediction. | StarDist and project: `None`, which assumes the input is already normalized. | Not applicable | Not applicable | Supplying another normalizer would change contrast and could normalize the image a second time. | Correctly left as `None` because the project calls `ultrack.imgproc.normalize` first. |
| `sparse` | Stores only above-threshold candidate predictions during tiled inference to reduce memory use. | StarDist and project: `True`, the recommended setting. | Not applicable | Not applicable | `False` retains dense predictions and uses more memory; it is required only for some diagnostic return modes. | Fixed implicitly to `True`. |
| `n_tiles` | Splits each StarDist prediction block into an additional number of inner tiles per image axis. | StarDist and project: `None`, meaning no inner tiling. | `1` per axis when supplied | No finite maximum documented | More tiles can prevent out-of-memory errors but add overlap work; this is separate from `predict_instances_big` blocks. | Fixed implicitly to `None`; the outer block workflow provides the current memory control. |
| `labels_out_dtype` | Selects the data type allocated for the assembled instance-label image. | StarDist and project: NumPy `int32`. | Not applicable | Not applicable | A type with too few positive values can overflow when an image contains many objects; it should not otherwise change masks. | Inherited default and compatible with the project's label array. |
| `show_progress` | Controls the progress bar for block processing. | StarDist default: `True`; project: `False`. | Not applicable | Not applicable | Changes console output only, not segmentation. | Explicitly disabled by the project. |

`block_size`, `min_overlap`, and `context` are primarily execution and assembly
settings, not substitutes for `prob_thresh` or `nms_thresh`. StarDist states
that `predict_instances_big` should match whole-image prediction only when all
predicted objects are smaller than `min_overlap` and
`min_overlap + 2 * context < block_size`. The block size must also fit within
each image axis and the values are rounded upward when necessary to match the
model grid.

Sources for this subsection are the exact StarDist 0.9.2 and Ultrack 0.8.0
packages, the official StarDist
[`predict_instances` and `predict_instances_big` source](https://github.com/stardist/stardist/blob/0.9.2/stardist/models/base.py),
the version-matched [NMS implementation](https://github.com/stardist/stardist/blob/0.9.2/stardist/nms.py),
the official [pretrained-model list](https://github.com/stardist/stardist#pretrained-models-for-2d),
the Ultrack [`normalize` API](https://royerlab.github.io/ultrack/api.html#ultrack.imgproc.normalize),
and the project's [`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py),
[`ultrack_2d.py`](../../src/cell_tracking/ultrack_2d.py), and
[`segmentation_parameters.py`](../../src/cell_tracking/segmentation_parameters.py).

### 1.4 Watershed

The project implements a marker-controlled 2D watershed for bright cells. It
does not use a pretrained model. Every frame follows this sequence:

```text
raw image
    -> Gaussian smoothing
    -> per-frame Otsu threshold (`smoothed > threshold`)
    -> remove small foreground components
    -> optionally fill enclosed foreground holes
    -> Euclidean distance transform
    -> h-maxima seed detection
    -> connected-component marker labels
    -> watershed on the negative distance map inside the foreground
```

These parameters affect the instance labels supplied to Ultrack; they are not
members of Ultrack's later `SegmentationConfig`. Each frame is processed
independently, so neither the threshold nor the watershed uses information from
neighboring time points.

#### Primary segmentation parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `smoothing_sigma` | Sets the Gaussian standard deviation, in pixels, applied to the raw frame before thresholding. | scikit-image `gaussian` default: `1.0`; project: `1.0`. | `0` in the parameter-analysis runner | No finite maximum documented | Lower values preserve more fine detail and noise; higher values suppress noise but blur boundaries, can enlarge connected foreground regions, and can merge nearby cells before watershed. | GOWT1 hole-filled runs at `1.0` and `0.5` are complete; `1.0` performed better. Sigma `0` and the corresponding HeLa comparisons are unreported. |
| foreground threshold method | Computes one Otsu intensity threshold from each smoothed frame and marks only pixels strictly above it as foreground. | Project: `threshold_otsu(smoothed)` independently for every frame; there is no fixed numerical threshold. | Not applicable; data-derived | Not applicable; data-derived | The threshold adapts to each frame's histogram, but a single global value within a frame can miss dim cells or include bright background when illumination is uneven. | Fixed to per-frame Otsu; alternative thresholding methods have not been compared. |
| `minimum_object_size` / `min_size` | Removes 4-connected binary foreground components containing fewer than this number of pixels. | scikit-image default through 0.25: `64`; project: `20`. | `1` in the project runner | No finite maximum documented | Lower values retain more small cells and noise; higher values remove more debris but can delete real small cells before seed detection. | Fixed to `20`; not swept. |
| `fill_holes` | Chooses whether to fill every enclosed background region in each cleaned 2D foreground mask before computing distances and seeds. | SciPy operation is optional; project default: `False`, enabled by `--watershed-fill-holes`. | Not applicable | Not applicable | Enabling it can prevent dark interiors from producing fragmented distance maps, but it can also fill enclosed background gaps between crowded cells. It cannot recover a cell that Otsu excluded entirely. | Plain versus filled GOWT1 comparison complete on both sequences; filling improved all reported aggregate metrics, with crowded-region inspection still important. HeLa results are unreported. |
| h-maxima height `h` | Keeps distance-map maxima whose height is at least `h` and uses them to create watershed seeds. | Project: `2.0` pixels. The CLI and run report call this `h_minima`, but the implementation calls `h_maxima`. | Greater than `0` in the project runner | No finite maximum documented | Lower values retain more shallow peaks and can split one cell with multiple seeds; higher values retain fewer peaks and can merge touching cells under one seed or leave a foreground component unseeded. | Fixed to `2.0`; not swept. The misleading CLI name should not be interpreted as an h-minima operation. |
| watershed `compactness` | Adds a spatial compactness penalty while marker regions expand through the negative distance map. | scikit-image and project: `0`, meaning ordinary watershed with no compactness penalty. | `0` | No finite maximum documented | Higher positive values favor more regularly shaped, spatially compact basins and can move boundaries away from the distance-map ridges. | Fixed implicitly to `0`; not exposed or tested. |

The h-maxima height is expressed in distance-map units. Because the project
uses the distance transform's default unit sampling, those units are pixels.
The CLI name `--watershed-h-minima` is therefore a naming error: increasing it
suppresses shallow **maxima** of the foreground distance map rather than
selecting minima of the raw image.

Hole filling is also order-dependent. It happens after the Otsu foreground and
small-object removal, but before the distance transform. It changes the shape
used to calculate distances and seeds; it does not alter the raw fluorescence
image or rerun small-object removal afterward.

The effective switch is `--watershed-fill-holes`. The benchmark parser also
contains an unused `--fill-hole` argument whose value is never passed to the
segmentation function; changing that argument does not enable or disable hole
filling in the current workflow.

#### Fixed algorithm settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| Gaussian `preserve_range` | Prevents scikit-image from rescaling the raw intensity range before smoothing. | scikit-image default: `False`; project: `True`. | Not applicable | Not applicable | `True` preserves the source intensity units for Otsu; `False` converts according to scikit-image's image-type conventions. | Explicitly fixed to `True`. |
| Gaussian `mode` | Defines how values beyond the image edge are supplied during smoothing. | scikit-image and project: `nearest`. | Not applicable | Not applicable | `nearest` repeats edge pixels; another boundary mode can change smoothing and thresholded shapes near frame borders. | Inherited package default; not exposed. |
| Gaussian `truncate` | Truncates the Gaussian kernel at this many standard deviations from its center. | scikit-image and project: `4.0`. | No bound documented | No finite maximum documented | Lower values use a smaller, faster approximation; higher values use a wider kernel and more closely represent the Gaussian tail. | Inherited package default; not exposed. |
| Otsu `nbins` | Sets the number of histogram bins used to compute the threshold for the floating-point smoothed image. | scikit-image and project: `256`. | No bound documented | No finite maximum documented | More bins give finer histogram resolution at additional cost; too few bins can make the selected threshold coarse. | Inherited package default; not exposed. |
| foreground `connectivity` | Defines which neighboring foreground pixels belong to one component during small-object removal. | scikit-image and project: `1`, meaning 4-connectivity in 2D. | `1` | `2` in 2D | At `1`, diagonal-only contact does not join objects; at `2`, diagonal contact can combine them before size filtering. | Inherited default; not exposed. |
| hole-fill `structure` | Defines which background pixels are connected when deciding whether a region is an enclosed hole. | SciPy and project: `None`, which generates a connectivity-one cross in 2D. | Not applicable | Not applicable | The default treats edge-connected background as open but can treat diagonal-only contact with the border as enclosed; a different structure can change which gaps are filled. | Inherited default whenever `fill_holes=True`; not exposed. |
| distance `sampling` | Sets physical pixel spacing for the Euclidean distance transform. | SciPy and project: `None`, meaning unit spacing on Y and X. | No bound documented | No finite maximum documented | Meaningful supplied spacings are positive; non-unit or unequal values change the relative Y/X distances, seed heights, and watershed geometry. Unit spacing measures distance in pixels. | Fixed implicitly to unit sampling. |
| h-maxima `footprint` | Defines the neighborhood used to identify and compare distance-map maxima. | scikit-image and project: `None`, resolved to a 3-by-3 maximum-norm neighborhood in 2D. | Not applicable | Not applicable | A larger or differently shaped footprint can combine or suppress nearby peaks and therefore change the number of markers. | Inherited default; not exposed. |
| marker-label `structure` | Defines when seed pixels belong to the same connected marker before watershed. | SciPy and project: `None`, resolved to a 4-connected cross in 2D. | Not applicable | Not applicable | Diagonally touching seed pixels remain separate markers under the default; a fully connected structure could merge them. | Inherited default; not exposed. |
| watershed `connectivity` | Defines which neighboring foreground pixels can be reached as each marker floods the negative distance map. | scikit-image and project: `1`, meaning 4-connectivity in 2D. | `1` | `2` in 2D | Higher connectivity permits diagonal flooding and can alter boundaries and tie-breaking between markers. | Inherited default; not exposed. |
| `watershed_line` | Chooses whether watershed boundaries are written as zero-valued separator pixels. | scikit-image and project: `False`. | Not applicable | Not applicable | `False` assigns every foreground pixel to a marker; `True` inserts one-pixel zero-valued lines between basins. | Fixed implicitly to `False`. |

The watershed receives `-distance` as its elevation image, the connected
h-maxima components as markers, and the cleaned foreground as its mask. The
negative sign makes the centers of foreground objects into basins from which
the markers flood outward. If no marker is found in a frame, the project writes
an all-zero label image for that frame rather than calling watershed.

The project environment pins Ultrack but does not pin exact SciPy or
scikit-image versions. Run reports should therefore preserve their installed
versions. In scikit-image 0.26, `min_size` was deprecated in favor of the
oppositely phrased `max_size`; the current project code and table describe the
`min_size` behavior used by the existing workflow: components smaller than 20
pixels are removed.

Sources for this subsection are the project's
[`ultrack_2d.py`](../../src/cell_tracking/ultrack_2d.py),
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py), and
[`segmentation_parameters.py`](../../src/cell_tracking/segmentation_parameters.py),
the versioned scikit-image documentation for
[`gaussian` and `threshold_otsu`](https://scikit-image.org/docs/0.23.x/api/skimage.filters.html),
[`h_maxima` and `remove_small_objects`](https://scikit-image.org/docs/0.23.x/api/skimage.morphology.html),
and [`watershed`](https://scikit-image.org/docs/0.23.x/api/skimage.segmentation.html),
plus the SciPy documentation for
[`binary_fill_holes`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.binary_fill_holes.html),
[`distance_transform_edt`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.distance_transform_edt.html),
and [`label`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.label.html).

## 2. Label-to-contour conversion

This stage converts saved instance labels into the two arrays required by
Ultrack segmentation:

- **Foreground:** a Boolean map of every location where a cell is allowed to
  exist. For one label stack, this is `labels > 0`.
- **Contours:** a floating-point map of boundary evidence. Higher values mark
  more likely separation boundaries; Ultrack uses this map to create competing
  segment hypotheses inside the foreground.

The numerical label IDs do not become Ultrack track IDs. At this stage, zero
means background and every positive integer means foreground; changes between
the positive IDs are used only to locate instance boundaries.

For a single label stack, the conversion is:

```text
instance labels shaped (T, (Z), Y, X)
    |-- labels > 0 ------------------------------> Boolean foreground
    |
    `-- outer boundary pixels
          -> optional spatial Gaussian smoothing
          -> per-frame maximum normalization ---> float32 contours
```

The first axis is always time. Conversion loops over time points and applies
boundary detection and Gaussian smoothing only within each 2D image or 3D
volume; it never smooths information between frames.

### 2.1 Core conversion parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `labels` | Supplies one instance-label time series, or a sequence of equal-shaped label time series, from which foreground and boundaries are derived. | Required by `labels_to_contours`; project inputs are saved Cellpose, StarDist, watershed, or 3D Cellpose labels. | `0` is background in project-validated labels | Limited by the integer label dtype | Positive label values define foreground, while changes between neighboring IDs define boundaries; the magnitude of a positive ID has no confidence meaning. | Required input; project loaders verify shape, integer type, and nonnegative labels before the standard 2D workflow. |
| contour `sigma` | Sets the standard deviation of the Gaussian filter applied to each spatial contour map. | Ultrack default: `None`, meaning no smoothing and no maximum normalization; project 2D default: `4.0`; project 3D default: `(0, 0, 0)` in ZYX order. | `0` in project runners | No finite maximum documented | Lower values keep sharper boundaries; higher values spread boundary evidence over a wider region and can change the hierarchy of candidate segments. A zero value is a no-op blur, while `None` also skips Ultrack's later normalization step. | Cellpose-input 2D sweeps at `4`, `2`, and `0` are complete for HeLa and GOWT1; `0` was best among those tested. Other input methods and ensembles are not fully swept. The 3D value has not been tuned. |
| boundary `mode` | Chooses which side of an instance transition is marked by `find_boundaries`. | Ultrack project implementation: `outer`. | Not applicable | Not applicable | `outer` marks background pixels around objects and also marks the boundary where two labeled objects touch; another mode would place boundary pixels differently. | Fixed inside Ultrack 0.8.0; not exposed by project runners. |
| boundary `connectivity` | Defines which spatial neighbors are inspected for a change in label value. | scikit-image and Ultrack: `1`, meaning edge neighbors in 2D and face neighbors in 3D. | `1` | Number of spatial dimensions | Higher connectivity also inspects diagonal or corner neighbors and can create additional boundary pixels. | Inherited default; not exposed or tested. |
| boundary `background` | Identifies the label value treated as background by outer-boundary detection. | scikit-image and Ultrack: `0`. | Not applicable | Not applicable | Changing it would redefine which labeled region receives the outside boundary; the rest of the project also assumes zero is background. | Fixed implicitly to `0`. |
| Gaussian `mode` | Defines how the contour map is extended beyond its spatial edges during smoothing. | SciPy and Ultrack: `reflect`. | Not applicable | Not applicable | Reflection reduces abrupt edge discontinuities; another mode could alter smoothed contour evidence near image borders. | Inherited default; not exposed. |
| Gaussian `truncate` | Truncates the smoothing kernel at this many standard deviations. | SciPy and Ultrack: `4.0`. | No bound documented | No finite maximum documented | Lower values use a smaller approximation; higher values spread the computation across a wider neighborhood. | Inherited default; not exposed. |
| per-frame contour normalization | Divides a smoothed contour map by its maximum value so the strongest boundary in that frame becomes one. | Applied by Ultrack whenever `sigma` is not `None`; there is no separate public parameter. | Not applicable | Not applicable | Normalization makes contour magnitudes comparable after changing the blur width, but it is relative to each individual time point rather than a sequence-wide scale. | Active for every current project setting, including numeric sigma `0`. |

The official Ultrack example describes smoothing as a way to make the boundary
map more similar to an interior distance-like landscape for segmentation
hypothesis generation. It does not change the saved input labels or rerun the
segmentation model. Changing `sigma` requires rerunning this conversion and all
later Ultrack stages, but not Cellpose, StarDist, or watershed.

Numeric zero and `None` should not be treated as completely interchangeable.
With `sigma=0`, Ultrack still calls the Gaussian filter and divides the result
by its per-frame maximum. With `sigma=None`, it does neither. For a nonempty
single-method binary boundary map, both normally retain sharp zero/one
boundaries. If a frame contains no boundary pixels and sigma is numeric,
Ultrack 0.8.0 divides by zero because it does not guard a zero maximum; the
resulting contour map should be checked for non-finite values.

### 2.2 Segmentation ensembles

The project's 2D ensemble uses the saved watershed, Cellpose, and StarDist
labels. It converts each method separately with the same contour sigma, then
combines the converted maps:

```text
foreground = watershed foreground OR Cellpose foreground OR StarDist foreground
contours = (normalized watershed contours
          + normalized Cellpose contours
          + normalized StarDist contours) / 3
```

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| component methods | Selects which saved segmentation label stacks contribute to the ensemble. | Project ensemble runner requires watershed, Cellpose, and StarDist. | At least one method in the shared helper | No finite maximum documented | Adding a complementary method can recover foreground or boundary evidence missing from another method, but a poor method can also introduce false foreground and conflicting boundaries. | Fixed to the three available 2D methods in completed ensemble runs. |
| foreground combination | Chooses how per-method Boolean foreground maps are merged. | Ultrack's multi-label conversion and the project helper both use logical OR, equivalent to a pixelwise maximum. | Not applicable | Not applicable | A location becomes eligible for Ultrack hypotheses when any method predicts foreground; disagreement cannot remove another method's foreground. | Fixed; not compared with intersection or voting rules. |
| contour combination | Chooses how boundary evidence from the component methods is merged. | Ultrack and project concept: equal-weight arithmetic mean; project helper averages the separately converted maps. | Not applicable | Not applicable | Agreement produces stronger shared boundary evidence, while a boundary unique to one of three methods contributes roughly one third of that method's normalized value. | Fixed to equal weights; alternative weights have not been tested. |
| method weights | Sets each method's relative influence on the contour mean. | Project: equal implicit weight `1 / N`; for three methods each weight is `1 / 3`. | Not applicable; not configurable | Not applicable; not configurable | Increasing one method's weight would make its boundaries more influential, but the current helper has no weight parameter. | Fixed implicitly to equal weights. |
| conversion and normalization order | Determines whether contour maps are normalized before or after combining methods. | Project: convert and normalize each method first, then average; fixed by `combine_label_stacks`. | Not applicable | Not applicable | Per-method normalization gives every method a peak value of one in each nonempty frame before averaging, preventing a method with larger raw boundary magnitude from dominating solely by scale. | Fixed by the project implementation; not compared with Ultrack's one-call combination order. |

The last row is a project-specific distinction. Ultrack's
`labels_to_contours([labels_a, labels_b, ...], sigma=s)` averages the binary
boundaries first, smooths the average, and normalizes once. The project helper
instead calls `labels_to_contours` once per method, so each method is smoothed
and normalized independently before the final mean. Gaussian smoothing and
averaging are linear, but separate maximum normalization is not; the two
workflows can therefore produce different contour values.

All component stacks must cover the same selected frames and have the same
shape. Ensemble label IDs do not need to match across methods because the
project combines foreground occupancy and boundary evidence, not object IDs.

### 2.3 Dimensional and operational settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| spatial sigma form | Chooses isotropic smoothing with one scalar or axis-specific smoothing with one value per spatial dimension. | Ultrack accepts either; project 2D uses scalar `4.0`, while project 3D uses ZYX tuple `(0, 0, 0)`. | `0` per axis in project runners | No finite maximum documented | A scalar applies the same voxel width on all spatial axes; a tuple can avoid excessive smoothing across a coarsely sampled Z axis. | A multi-value 2D sigma sweep is complete only for Cellpose inputs; 3D axis-specific smoothing remains untuned. |
| sigma units | Determines how contour-smoothing distances are interpreted. | Ultrack and project: array pixels in 2D and voxels in 3D. | Not applicable | Not applicable | The same numerical sigma represents a different physical distance when voxel spacing is anisotropic. | Fixed by the array grid; no physical-unit conversion is applied here. |
| linking `scale` | Converts spatial coordinates for later link-distance calculations; it does not alter contour smoothing. | 2D project: no scale supplied; 3D project: required dataset-specific ZYX scale. | Greater than `0` in the 3D runner | No finite maximum documented | Scale changes physical distances between candidate segments during linking, while contour sigma remains in voxel units. | Documented here only to prevent unit confusion; its parameter table belongs to Ultrack linking. |
| `foreground_store_or_path` | Selects optional Zarr storage for the Boolean foreground output. | Ultrack default: `None`, creating temporary storage; project 3D writes `foreground.zarr`. | Not applicable | Not applicable | Disk-backed output reduces memory pressure and preserves the converted map but adds storage I/O. | Temporary for current 2D conversion; explicit disk path for 3D tracking. |
| `contours_store_or_path` | Selects optional Zarr storage for the float32 contour output. | Ultrack default: `None`, creating temporary storage; project 3D writes `contours.zarr`. | Not applicable | Not applicable | Disk-backed output reduces memory pressure and preserves the converted map but adds storage I/O. | Temporary for current 2D conversion; explicit disk path for 3D tracking. |
| `overwrite` | Allows existing output stores at the requested paths to be replaced. | Ultrack and project: `False` during conversion. | Not applicable | Not applicable | Enabling it can replace saved converted inputs; it does not change their intended numerical values. | Inherited default; project output preparation is responsible for avoiding conflicting stores. |
| output dtypes | Determines the stored numeric representation of the two maps. | Ultrack 0.8.0: Boolean foreground and float32 contours; project retains these types. | Not applicable | Not applicable | The foreground stores eligibility only, while float32 preserves graded smoothed boundary evidence for Ultrack segmentation. | Fixed by Ultrack and validated or cast by project workflows. |

Sources for this section are the exact Ultrack 0.8.0 wheel, the official
[`labels_to_contours` API](https://royerlab.github.io/ultrack/api.html#ultrack.utils.labels_to_contours),
the official [StarDist-to-Ultrack example](https://royerlab.github.io/ultrack/examples/stardist_2d/2d_tracking.html),
the official [segmentation-ensemble tutorial](https://royerlab.github.io/ultrack-i2k2024/tracking.html#combined-contours-and-foreground),
the scikit-image [`find_boundaries` API](https://scikit-image.org/docs/0.23.x/api/skimage.segmentation.html#skimage.segmentation.find_boundaries),
the SciPy [`gaussian_filter` API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html),
and the project's [`ultrack_2d.py`](../../src/cell_tracking/ultrack_2d.py),
[`ultrack_labels.py`](../../src/cell_tracking/ultrack_labels.py),
[`run_2d_ensemble.py`](../../scripts/ultrack/run_2d_ensemble.py), and
[`track_3d_labels.py`](../../scripts/ultrack/track_3d_labels.py).

## 3. Ultrack segmentation configuration

Ultrack segmentation is not the Cellpose, StarDist, or watershed step that
produced the input labels. It receives the foreground and contour maps from
Section 2 and builds many overlapping candidate segments for each time point.
The later tracking solver jointly chooses a compatible subset of these
candidates using temporal links. This stage uses no information from adjacent
frames by itself.

In Ultrack 0.8.0, one time point follows this sequence:

```text
foreground map > threshold
    -> connected foreground components
    -> early removal of very small isolated components
    -> pre-splitting of components larger than max_area
    -> hierarchical watershed using the contour map as edge evidence
    -> pruning by min_area, max_area, and min_frontier
    -> overlapping candidate segment hypotheses
```

The area settings count array elements: pixels for 2D data and voxels for 3D
data. They are not converted to physical units, and the linking `scale` does
not affect them. A suitable 3D value can therefore differ greatly from a 2D
value for the same biological cell.

### 3.1 Candidate-hypothesis parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `threshold` | Binarizes the supplied foreground map using the strict comparison `foreground > threshold`. | Ultrack 0.8.0 package default: `0.5`; current 2D project workflows inherit `0.5`. | Not documented | Not documented | Lower values admit more uncertain foreground and higher values admit less when the input is probabilistic. With the project's Boolean foreground, any value from `0` up to but not including `1` produces the same mask. | Fixed at `0.5`; not a meaningful sweep for the current label-derived Boolean inputs. This is separate from Cellpose or StarDist probability thresholds. |
| `min_area` | Sets the minimum pixel or voxel count retained for nodes in each segmentation hierarchy. | Ultrack 0.8.0 package default: `100`; current 2D project workflows inherit `100`. | Not documented | `max_area` (package validation permits equality) | Increasing it removes or merges more small hypotheses and can reduce over-segmentation, but can exclude real small cells; decreasing it preserves smaller cells and fragments. | Baseline `100` is recorded but has not been swept. Dataset-specific 3D values must be read from the saved effective configuration. |
| `min_area_factor` | Sets the early connected-component cutoff to `min_area / min_area_factor` before the hierarchy is built. | Ultrack 0.8.0 package default: `4.0`; current 2D project workflows inherit `4.0`. | Not documented | Not documented | For a fixed `min_area`, a larger positive factor lowers the early cutoff and retains more tiny isolated components; a smaller positive factor removes more of them. This direction is the opposite of what the parameter name may suggest. | Fixed at `4.0`; not swept. With `min_area=100`, disconnected components below 25 pixels or voxels are removed by this early filter when multiple components exist. |
| `max_area` | Sets the maximum pixel or voxel count for candidate hypotheses and triggers pre-splitting of larger connected components. | Ultrack 0.8.0 package default: `1,000,000`; current 2D project workflows inherit it. | `min_area` (package validation) | No finite maximum documented | Decreasing it prevents very large or fused hypotheses and forces more splitting; increasing it permits larger merged hypotheses, which can correct unwanted splitting but increases the hierarchy search space. | Baseline `1,000,000` is recorded but has not been swept. Dataset-specific 3D values must be read from the saved effective configuration. |
| `min_frontier` | Merges hierarchy regions whose average shared contour strength is below this value. | Ultrack 0.8.0 package default: `0.0`, which disables frontier filtering; current 2D project workflows inherit `0.0`. | Not documented | Not documented | Increasing it merges across more weak boundaries and can reduce over-segmentation, but can fuse nearby real cells; decreasing it preserves weaker splits. Its scale must be interpreted relative to the contour map. | Fixed at `0.0`; not swept. Current smoothed project contour maps are normalized per frame before this stage. |
| `ws_hierarchy` | Chooses the Higra watershed hierarchy used to order possible region merges. | Ultrack 0.8.0 package default: `area`; accepted configuration names are `area`, `dynamics`, and `volume`; current 2D workflows inherit `area`. | Not applicable | Not applicable | Changing the hierarchy criterion changes which nested segment candidates are produced from the same foreground and contour maps. The options should be compared empirically rather than treated as a numeric low-to-high scale. | Fixed to `area`; the three hierarchy types have not been compared. |
| `max_noise` | Sets the upper endpoint of independent uniform additive noise applied to the contour map before hierarchy construction. | Ultrack 0.8.0 package default: `0.0`, meaning no noise; current 2D workflows inherit `0.0`. | Not documented | Not documented | Small positive values can break ties on flat contour plateaus; larger values perturb boundary ordering more strongly and can overwhelm weak real boundaries. Values at or below zero add no noise in the 0.8.0 implementation. | Fixed at `0.0`; not swept. |
| `random_seed` | Selects whether the random-number generator used for contour noise is reseeded with the frame index. | Ultrack 0.8.0 package default: `frame`; accepted values are `frame`, `none`, and `None`; current 2D workflows inherit `frame`. | Not applicable | Not applicable | `frame` makes any added noise reproducible for each time point and independent of worker order; `none` or `None` leaves the existing random state unchanged. It does not change segmentation when `max_noise=0`. | Fixed to `frame`, but inactive because `max_noise=0`. |
| `anisotropy_penalization` | Is intended to add a penalty to graph edges along Z so the 3D hierarchy can favor XY separation. | Ultrack 0.8.0 package default: `0.0`; current 2D workflows inherit `0.0`. | Not documented | Not documented | The documented intention is that positive values prioritize XY-plane segmentation and negative values do the opposite. However, the standard Ultrack 0.8.0 segmentation path does not pass this field to hierarchy construction, so changing it there has no effect. | Fixed at `0.0`. Treat as inactive in the project's pinned version unless the implementation is changed and separately verified. |

`min_area` participates in two different operations. First, Ultrack may remove
complete connected foreground components smaller than
`min_area / min_area_factor`; with the defaults, that means components below
25 pixels or voxels. In 0.8.0 this early operation is skipped when a frame has
only one connected foreground component. Second, Ultrack prunes small nodes
inside every hierarchy using `min_area` itself. The factor therefore does not
replace the final 100-pixel or 100-voxel hierarchy cutoff.

`max_area` also acts twice. Ultrack first pre-splits connected foreground
components larger than the limit to keep hierarchy construction tractable,
then removes candidate nodes whose area exceeds the limit. It is therefore
both a biological size constraint and a computational constraint.

### 3.2 How the current project obtains these values

The standard 2D benchmark and 2D ensemble scripts create `MainConfig()` and
change only `segmentation_config.n_workers`. They therefore use every
scientific package default shown above, regardless of whether the upstream
labels came from Cellpose, StarDist, watershed, or their ensemble. The
parameter-analysis runner instead requires an explicit TOML configuration and
saves the resolved values to `effective_config.json`.

The 3D tracking runner also requires an external TOML configuration and saves
both `source_config.toml` and `effective_config.json`. That TOML file is not
stored in this repository, so no single 3D value should be inferred from the
2D defaults. A 3D report should quote its saved effective configuration,
especially `min_area` and `max_area`, whose units are voxels.

For the current Boolean foreground maps, the first useful segmentation-config
study should normally measure cell areas and examine the hypotheses produced
by `min_area`, `max_area`, and possibly `min_frontier`. The official tuning
guide recommends beginning near half the expected or smallest non-outlier
cell area for `min_area`, and about 1.25 to 1.5 times the largest cell area for
`max_area`. These are starting heuristics, not accepted API limits. The guide
also suggests changing `min_frontier` in steps of 0.05 when weak boundaries
are producing excessive splitting.

### 3.3 Operational setting

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `n_workers` | Sets the number of workers that construct and store per-frame segmentation hierarchies. | Ultrack 0.8.0 package default: `1`; 2D benchmark runner default: `4`; 2D ensemble runner default: `1`; explicit TOML value for parameter-analysis and 3D runs. | Not documented | No finite maximum documented | More workers may reduce runtime but use more memory and database resources; this is not intended to change the candidate hypotheses. Frame-based random seeding keeps positive contour noise reproducible across worker order. | Treated as an operational value and recorded with each run, not included in the scientific parameter sweep. |

There are no documented numerical bounds for most fields in
`SegmentationConfig`, and Ultrack 0.8.0 validates only that `min_area` is not
greater than `max_area`. This does not make arbitrary values meaningful. In
particular, `min_area_factor=0` causes division by zero, negative area values
are not biologically meaningful, and foreground thresholds outside the input
map's value range can make nearly everything foreground or background.

Sources for this section are the exact Ultrack 0.8.0 wheel, the official
[`SegmentationConfig` documentation](https://royerlab.github.io/ultrack/configuration.html#ultrack.config.SegmentationConfig),
the official [tracking-performance tuning guide](https://royerlab.github.io/ultrack/optimizing.html),
the Higra [watershed-hierarchy documentation](https://higra.readthedocs.io/en/stable/python/watershed_hierarchy.html),
and the project's
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py),
[`run_2d_ensemble.py`](../../scripts/ultrack/run_2d_ensemble.py),
[`segmentation_parameters.py`](../../src/cell_tracking/segmentation_parameters.py),
and [`track_3d_labels.py`](../../scripts/ultrack/track_3d_labels.py).

## 4. Ultrack linking configuration

Ultrack linking creates a sparse graph of possible associations between the
candidate segments from two adjacent frames. It does not select the final
segments or tracks; the tracking solver in Section 5 chooses among these links
and can leave a candidate link unused.

In Ultrack 0.8.0, linking each pair of frames follows this sequence:

```text
candidate segments at t and t + 1
    -> optionally shift t + 1 positions using a stored motion field
    -> optionally scale spatial coordinates
    -> find up to 2 * max_neighbors sources within max_distance
    -> optionally reject candidates using image-intensity z-scores
    -> score each remaining pair as IoU - distance_weight * distance
    -> keep at most max_neighbors links for each t + 1 candidate
    -> store candidate links for the tracking solver
```

The search is directed from each target candidate at `t + 1` back to source
candidates at `t`. Therefore, `max_neighbors` is a cap per target in the 0.8.0
implementation, not necessarily a cap on the total outgoing links from each
source. Links are created only between consecutive frames. Increasing a
linking radius does not connect across a missing frame and is not gap closing.

### 4.1 Linking parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `max_distance` | Sets the hard centroid-distance radius within which a candidate from frame `t` can be considered for a candidate at `t + 1`. | Ultrack 0.8.0 package default: `15.0`; current 2D benchmark and ensemble workflows inherit `15.0`. | Not documented | No finite maximum documented | A smaller value makes a sparser graph and can exclude the true association; a larger value admits faster motion but adds ambiguous links and computation. It changes eligibility, not the score formula. | Fixed at `15.0` for current 2D runs and not swept. The 3D value comes from the external TOML and must be interpreted with that run's `scale`. |
| `max_neighbors` | Limits the number of source candidates retained for each target candidate after scoring. | Ultrack 0.8.0 package default: `5`; current 2D benchmark and ensemble workflows inherit `5`. | Not documented | No finite maximum documented | Ultrack first queries up to twice this number of nearest sources, then keeps the highest-scoring half. Lower values can discard the correct link; higher values preserve more alternatives but enlarge the graph and solver problem. | Fixed at `5`; not swept. With the default, at most 10 nearby sources are scored and at most 5 links are stored per target. |
| `distance_weight` | Sets the coefficient subtracted from IoU according to centroid distance: `link score = IoU - distance_weight * distance`. | Ultrack 0.8.0 package default: `0.0`; current 2D benchmark and ensemble workflows inherit `0.0`. | Not documented | No finite maximum documented | At zero, links are ranked by IoU, with shorter distance used only to break equal-score ties. Increasing a nonnegative value favors nearer candidates and can make distant-link scores negative, but does not itself remove those links. A negative value would reward distance and is not the documented intent. | Fixed at `0.0`; not swept. Any test value must be chosen relative to both the 0-to-1 IoU scale and the distance units established by `scale`. |
| `z_score_threshold` | Rejects a candidate pair when its within-mask mean intensities differ by more than this many target-mask standard deviations in any supplied linking image. | Ultrack 0.8.0 package default: `5.0`; current 2D benchmark and ensemble workflows inherit `5.0`. | Not documented | No finite maximum documented | Lower values reject more appearance changes; higher values allow greater intensity differences. It is a hard filter before link scoring and has no effect when no images are passed to `link`. | Inactive in all current 2D, parameter-analysis, and 3D workflows because their linking calls do not supply `images`; not swept. |

`max_distance` and `max_neighbors` are both hard candidate-graph controls, but
they act in different order. The radius first decides which sources are
eligible. Ultrack then examines at most `2 * max_neighbors` of the nearest
eligible sources and retains the `max_neighbors` highest scores, using shorter
distance as a tie-breaker. A candidate outside `max_distance` cannot be rescued
by a high IoU or a favorable `distance_weight`.

The default association evidence is mask intersection-over-union. IoU ranges
from zero to one and is positive only when the two candidate masks overlap
after any motion shift. With `distance_weight=0`, non-overlapping candidates
inside the search radius can still be stored with a zero score; Ultrack 0.8.0
does not require stored link scores to be positive. The tracking solver later
transforms these scores according to `TrackingConfig` and decides whether to
use a link.

The `z_score_threshold` calculation is local rather than a dataset-wide image
normalization. For each supplied image, Ultrack compares the source-mask and
target-mask mean intensities and divides their difference by the target mask's
intensity standard deviation. The pair passes only when the largest absolute
z-score across the supplied images is at or below the threshold. Target
standard deviations at or below `1e-6` are replaced by `1.0`. This feature
should not be tuned without recording which images and intensity preprocessing
were supplied.

### 4.2 Spatial scale and optional motion input

`scale` and a motion field are not fields of `LinkingConfig`, but they change
the distances or overlaps to which the configuration is applied and therefore
belong in the linking record.

| Parameter or input | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| linking `scale` | Multiplies spatial centroid coordinates before neighbor search and distance calculation. | Ultrack `link` default: `None`, meaning array-coordinate units; current 2D workflows use `None`; the 3D runner requires a dataset-specific ZYX sequence. | Greater than `0` for every axis in the project 3D runner | No finite maximum documented | An anisotropic scale makes equal physical motion comparable across axes. It also changes the units of `max_distance` and the distance term in link scoring, but it does not resample masks or change segmentation-area thresholds. | No scale is supplied in current 2D runs, so distances are pixels. The completed MDA231 Cellpose 3D command requested `(4.83, 1, 1)`; its saved run record remains the authority. |
| `images` supplied to `link` | Supplies one or more time-series images from which within-mask intensities are measured for z-score filtering. | Ultrack `link` default: empty sequence, which disables the filter; all current project workflows use the empty default. | Not applicable | Not applicable | Supplying images activates `z_score_threshold`; changing the images or their preprocessing can change which links exist even when the configuration is unchanged. | Not used. Raw images are not currently passed into the linking call. |
| motion field / stored node shift | Shifts target positions for neighbor search and shifts target masks before IoU is calculated. | No motion field by default, leaving node shifts at zero; current project workflows do not call `add_flow`. | Not applicable | Not applicable | A suitable field can restore overlap for fast or nonuniform motion; an inaccurate field can move the correct association away and distort both distance and IoU evidence. | Not used in current 2D or 3D runs. It should be evaluated separately from a plain `max_distance` sweep. |

When `scale` is present, Ultrack multiplies the last matching spatial
coordinates by it. For the project 3D runner these are Z, Y, and X. Thus a
configuration with `max_distance=15` means 15 pixels in the current 2D
workflows, but 15 units of the supplied scale in a 3D workflow. The same
numerical value is not automatically comparable across those cases.

A larger `max_distance` only makes a fast-moving pair eligible. If the masks no
longer overlap, its baseline IoU remains zero. Motion-field alignment can be
more informative than continuing to expand the radius because it shifts the
target mask as well as its centroid before IoU is calculated.

### 4.3 How the current project obtains these values

The standard 2D benchmark and ensemble runners construct `MainConfig()` and
override only `linking_config.n_workers`. They inherit `max_distance=15.0`,
`max_neighbors=5`, `distance_weight=0.0`, and `z_score_threshold=5.0`. Their
calls to `Tracker.link()` supply neither `scale` nor `images`, and no flow field
is added. The resolved 2D baseline configuration is also recorded in the
reproducibility document.

The parameter-analysis runner requires a TOML configuration and saves its
resolved values to `effective_config.json`, but it still calls `Tracker.link()`
without `scale` or `images`. Configuration sweeps should therefore change the
four `LinkingConfig` fields, while a scale, color-filter, or motion-field study
would require an explicit workflow change and a distinct experiment record.

The 3D runner requires both an external TOML configuration and a positive ZYX
`scale`. It saves `source_config.toml` and `effective_config.json`, while its run
report records the command arguments. The repository does not contain a
universal 3D linking configuration, so the external records must be checked
before reporting `max_distance` or its units.

The first linking study should measure frame-to-frame centroid displacement in
the units actually used by `link`. The official tuning guide recommends
starting `max_distance` near the maximum expected movement with some tolerance,
giving 1.5 times the expected movement as an example. That is a starting
heuristic rather than an API limit. After the correct associations fit inside
the radius, `max_neighbors` controls how many alternatives survive and
`distance_weight` controls their ranking. `z_score_threshold` should remain
out of the sweep unless the workflow intentionally supplies linking images.

### 4.4 Operational setting

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `n_workers` | Sets the number of adjacent frame pairs linked in parallel. | Ultrack 0.8.0 package default: `1`; current 2D benchmark and ensemble runner defaults: `1`; explicit TOML value for parameter-analysis and 3D runs. | Not documented | No finite maximum documented | More workers may reduce linking time but increase memory use and concurrent database activity; it is not intended to change the candidate links. | Treated as an operational value and recorded with each run, not included in the scientific sweep. |

Ultrack 0.8.0 declares no numerical validators for the four
`LinkingConfig` fields. This does not make arbitrary values meaningful:
neighbor counts and search radii need to be positive for a useful graph,
nonnegative distance weights match the documented penalty, and a negative
z-score threshold would reject all real intensity comparisons.

Sources for this section are the exact Ultrack 0.8.0 wheel, the official
[`LinkingConfig` documentation](https://royerlab.github.io/ultrack/configuration.html#ultrack.config.LinkingConfig),
the official [`link` API](https://royerlab.github.io/ultrack/api.html#ultrack.link),
the official [tracking-performance tuning guide](https://royerlab.github.io/ultrack/optimizing.html),
the [Ultrack paper](https://arxiv.org/abs/2308.04526), and the project's
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py),
[`run_2d_ensemble.py`](../../scripts/ultrack/run_2d_ensemble.py),
[`segmentation_parameters.py`](../../src/cell_tracking/segmentation_parameters.py),
[`ultrack_labels.py`](../../src/cell_tracking/ultrack_labels.py), and
[`track_3d_labels.py`](../../scripts/ultrack/track_3d_labels.py).

## 5. Ultrack tracking configuration

`TrackingConfig` controls the optimization that jointly selects a compatible
set of segmentation hypotheses and adjacent-frame links. Ultrack formulates
this as a mixed-integer linear program (ILP). The solver maximizes transformed
link evidence while respecting these biological and spatial constraints:

```text
selected cell
    <- exactly one incoming link or one appearance event
    -> zero outgoing links plus disappearance,
       one outgoing link for continuation, or
       two outgoing links plus one division event

overlapping hypotheses from the same frame cannot both be selected
two source cells cannot merge into one selected target
```

Ignoring optional node-probability scores, the objective can be read as:

```text
maximize
    sum(transformed scores of selected links)
    + appear_weight * number of penalized appearances
    + disappear_weight * number of penalized disappearances
    + division_weight * number of divisions
```

Because the objective is maximized, the documented negative event weights are
penalties. A value closer to zero makes the event less costly; a more-negative
value discourages it. Positive values would reward events and are not the
documented intent.

### 5.1 Appearance, disappearance, and division

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `appear_weight` | Adds this objective weight when a selected cell has no incoming link and therefore starts a lineage. | Ultrack 0.8.0 package default: `-0.001`; current 2D benchmark and ensemble workflows inherit `-0.001`. | Not documented | Not documented | Moving it closer to zero permits more track starts; making it more negative suppresses spontaneous starts but can remove real cells whose incoming link is missing. | Baseline `-0.001` is recorded but not swept. Dataset-specific 3D values must be read from the external effective configuration. |
| `disappear_weight` | Adds this objective weight when a selected cell has no outgoing link and therefore ends a lineage. | Ultrack 0.8.0 package default: `-0.001`; current 2D benchmark and ensemble workflows inherit `-0.001`. | Not documented | Not documented | Moving it closer to zero permits more track endings; making it more negative encourages continuity but can remove short or weakly linked tracks rather than preserve them. | Baseline `-0.001` is recorded but not swept. The official guide recommends tuning this event weight first. |
| `division_weight` | Adds this objective weight when a selected parent uses two outgoing links instead of one. | Ultrack 0.8.0 package default: `-0.001`; current 2D benchmark and ensemble workflows inherit `-0.001`. | Not documented | Not documented | Moving it closer to zero allows more divisions; making it more negative suppresses divisions. It cannot recover a daughter link excluded during linking. | Baseline `-0.001` is recorded but not swept. Division counts have not yet been used for tuning. |
| `image_border_size` | Defines a spatial border band in which appearance and disappearance penalties are set to zero. | Ultrack 0.8.0 package default: `None`, meaning no spatial-border exemption; current 2D workflows inherit `None`. | Not documented per axis | No finite maximum documented | A larger band allows more unpenalized entries and exits near image edges but can also permit unnecessary track breaks there. The test uses candidate centroids, not whether any mask pixel touches the border. | Fixed at `None`; not tested. A 3D value would be a ZYX tuple in voxel coordinates, independent of linking `scale`. |

Appearances at the first frame of a global solve are automatically unpenalized,
and disappearances at the final frame are unpenalized. `image_border_size`
extends that exemption to spatial borders at intermediate time points. In 2D,
Ultrack 0.8.0 can accept a YX tuple and pads it with a zero-width Z border; in
3D the documented order is ZYX.

These event variables do not perform gap closing. If a cell disappears at
frame `t` and a similar cell appears at `t + 2`, the solver represents an ended
lineage and a new lineage because the linking graph contains only adjacent
frames. It does not know that the two events belong to the same biological
cell. Gap closing remains a separately reported post-processing step.

The appearance and division weights must be interpreted together. When a new
candidate could be explained as either a lineage start or a second child of an
existing parent, their relative penalties influence the choice. The official
tuning guide recommends keeping `division_weight` equal to or more negative
than `appear_weight` while tuning appearances so that new cells are not
systematically converted into false divisions.

### 5.2 Link-score transformation

The link scores produced in Section 4 are transformed only when the tracking
model is built. These fields do not change which candidate links exist.

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `link_function` | Chooses whether each stored link score `w` becomes `w + bias` or `w ** power + bias` in the solver objective. | Ultrack 0.8.0 package default: `power`; accepted values are `identity` and `power`; current 2D workflows inherit `power`. | Not applicable | Not applicable | `identity` preserves the relative score scale, while `power` changes the contrast between weak and strong links according to `power`. | Fixed to `power`; not compared with `identity`. |
| `power` | Sets the exponent used when `link_function=power`. | Ultrack 0.8.0 package default: `4`; current 2D workflows inherit `4`. | Not documented | Not documented | For nonnegative scores between zero and one, values above one suppress weak links more strongly than strong links. At the default, `0.5` becomes `0.0625` while `1.0` remains `1.0`. The field is inactive with `identity`. | Fixed at `4`; not swept. Its documented purpose is to discourage solutions composed of many weak overlaps. |
| `bias` | Adds a constant after transforming every selected link score. | Ultrack 0.8.0 package default: `-0.0`, numerically zero; current 2D workflows inherit it. | Not documented | Not documented | A more-negative value penalizes every selected link and can make lineage starts and ends preferable to weak continuations; a positive value rewards adding links and is not the documented intent. | Fixed at zero; not swept. |

With the default `distance_weight=0`, ordinary IoU link scores lie between zero
and one, so the fourth power strongly favors high-overlap associations. This is
the setting motivated in the Ultrack paper as a way to avoid selecting many
weak overlaps instead of fewer strong ones.

`distance_weight` and `power` have a less intuitive interaction. A positive
distance penalty can make a stored link score negative. Ultrack 0.8.0 applies
the power directly without clipping: an even power such as four converts a
negative score into a positive objective value, and a fractional power can
produce a non-finite value. A `distance_weight` sweep must therefore inspect
the resulting score distribution and keep the link transformation fixed and
valid; it should not assume that more-negative pre-transform scores remain
penalized.

The same transformation is also applied to optional per-node probabilities
when every node has one. The current project does not add node probabilities,
so `link_function`, `power`, and `bias` currently affect link scores only.

### 5.3 Windowing and solution-quality controls

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `window_size` | Splits a long time series into smaller temporal ILPs containing this many main frames instead of solving the complete sequence at once. | Ultrack 0.8.0 package default: `None`, meaning one global solve; current 2D workflows inherit `None`. | Not documented | No finite maximum documented | Smaller windows reduce peak memory and solve time but approximate the global solution and can introduce window-edge effects; larger windows provide more temporal context at greater computational cost. | Fixed at `None` for current 2D runs; no windowed comparison. External 3D configurations must be checked separately. |
| `overlap_size` | Adds temporal context around each solve window and helps carry selected boundary segments between windows. | Ultrack 0.8.0 package default: `1` frame on each applicable side; current 2D workflows inherit `1`. | Not documented | No finite maximum documented | Larger overlaps give the solver more context across window boundaries but repeat more computation and use more memory; too little overlap can produce seam errors. It is inactive when `window_size=None`. | Inherited default but inactive in current global 2D solves; not swept. |
| `solution_gap` | Sets the relative MIP optimality-gap tolerance forwarded to Python-MIP's `max_mip_gap`. | Ultrack 0.8.0 package default: `0.001`, corresponding to a 0.1% relative tolerance; current 2D workflows inherit it. | Not documented | Not documented | A smaller tolerance requires a tighter proof of optimality and may take longer; a larger tolerance can stop earlier with a solution farther from the best bound. | Fixed at `0.001`; treated as a solver-quality setting rather than a biological parameter. |
| `time_limit` | Sets the maximum solver search time in seconds for each ILP window. | Ultrack 0.8.0 package default: `36,000` seconds, or 10 hours; current 2D workflows inherit it. | Not documented | No finite maximum documented | A shorter limit can return a feasible but not proven-optimal solution, or fail if no feasible solution is found; a longer limit allows more search. With windowing, the limit applies separately to each window rather than the complete run. | Fixed at `36,000` and not swept; each run should preserve its actual solver status. |

When `window_size` is set, Ultrack 0.8.0 solves even-numbered windows first and
then odd-numbered windows. Overlap frames and saved boundary selections are
used to constrain neighboring windows and maintain continuity. This is a
scalability approximation, not the same optimization problem as a single
global solve, so window settings belong in every reproducibility record.

Python-MIP can report a feasible solution when the search stops before proving
optimality. Ultrack 0.8.0 accepts that solution with a warning. Evaluation
reports should therefore preserve the actual solver status, not merely the
fact that an output was exported.

### 5.4 Solver and operational settings

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `solver_name` | Selects the mixed-integer solver backend. | Ultrack 0.8.0 package default: empty string, selecting Gurobi when available and otherwise CBC; accepted values are `GUROBI`, `CBC`, and empty string. Project 2D runner default: `GUROBI`. | Not applicable | Not applicable | The backend primarily changes runtime, memory use, licensing, and the ability to finish difficult problems; different early termination can also yield different feasible solutions. Ultrack falls back to CBC if solver initialization fails. | Current 2D scripts request Gurobi; the actual backend must be confirmed from the run log. Parameter-analysis and 3D runs obtain it from their TOML files. |
| `n_threads` | Sets the number of threads made available to the solver backend. | Ultrack 0.8.0 package default: `-1`, meaning all available cores in Python-MIP; current 2D runner default: `4`. | `-1` in the documented Python-MIP modes | No finite maximum documented | More threads may reduce solve time but increase CPU and memory use; exact performance and determinism are backend-dependent. `0` uses the backend default and positive values request that many threads. | Fixed to `4` in current standard 2D scripts; explicit TOML value for parameter-analysis and 3D runs. |
| `method` | Selects the backend's linear-programming method for the initial relaxation. | Ultrack 0.8.0 package and current 2D default: `0`, which Python-MIP defines as automatic. | Not applicable; integer-coded category | Not applicable; integer-coded category | Current Python-MIP documentation lists automatic, dual simplex, primal simplex, barrier variants, racing, and recommendation modes; availability and behavior depend on the installed backend. | Fixed at `0`; not tuned. The project does not pin an exact Python-MIP version, so its runtime version should be recorded before changing this field. |

`solution_gap` and `time_limit` can affect the returned result even though they
are computational controls. `solver_name`, `n_threads`, and `method` should
normally remain fixed during a biological parameter comparison so that changes
in solver behavior are not confused with changes in event weights.

### 5.5 Declared but inactive fields in Ultrack 0.8.0

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `dismiss_weight_guess` | Has no documented role and is not read anywhere outside configuration/default construction in the exact Ultrack 0.8.0 wheel. | Ultrack 0.8.0 package default: `None`; omitted from the public configuration page. | Not documented | Not documented | No effect in the standard 0.8.0 tracking implementation. | Leave as `None`; do not include in a parameter sweep. |
| `include_weight_guess` | Has no documented role and is not read anywhere outside configuration/default construction in the exact Ultrack 0.8.0 wheel. | Ultrack 0.8.0 package default: `None`; omitted from the public configuration page. | Not documented | Not documented | No effect in the standard 0.8.0 tracking implementation. | Leave as `None`; do not include in a parameter sweep. |

### 5.6 How the current project obtains these values

The standard 2D benchmark and ensemble runners construct `MainConfig()`. They
inherit all scientific and solution-quality defaults in this section, then
request `solver_name=GUROBI` and `n_threads=4`. The resolved baseline record is
therefore:

```text
appear_weight=-0.001       disappear_weight=-0.001
division_weight=-0.001     image_border_size=None
window_size=None           overlap_size=1
solution_gap=0.001         time_limit=36000
link_function=power        power=4             bias=0
solver_name=GUROBI         n_threads=4          method=0
```

The parameter-analysis and 3D runners instead require external TOML files and
save resolved configurations to `effective_config.json`. Their values must be
quoted from those records rather than inferred from the 2D baseline. None of
the current project workflows adds node probabilities or fixes solver variables
from annotations or ground-truth matches.

Before tuning these weights, the segmentation hypotheses and linking graph
must already contain the desired cells and associations. Tracking parameters
can choose among existing candidates, but cannot create a missing segment or a
link excluded by `max_distance` or `max_neighbors`.

A controlled tracking study should keep the segmentation and link graph fixed,
rerun only `solve`, and begin from recorded event errors:

1. Tune `disappear_weight` first, as recommended by the official guide, while
   checking whether fewer endings improve continuity or merely remove weak
   tracks.
2. Tune `appear_weight` and `division_weight` together, keeping the division
   penalty equal to or more negative than the appearance penalty unless there
   is evidence for another relationship.
3. Compare predicted division, start, and end counts with annotations rather
   than optimizing only a single aggregate tracking score.
4. Keep `link_function`, windowing, gap, time limit, solver, and thread count
   fixed during the event-weight study. Test those separately if needed.

Ultrack 0.8.0 declares no numerical validators for these tracking fields. The
configuration can therefore accept values that contradict their documented
roles or cause invalid transformations. Experimental plans should state the
tested range explicitly instead of treating the absence of validation as an
unlimited meaningful range.

Sources for this section are the exact Ultrack 0.8.0 wheel, the official
[`TrackingConfig` documentation](https://royerlab.github.io/ultrack/configuration.html#ultrack.config.TrackingConfig),
the official [`solve` API](https://royerlab.github.io/ultrack/api.html#ultrack.solve),
the official [tracking-performance tuning guide](https://royerlab.github.io/ultrack/optimizing.html),
the [Ultrack paper](https://arxiv.org/abs/2308.04526), the Python-MIP
[`Model` and `LP_Method` documentation](https://docs.python-mip.com/en/latest/classes.html),
and the project's
[`run_2d_benchmark.py`](../../scripts/ultrack/run_2d_benchmark.py),
[`run_2d_ensemble.py`](../../scripts/ultrack/run_2d_ensemble.py),
[`segmentation_parameters.py`](../../src/cell_tracking/segmentation_parameters.py),
[`track_3d_labels.py`](../../scripts/ultrack/track_3d_labels.py), and
[`ultrack-reproducibility.md`](ultrack-reproducibility.md).

## 6. Optional post-processing

Ultrack's `close_tracks_gaps` utility operates after segmentation, linking,
and solving. It receives an exported track table and optionally a dense
track-labeled segmentation. It does not revise the Ultrack database, rerun the
solver, or use the original candidate-link scores.

In Ultrack 0.8.0, gap closing follows this sequence:

```text
solved track table
    -> identify root-track starts and terminal-track ends
    -> consider 1 missing frame, then 2, up to max_gap
    -> group ends at t with starts at t + gap + 1
    -> compute endpoint Euclidean distances
    -> make a one-to-one minimum-total-distance assignment
    -> retain assigned pairs whose distance is strictly below max_radius
    -> merge each retained pair under the earlier track ID
    -> linearly interpolate coordinates for the missing frames
    -> optionally relabel and fill a copied segmentation array
```

This is different from linking. Linking proposes adjacent-frame edges before
the solver and uses overlap-based evidence. Gap closing joins already solved
tracklets across one or more absent frames using endpoint distance only. Its
output is a new post-processed result that must be evaluated separately from
the raw Ultrack solution.

### 6.1 Gap-closing parameters

| Parameter | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `max_gap` | Sets the largest number of missing intermediate frames that may be filled between a track end and a later track start. | Required by `close_tracks_gaps`; Ultrack provides no default. | Not documented | No finite maximum documented | Increasing it can reconnect longer interruptions but also allows less certain matches over more elapsed time. `max_gap=1` tests an end at `t` against a start at `t+2`; the utility does not join an unlinked adjacent pair at `t` and `t+1`. | Not used or tested in the current project. A future value should be based on observed consecutive missing-detection lengths. |
| `max_radius` | Sets the strict upper endpoint-distance threshold for accepting an assigned pair of tracklets. | Required by `close_tracks_gaps`; Ultrack provides no default. | Not documented | No finite maximum documented | A smaller radius reduces false joins but misses faster motion; a larger radius closes more gaps while increasing identity-switch risk in crowded regions. A distance exactly equal to the radius is rejected. | Not used or tested. A future value must be reported in the units established by `spatial_columns` and `scale`. |
| `spatial_columns` | Selects the coordinate columns used for distance matching and interpolation. | Ultrack 0.8.0 default: `['z', 'y', 'x']`. | Not applicable | Not applicable | Adding an axis includes its displacement in the Euclidean distance; omitting an axis ignores motion along it. The named columns must exist in the track table. | For future 2D use, this must be set to `['y', 'x']` because the project's 2D track table has no Z column; 3D uses ZYX. |
| `scale` | Multiplies the selected coordinates before distance matching and interpolation, then restores the returned table to its original coordinate system. | Ultrack 0.8.0 default: `None`, meaning raw table-coordinate units. | Not documented per axis | No finite maximum documented | A positive anisotropic scale makes `max_radius` operate in physical or otherwise normalized distance units. Incorrect axis order or values distort matching. | Not used. A future 3D track-table study should use the same ZYX spacing convention as linking, while preserving the exact values in its report. |

`max_radius` is a total endpoint-displacement limit, not a per-frame speed.
The same radius is applied to every gap length. For example, a three-frame
interruption receives no larger motion allowance than a one-frame
interruption. If motion per frame is the intended criterion, the experiment
must translate that criterion into an explicit radius policy rather than
assuming the function scales it automatically.

For each endpoint-time and gap-length group, Ultrack uses SciPy's linear-sum
assignment to minimize total Euclidean distance with one-to-one matches. The
radius filter is applied after that assignment. Consequently, the function
does not explicitly maximize the number of within-radius closures, and a
different valid pairing can remain unused after an assigned pair is rejected.
Gap lengths are processed from shortest to longest, and matched endpoints are
removed before longer gaps are considered, so the overall procedure is
sequential even though each individual assignment is optimal for its distance
matrix.

Only root starts, where `parent_track_id` indicates no parent, are eligible as
the later endpoint. Only terminal ends, whose track ID is not the parent of a
daughter track, are eligible as the earlier endpoint. This avoids directly
merging across an existing division boundary, but distance-only matching can
still join unrelated root and terminal tracks in a crowded field.

### 6.2 Track-table and segmentation outputs

| Parameter or input | What it does | Default and source | Minimum | Maximum | Effect | Project status |
| --- | --- | --- | ---: | ---: | --- | --- |
| `tracks_df` | Supplies the solved tracks with `track_id`, `parent_track_id`, `t`, and every requested spatial column. | Required input; normally derived from `to_tracks_layer`. | Not applicable | Not applicable | The function copies this table, merges matched track IDs, updates references to merged parent IDs, and inserts one row for each missing frame. | Current raw `tracks.csv` files have not been passed through gap closing. They remain solver outputs. |
| coordinate interpolation | Creates straight-line positions between the earlier endpoint and later start for every missing frame. | Fixed Ultrack 0.8.0 behavior; there is no interpolation-method parameter. | Not applicable | Not applicable | It assumes constant straight-line motion across the gap. Spatial coordinates are interpolated, while other fields in an inserted row are copied from the earlier endpoint rather than independently estimated. | Untested. Interpolated points would require visual validation against the raw movie. |
| `segments` | Supplies an optional dense time-series segmentation whose label values correspond to `track_id`. | Ultrack 0.8.0 default: `None`, returning only the post-processed table. | Not applicable | Not applicable | When supplied, Ultrack copies the array, relabels the later tracklet with the earlier track ID, and fills missing frames by translating the earlier endpoint mask along the interpolated path. It does not infer a new mask from image data or interpolate cell shape. | Not used. Current project exports must be preserved separately before any segmentation rewriting is tested. |
| `segments_store_or_path` | Selects where the copied and modified segmentation is stored. | Ultrack 0.8.0 default: `None`, creating temporary in-memory Zarr storage. | Not applicable | Not applicable | An explicit new path preserves the derived masks for inspection; omitting it can leave only a temporary result. This setting does not change the matching decisions. | No project convention yet. A future experiment should use a distinct post-processing directory, never the raw solver-output path. |
| `overwrite` | Allows an existing destination segmentation store to be replaced. | Ultrack 0.8.0 default: `False`. | Not applicable | Not applicable | Enabling it affects output-file safety only; it does not alter gap matching. | Should remain `False` unless a dedicated derived-output path has been verified. |

When `segments` is omitted, the returned table contains interpolated track
rows but no corresponding image masks. This can be sufficient for trajectory
analysis, but it is not a complete segmentation-and-tracking result for CTC
evaluation. When `segments` is supplied, the function returns both the new
table and a copied segmentation. Shifted masks are rasterized to integer array
indices and clipped at the image boundary, so their positions can differ
slightly from the floating-point interpolated centers.

The filled masks are translated copies of the earlier endpoint mask. They do
not respond to intensity changes, growth, rotation, deformation, neighboring
cells, or a division occurring inside the missing interval. Gap-filled masks
can therefore improve lineage continuity while worsening segmentation overlap;
TRA and SEG must both be reported rather than assuming a tracking repair is an
overall improvement.

### 6.3 Ultrack 0.8.0 scale caveat for filled masks

The track-table scale behavior is internally consistent: coordinates are
multiplied before matching and divided back before the table is returned.
However, when both a non-unit `scale` and `segments` are supplied, the exact
0.8.0 implementation passes the scaled interpolation step directly to the
segmentation painter as an array-index shift. It does not divide that shift
back into voxel units first. The filled mask can therefore be displaced by a
different amount from its returned ZYX or YX center.

This combination has not been used by the project and should not be treated as
verified 3D post-processing. A future implementation should first reproduce
the behavior on a small synthetic anisotropic example and resolve the unit
mismatch before evaluating rewritten 3D masks. This reference records the
caveat but does not modify the Ultrack package.

### 6.4 Project status and evaluation requirements

No current project script calls `close_tracks_gaps`; all reported results are
raw Ultrack solver outputs. Therefore there is no project default for
`max_gap` or `max_radius`, and no improvement from gap closing has been
established.

If this optional stage is tested later:

1. preserve the raw `tracks.csv`, segmentation, CTC export, and evaluation;
2. write post-processed tracks and masks to a separate directory with
   `max_gap`, `max_radius`, `spatial_columns`, `scale`, and package versions;
3. record every joined track-ID pair, gap length, and endpoint distance;
4. inspect crowded regions, entries and exits, and nearby divisions in the
   original movie; and
5. evaluate the raw and post-processed outputs separately on a development
   sequence before using an untouched sequence for comparison.

Gap closing can be rerun from saved solved tracks and track-labeled masks. It
does not require Cellpose, StarDist, watershed, Ultrack segmentation, linking,
or solving to run again. If solver weights are changed, however, gap closing
must be repeated because the set of track starts and ends can change.

Ultrack exposes other track utilities, but they should be added to this master
reference only when the project uses or evaluates them. Export-time CTC track
stitching is also a separate option intended for the special first-frame track
selection workflow; it is not the general missing-frame gap closer documented
here.

Sources for this section are the exact Ultrack 0.8.0 wheel, the official
[`close_tracks_gaps` API](https://royerlab.github.io/ultrack/api.html#ultrack.tracks.close_tracks_gaps),
the official [tracking-performance tuning guide](https://royerlab.github.io/ultrack/optimizing.html),
the SciPy documentation for
[`linear_sum_assignment`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html)
and [`cdist`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.cdist.html),
and the project's
[`ultrack-parameter-analysis.md`](ultrack-parameter-analysis.md).

## 7. Parameter interactions

Parameters should be interpreted according to the earliest stage they can
change. Every stage restricts the possibilities available to the next one:

```text
segmentation model
    -> foreground and contour maps
    -> per-frame segment hypotheses
    -> adjacent-frame candidate links
    -> solver-selected tracks
    -> optional post-processed tracks
```

A later parameter can select differently among possibilities that survived,
but it usually cannot recreate something removed earlier. This gives a useful
diagnostic order:

| Observed problem | First question | Earliest relevant stage | What later stages cannot do |
| --- | --- | --- | --- |
| A cell is absent from the saved model labels | Did the segmentation method detect any of its pixels? | Cellpose, StarDist, or watershed | Label conversion and Ultrack cannot recover a cell with no foreground support. |
| A cell is present in saved labels but absent from Ultrack foreground | Was conversion correct, and did `threshold` retain it? | Label-to-contour conversion or Ultrack segmentation threshold | Linking and solving cannot select a segment outside the foreground map. |
| Foreground is present but no candidate has the desired cell boundary | Do the contour map and hierarchy contain the desired split or merge? | Contour `sigma`, `min_area`, `max_area`, `min_frontier`, hierarchy choice | Linking and solving can only select an existing hierarchy node. |
| Correct candidates exist in adjacent frames but have no edge | Are they inside `max_distance`, the neighbor shortlist, and any intensity filter? | Ultrack linking | Tracking weights cannot select an edge that was never stored. |
| Correct candidates and edge exist but the solver chooses another lineage | How do transformed link evidence and event penalties compare? | Ultrack tracking | Post-processing cannot reproduce the original global hypothesis selection. |
| The raw solution contains a short missing-detection gap | Is distance-only post-processing biologically justified? | Optional gap closing | Gap closing cannot prove identity from image or overlap evidence it does not inspect. |

### 7.1 Segmentation method, conversion, and hierarchy

#### Model confidence versus Ultrack foreground threshold

Cellpose's `cellprob_threshold`, StarDist's probability threshold, and the
watershed foreground calculation act on raw images before instance labels are
saved. They determine which pixels and instances reach Ultrack at all.
Ultrack's `segmentation_config.threshold` instead binarizes the later
foreground map.

The current project converts labels into a Boolean foreground. Consequently,
any Ultrack threshold from zero up to but not including one produces the same
foreground mask. Sweeping the default `0.5` would not reproduce a Cellpose or
StarDist confidence sweep. The model must be rerun to change its confidence
threshold; Ultrack segmentation onward must then be rerun because the saved
labels and converted maps changed.

#### Upstream size filters versus hierarchy area filters

Cellpose `min_size`, watershed `minimum_object_size`, and similar model-level
filters can delete a complete predicted object before conversion. Ultrack's
`min_area` and `max_area` instead prune or split candidate hypotheses inside
the converted foreground. Their numerical values are not interchangeable even
when they all use pixels or voxels.

Within Ultrack, `min_area_factor` also depends on `min_area`: the early
connected-component cutoff is approximately
`min_area / min_area_factor`. Increasing `min_area` therefore raises both the
early component cutoff and the final hierarchy cutoff unless the factor is
changed. Increasing `min_area_factor` has the opposite effect on the early
cutoff, retaining more tiny disconnected components, but does not remove the
final `min_area` pruning.

`max_area` is both a biological and computational constraint. Lowering it can
exclude fused-cell hypotheses and pre-split large foreground components;
raising it allows larger candidates and can increase hierarchy size. The
resulting number of hypotheses propagates into linking and the ILP, so an
apparently small area-range change can alter runtime as well as segmentation.

#### Contour smoothing versus frontier filtering

Contour `sigma` changes the boundary landscape before the hierarchy is built:
it spreads boundary evidence spatially and, for numeric sigma values, the
project's conversion normalizes each time point by its maximum. `min_frontier`
then merges hierarchy regions whose average shared contour strength is below a
threshold. These are complementary but not equivalent operations.

Because smoothing changes both the shape and relative values of the contour
map, a `min_frontier` value should not be transferred unchanged between sigma
settings without inspection. The effect is not guaranteed to be monotonic:
smoothing can strengthen continuity along one boundary while weakening or
spreading another after normalization. `max_noise` is also relative to this
contour scale, so it should remain fixed when studying sigma or frontier
effects.

For ensembles, logical-OR foreground can rescue a cell found by only one
method, but it can also introduce that method's false foreground. Equal-mean
contours strengthen boundaries shared across methods and dilute boundaries
unique to one method. Ensemble membership and weighting therefore interact
directly with `min_frontier` and hierarchy construction.

### 7.2 Linking eligibility and score

| Interaction | Direct consequence | Project implication |
| --- | --- | --- |
| `max_distance` and linking `scale` | `scale` establishes the distance units, while `max_distance` applies the hard radius in those units. | A 15-pixel 2D radius is not equivalent to a radius of 15 after applying 3D ZYX spacing. Record both values. |
| `max_distance` and motion field | A larger radius makes fast motion eligible, but does not restore mask overlap; a motion field shifts the target position and mask before distance and IoU are computed. | If correct pairs have zero IoU because motion exceeds cell size, test alignment separately instead of expanding only the radius. |
| `max_distance` and `max_neighbors` | The radius defines eligible sources, but only the `2 * max_neighbors` nearest are scored and only `max_neighbors` survive. | Increasing the radius may have no effect in a dense candidate graph unless the neighbor cap is also sufficient. |
| Segmentation hypotheses and `max_neighbors` | Every hierarchy node is a candidate, so several overlapping hypotheses for one biological cell can occupy the nearest-neighbor shortlist. | A neighbor count is not the same as the number of nearby biological cells; changes to area/frontier settings can change how restrictive the same cap is. |
| `distance_weight` and `max_distance` | `max_distance` determines whether an edge exists; `distance_weight` changes the score of an existing edge. | Tune the radius first so correct edges are available, then tune ranking. A distance penalty cannot rescue an excluded edge. |
| `distance_weight` and tracking `power` | Positive distance penalties can produce negative stored scores, while the default fourth power makes negative values positive again. | Inspect the stored score distribution before combining nonzero distance penalties with `link_function=power`. |
| `z_score_threshold` and linking `images` | The threshold is inactive unless images are explicitly passed to `link`. | Do not include it in the current sweep; activating it is a workflow change that must record the supplied images and preprocessing. |

`max_distance` and `max_neighbors` are hard graph-construction settings. If
they are too restrictive, no solver setting can restore the correct lineage.
If they are too permissive, the solver receives more ambiguous edges and a
larger optimization problem. Measurements should therefore record not only
the final tracking score but also edge counts, the fraction of candidates with
no links, and whether annotated associations are present in the graph.

Linking still connects only `t` to `t+1`. Neither a larger radius nor a smaller
distance penalty creates a direct `t`-to-`t+2` edge. Missing-frame repair is a
separate post-processing decision.

### 7.3 Link evidence and tracking-event penalties

The solver compares transformed link scores with the alternatives allowed by
appearance, disappearance, and division variables. For a weak continuation,
the relevant trade-off is not the link score alone: ending the earlier track
and starting a new one incurs the disappearance and appearance penalties
instead. Changing `power` or `bias` changes the link-evidence scale and can
therefore require retuning all three event weights.

| Interaction | Direct consequence | Project implication |
| --- | --- | --- |
| `link_function`, `power`, and event weights | The default fourth power strongly suppresses moderate IoUs before they are compared with event penalties. | Keep the transform fixed during the initial event-weight sweep. Results from identity and power transforms are not directly comparable at the same weights. |
| `bias` and lineage continuity | A negative bias penalizes every selected link and can make an appearance-plus-disappearance explanation preferable to a weak continuation. | Treat bias as part of the objective scale, not a harmless numeric offset. |
| `appear_weight` and `division_weight` | A later cell may be explained as a new lineage or as a second daughter when compatible links exist. | Tune the two together; the official guide recommends a division penalty equal to or more negative than the appearance penalty to reduce false divisions. |
| `division_weight` and `max_distance` | A less-negative division penalty cannot create daughter edges outside the linking radius or shortlist. | Verify both daughter links before interpreting missed divisions as a solver-weight problem. |
| `disappear_weight` and link availability | A more-negative disappearance penalty encourages continuation only when a usable outgoing edge exists; otherwise it can cause the candidate track to be omitted. | Follow the official recommendation to tune disappearance first, while checking selected-cell counts and not only track length. |
| `image_border_size` and appearance/disappearance | Spatial-border cells receive no appearance or disappearance penalty, and first/last-time-point events are also unpenalized. | Separate genuine interior breaks from expected entries and exits before estimating event penalties. |

More-negative appearance and disappearance weights can reduce the number of
short tracks, but this does not guarantee better continuity. The solver may
drop an entire weak track rather than pay its start and end penalties. Track
counts, missed detections, false detections, lineage starts, lineage ends, and
division errors should be examined together.

### 7.4 Solver disappearance versus post-processing gap closing

`disappear_weight` acts inside the global solver. It changes which hypotheses
and adjacent-frame links are selected, and it can remove a weak lineage
entirely. `close_tracks_gaps` acts only after that decision. It merges root
starts with terminal ends by endpoint distance and inserts straight-line rows;
it cannot revisit candidate segmentation or link evidence.

The two should not be tuned in one combined sweep. First establish a raw
solver baseline and tune event weights against raw tracking errors. Only then,
if short missing-detection gaps remain, evaluate gap closing as a separate
derived output. Otherwise post-processing can hide whether continuity improved
because of a better solver objective or because nearby track IDs were joined
afterward.

Gap-closing `max_radius` is not automatically related to linking
`max_distance`. Linking measures adjacent-frame candidate displacement and
uses overlap-based scoring; gap closing measures total endpoint displacement
across multiple elapsed frames and uses distance-only assignment. The values
may use the same physical scale, but they answer different questions and need
separate justification.

### 7.5 Windowing, overlap, and solver quality

`window_size=None` gives a single global optimization. Setting a finite window
reduces peak problem size but replaces that global solve with a sequence of
overlapping local solves. `overlap_size` supplies temporal context at their
boundaries. Larger windows and overlaps generally retain more global context
while increasing memory and runtime; a small overlap can make boundary choices
more sensitive to the order in which windows are solved.

Window settings also interact with `time_limit`: the limit applies to each
window, not the full sequence. `solution_gap` and early time-limit termination
control how completely each window is optimized. These settings can change the
returned tracks even though they are computational rather than biological.
They should remain fixed during parameter comparisons, and every run should
record whether its solver status was optimal or merely feasible.

Increasing segmentation candidates, `max_neighbors`, or `max_distance`
enlarges the downstream optimization. Windowing can make that problem
tractable, but it should not be used to conceal an unnecessarily broad
candidate graph. Tight, biologically justified area and movement constraints
should be established before approximating the solve with smaller windows.

### 7.6 Dimensional units

The workflow uses three different kinds of spatial units:

| Setting | Units | Affected stage |
| --- | --- | --- |
| Cellpose `diameter` | XY pixels in the input used for Cellpose scaling | Cellpose segmentation |
| Cellpose 3D `anisotropy` | Ratio of Z spacing to XY spacing | Cellpose 3D inference |
| contour `sigma` | Pixels in 2D or per-axis voxels in 3D | Label-to-contour conversion |
| `min_area`, `max_area` | Pixels in 2D or voxels in 3D | Ultrack segmentation hypotheses |
| linking `scale` | Multipliers that convert centroid coordinates into chosen distance units | Ultrack linking |
| gap-closing `scale` | Multipliers applied to exported endpoint coordinates | Optional post-processing |

Linking scale does not convert contour smoothing or hierarchy areas into
physical units. Likewise, Cellpose anisotropy does not automatically populate
Ultrack's linking or gap-closing scale. A 3D run must record each value
explicitly and in axis order.

### 7.7 Recommended tuning order for this project

The following order isolates the first stage capable of causing each error and
reuses completed outputs where possible:

1. **Validate saved segmentation labels.** Confirm that expected cells are
   present and inspect model-specific false positives, false negatives,
   mergers, and splits. Finish model-level threshold and 3D Cellpose tuning
   here.
2. **Validate foreground and contour maps.** Confirm Boolean foreground
   coverage and inspect contour evidence at desired cell boundaries. Complete
   contour-sigma comparisons before tuning hierarchy frontier values.
3. **Tune Ultrack segmentation constraints.** Measure cell-size distributions,
   set `min_area` and `max_area`, then inspect `min_area_factor` and
   `min_frontier` only where their corresponding error modes are present.
4. **Tune linking eligibility.** Measure adjacent-frame displacement in the
   correct units, establish `scale`, and set `max_distance` with tolerance.
   Verify correct edges before changing `max_neighbors` or `distance_weight`.
5. **Tune tracking events.** Hold the candidate nodes, links, and link
   transformation fixed. Tune disappearance first, then appearance and
   division together using event-specific diagnostics.
6. **Evaluate optional gap closing separately.** Only after the raw solver is
   understood, test explicit `max_gap` and `max_radius` values in a distinct
   output directory.
7. **Change scalability controls only when needed.** Keep worker counts,
   solver, threads, solution gap, time limit, window size, and overlap constant
   during scientific comparisons.

Use one development sequence for parameter selection and preserve another as
a less-biased comparison whenever annotations permit. Change one parameter or
one explicitly coupled group at a time, save the effective configuration, and
record intermediate counts in addition to final DET, SEG, TRA, and `OP_CTB`.

This synthesis is based on the exact-version implementations and authoritative
sources cited in Sections 1 through 6. If a later package version changes an
implementation caveat or default, update the originating parameter section
first and then revise the interaction described here.

## 8. Which stages must be rerun?

| Parameter source | Fixed inputs that can be reused | First stage that must be rerun | Final result requires |
| --- | --- | --- | --- |
| Segmentation method | Raw images | Segmentation method | Ultrack segmentation, linking, and solving |
| Label-to-contour conversion | Saved instance labels | Label-to-contour conversion | Ultrack segmentation, linking, and solving |
| Ultrack `SegmentationConfig` | Foreground and contour maps | Ultrack segmentation | Linking and solving |
| Ultrack `LinkingConfig` | Candidate segment hypotheses | Ultrack linking | Solving |
| Ultrack `TrackingConfig` | Candidate hypotheses and links | Ultrack solving | Export and evaluation |
| Gap-closing post-processing | Raw solved tracks | Gap closing | Separate post-processed export and evaluation |

## 9. Adapting Ultrack to a new dataset

A new dataset does not require every parameter in this reference to be swept.
First measure the properties that determine biological scale and movement, then
tune only the parameters connected to an observed failure. Parameters without
a dataset-specific justification should remain fixed and be recorded with their
source.

### 9.1 Dataset intake

Record these properties before selecting parameter values:

| Dataset property | Why it matters | Parameters it informs |
| --- | --- | --- |
| Array shape, axis order, and dimensionality | Prevents time, channel, and spatial axes from being interpreted incorrectly. | Cellpose `do_3D`, `z_axis`, and `channel_axis`; contour conversion; spatial columns used for linking and export |
| Physical voxel spacing and anisotropy | Distances measured in array coordinates do not represent the same physical distance along every axis when spacing is unequal. | Cellpose `anisotropy`; linking `scale`; gap-closing `scale`; interpretation of contour `sigma` |
| Typical cell diameter, area, or volume | Supplies a biological size scale and identifies implausibly small or large candidates. | Cellpose `diameter`; watershed size settings; Ultrack `min_area`, `max_area`, and `min_area_factor` |
| Frame interval and observed displacement | Determines how far a cell can plausibly move between consecutive frames and across a missing detection. | Linking `max_distance`; gap-closing `max_gap` and `max_radius` |
| Cell density and crowding | Determines how many plausible neighbors and competing segment hypotheses may exist locally. | Linking `max_neighbors`; contour `sigma`; segmentation `min_frontier`; segmentation-model thresholds |
| Division frequency and cells entering or leaving the field of view | Provides context for deciding whether track starts, ends, and divisions are biologically plausible. | Tracking appearance, disappearance, and division weights; `image_border_size` |
| Image channels, intensity behavior, and background noise | Determines which model inputs and preprocessing choices are appropriate. | Model channels; normalization; raw-image smoothing; model-confidence thresholds; optional linking images |
| Annotation type, spatial coverage, and annotated frames | Determines which outputs can be validated and which metrics are meaningful. | Development and holdout split; segmentation and tracking metrics; interpretation of public-data results |

These properties should be measured from representative images and metadata
rather than copied from a CTC dataset. When annotations cover only selected
slices or frames, record that limitation alongside every resulting metric.

### 9.2 Minimum viable tuning sequence

When time does not permit a broad parameter sweep, use this order:

1. Record the dataset dimensions, axis order, voxel spacing, frame interval,
   channels, and annotation coverage.
2. Inspect the saved segmentation labels and the converted foreground and
   contour maps on representative easy, crowded, dim, and noisy regions.
3. Set size, anisotropy, and spatial-scale parameters from measured cells and
   image metadata rather than inheriting values chosen for another dataset.
4. Set linking `max_distance` from observed consecutive-frame displacement,
   then verify that annotated correct links are present in the candidate graph.
   Increase `max_neighbors` only if crowding causes correct candidates to be
   discarded.
5. Tune appearance, disappearance, and division weights only after the needed
   segments and candidate links exist. A solver weight cannot recover a segment
   or edge removed by an earlier stage.
6. Evaluate gap closing separately from the raw solver output and retain both
   versions. Do not use post-processing to hide a systematic segmentation or
   linking failure.
7. Leave solver-engine, operational, and inactive parameters at their recorded
   defaults unless a specific failure or scalability limit motivates changing
   them.

Use a small development subset that represents the dataset's main failure
modes, and preserve different annotated data as a holdout when possible. Change
one parameter or one explicitly coupled group at a time. For every run, save
the effective configuration, package and model versions, input-data identifier,
qualitative observations, and applicable segmentation and tracking metrics.

## Authoritative sources

Use sources in this order when completing the parameter tables:

1. the source or runtime signature from the exact installed package version;
2. official version-matched API documentation;
3. the pretrained model's loaded configuration;
4. the project's effective configuration and scripts; and
5. the Ultrack paper or supplementary experiment configurations for context.

A paper's experiment value should be labeled as a paper setting, not as a
package default or a numerical limit.
