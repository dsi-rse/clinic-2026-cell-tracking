"""Write a label movie in Cell Tracking Challenge (CTC) format.

Two modes:
  gt - ground truth from corrected labels:
         <out>/01_GT/TRA/man_trackTTT.tif + man_track.txt
         <out>/01_GT/SEG/man_segTTT.tif
       parents come from divisions.csv (columns parent,daughter,frame)
  res - a result to be scored:
         <out>/01_RES/maskTTT.tif + res_track.txt
       parents come from Ultrack's tracks.csv (track_id, parent_track_id), if given;

In both modes, each label ID is one track. If a label is missing in some frames and
then comes back, the CTC format needs separate tracks, so the later part gets a new
ID with the earlier part as its parent (and a note is printed).

Examples:
  python labels_to_ctc.py gt  run/corrected_labels.tif run/ctc_eval --frames 0:10 \
      --divisions run/divisions.csv
  python labels_to_ctc.py res run/tracked_labels.tif run/ctc_eval --frames 0:10 \
      --tracks_csv run/tracks.csv
  python labels_to_ctc.py res run/cellpose_labels.tif run/ctc_eval_cellpose --frames 0:10 \
      --single_frame
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage

MOVIE_NDIM = 3
MAX_WARNINGS = 20


def parse_args():
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("mode", choices=["gt", "res"])
    p.add_argument("labels", type=Path, help="T x Y x X label TIFF")
    p.add_argument("out_dir", type=Path, help="writes 01_GT/ or 01_RES/ in here")
    p.add_argument("--frames", default="all", help="'all' or 'a:b' (b exclusive)")
    p.add_argument("--sequence", default="01", help="sequence name in folder names")
    p.add_argument("--divisions", type=Path, help="gt: divisions.csv")
    p.add_argument("--tracks_csv", type=Path, help="res: Ultrack tracks.csv")
    p.add_argument("--single_frame", action="store_true", help="res: one-frame tracks")
    return p.parse_args()


def select_frames(labels, spec):
    """Keep frames a:b, renumbered from 0; return (labels, first original frame)."""
    if spec == "all":
        return labels, 0
    start, stop = (int(s) if s else None for s in spec.split(":"))
    return labels[start:stop], start or 0


def check_pieces(labels):
    """Print labels that consist of several separate pieces in one frame."""
    found = 0
    for t, frame in enumerate(labels):
        ids = np.unique(frame)
        for i in ids[ids > 0]:
            _, n = ndimage.label(frame == i)
            if n > 1:
                found += 1
                if found <= MAX_WARNINGS:
                    print(f"  warning: label {i} has {n} separate pieces in frame {t}")
    if found:
        print(f"  {found} label/frame pairs with several pieces (check them in napari)")


def parents_from_divisions(path, first):
    """Read divisions.csv into {daughter: parent}."""
    if path is None:
        return {}
    df = pd.read_csv(path)
    missing = {"parent", "daughter"} - set(df.columns)
    if missing:
        raise SystemExit(f"{path} needs columns parent,daughter (missing {missing})")
    if "frame" in df.columns and first:
        print(f"  note: frames in {path.name} are taken as original frame numbers")
    return dict(zip(df["daughter"].astype(int), df["parent"].astype(int)))


def parents_from_tracks_csv(path):
    """Read Ultrack's tracks.csv into {track_id: parent_track_id}."""
    if path is None:
        return {}
    df = pd.read_csv(path)
    if "parent_track_id" not in df.columns:
        print(f"  note: no parent_track_id column in {path.name}; no divisions used")
        return {}
    pairs = df[["track_id", "parent_track_id"]].drop_duplicates()
    return {int(t): int(p) for t, p in pairs.itertuples(index=False) if p > 0}


