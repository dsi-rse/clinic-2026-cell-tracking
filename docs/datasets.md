# Datasets

## Official download pages

- [2D+Time datasets](https://celltrackingchallenge.net/2d-datasets/)
- [3D+Time datasets](https://celltrackingchallenge.net/3d-datasets/)
- [Dataset descriptions](https://celltrackingchallenge.net/datasets/)
- [Annotation descriptions and format documents](https://celltrackingchallenge.net/annotations/)

Download the **training** archives when reproducing results locally because they include public reference annotations. Do not commit downloaded archives or extracted images to this repository.

## Initial dataset candidates

This is a starting list, not a final assignment.

| Dataset | Dimension | Biological/imaging relevance | Possible role |
|---|---:|---|---|
| Fluo-N2DH-GOWT1 | 2D+t | Fluorescent mouse stem-cell nuclei | Biologically relevant 2D benchmark |
| Fluo-C2DL-MSC | 2D+t | Fluorescent mesenchymal stem cells | Additional stem-cell benchmark |
| Fluo-N3DH-CHO | 3D+t | Fluorescent nuclei in a 3D sequence | Technically relevant 3D nuclear benchmark |
| Fluo-C3DL-MDA231 | 3D+t | Cells embedded in a 3D matrix | Irregular whole-cell 3D benchmark |
| Fluo-N3DH-SIM+ | 3D+t | Simulated fluorescent nuclei with exact truth | Controlled 3D debugging dataset |

## Selection criteria

Before final selection, compare each candidate with the UChicago movies:

- nucleus versus whole-cell labeling;
- 2D versus true 3D acquisition;
- voxel anisotropy and spatial resolution;
- time interval and displacement between frames;
- cell density, overlap, and image contrast;
- frequency of division, entry, exit, and death;
- dataset size and available compute.

Select approximately two 2D and one or two 3D datasets. Begin with small sequences or cropped volumes for installation and debugging.

## Local storage convention

Recommended cluster layout:

```text
<PROJECT_DATA_ROOT>/
  ctc/
    Fluo-N2DH-GOWT1/
    Fluo-N3DH-CHO/
  uchicago/
    amanda/
  derived/
  models/
  runs/
```

Record the actual root in an untracked `config/data_paths.yaml` copied from `config/data_paths.example.yaml`.
