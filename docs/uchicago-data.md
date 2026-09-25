# UChicago Stem-Cell Data

The project may use selected time-lapse stem-cell movies provided by Amanda's group. The students will test existing tracking methods for course research under mentor supervision.

## Cluster location

Mentor: replace the placeholder below with the approved shared cluster path before student onboarding.

```text
<CLUSTER_PATH_TO_AMANDA_DATA>
```

Also copy `config/data_paths.example.yaml` to the ignored file `config/data_paths.yaml` and enter the same path there.

## Access and use

- Confirm that every student has access through the approved group or project permissions.
- Do not copy the data into GitHub, personal cloud storage, or other unapproved locations.
- Treat the original directory as read-only.
- Write converted data, crops, annotations, and results to a separate project directory.
- Do not publish raw or derived images outside the course without the data provider's approval.
- Record any limits on presentation, sharing, attribution, or future reuse.

## Metadata to collect

- biological sample and labeling target;
- microscopy modality and channels;
- array axis order and file format;
- number of time points and time interval;
- image size and voxel spacing in Z, Y, and X;
- bit depth and intensity normalization considerations;
- approximate cell count, density, and displacement;
- occurrence of division, entry/exit, death, or debris;
- preferred biological outputs from tracking.

## Data preparation

Never overwrite the original movies. Conversion scripts should preserve metadata or record it explicitly. For anisotropic 3D data, pass physical voxel spacing to methods that support it and document any resampling.