def split_gaps(labels, parents):
    """Give each continuous run of a label its own track; return (labels, track table)."""
    labels = labels.astype(np.uint32).copy()
    present = {}
    for t, frame in enumerate(labels):
        for i in np.unique(frame):
            if i:
                present.setdefault(int(i), []).append(t)
    next_id = int(labels.max()) + 1
    tracks = {}
    last_part = {}
    for i in sorted(present):
        frames = present[i]
        runs, start = [], frames[0]
        for a, b in zip(frames, frames[1:] + [None]):
            if b is None or b != a + 1:
                runs.append((start, a))
                start = b
        prev = None
        for k, (b, e) in enumerate(runs):
            new = i if k == 0 else next_id
            if k:
                next_id += 1
                for t in range(b, e + 1):
                    labels[t][labels[t] == i] = new
                print(
                    f"  label {i} is missing before frame {b}: continued as track {new}"
                )
            tracks[new] = [b, e, prev if prev is not None else 0]
            prev = new
        last_part[i] = prev
    for daughter, parent in parents.items():
        if daughter in tracks and parent in last_part:
            tracks[daughter][2] = last_part[parent]
        elif daughter in tracks:
            print(f"  warning: parent {parent} of {daughter} not found in these frames")
    for i, (b, e, p) in tracks.items():
        if p and tracks.get(p, [0, b])[1] >= b:
            print(
                f"  warning: parent {p} of {i} still exists at frame {b}; parent ignored"
            )
            tracks[i][2] = 0
    return labels, tracks


def single_frame_tracks(labels):
    """Relabel so every object in every frame is its own one-frame track."""
    out = np.zeros(labels.shape, dtype=np.uint32)
    tracks, next_id = {}, 1
    for t, frame in enumerate(labels):
        for i in np.unique(frame):
            if i:
                out[t][frame == i] = next_id
                tracks[next_id] = [t, t, 0]
                next_id += 1
    return out, tracks


def write_track_file(path, tracks):
    """Write CTC 'L B E P' lines."""
    lines = [f"{i} {b} {e} {p}" for i, (b, e, p) in sorted(tracks.items())]
    path.write_text("\n".join(lines) + "\n")


def main():
    """Convert and write the CTC folders."""
    a = parse_args()
    labels = tifffile.imread(str(a.labels))
    if labels.ndim != MOVIE_NDIM:
        raise SystemExit(f"expected T x Y x X labels, got shape {labels.shape}")
    labels, first = select_frames(labels, a.frames)
    print(f"{a.labels.name}: {labels.shape[0]} frames (original frames {first}..)")
    check_pieces(labels)

    if a.mode == "res" and a.single_frame:
        labels, tracks = single_frame_tracks(labels)
    else:
        if a.mode == "gt":
            parents = parents_from_divisions(a.divisions, first)
        else:
            parents = parents_from_tracks_csv(a.tracks_csv)
        labels, tracks = split_gaps(labels, parents)

    if a.mode == "gt":
        tra = a.out_dir / f"{a.sequence}_GT" / "TRA"
        seg = a.out_dir / f"{a.sequence}_GT" / "SEG"
        tra.mkdir(parents=True, exist_ok=True)
        seg.mkdir(parents=True, exist_ok=True)
        for t, frame in enumerate(labels):
            tifffile.imwrite(
                str(tra / f"man_track{t:03d}.tif"), frame.astype(np.uint16)
            )
            tifffile.imwrite(str(seg / f"man_seg{t:03d}.tif"), frame.astype(np.uint16))
        write_track_file(tra / "man_track.txt", tracks)
        out = tra.parent
    else:
        out = a.out_dir / f"{a.sequence}_RES"
        out.mkdir(parents=True, exist_ok=True)
        for t, frame in enumerate(labels):
            tifffile.imwrite(str(out / f"mask{t:03d}.tif"), frame.astype(np.uint16))
        write_track_file(out / "res_track.txt", tracks)
    n_linked = sum(1 for _, _, p in tracks.values() if p)
    print(
        f"wrote {out}: {len(tracks)} tracks, {n_linked} with a parent (divisions or gaps)"
    )


if __name__ == "__main__":
    main()