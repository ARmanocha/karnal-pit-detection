#!/usr/bin/env python3
"""
Stage 2 of the pit workflow: confirm and outline pits with high-resolution
imagery and a YOLOv8 detector.

  Stage 1  Earth Engine (mine_pit_detection.js): Sentinel data at 10 m over the
           whole district -> karnal_pits_list_<dates>.csv (lon, lat, area_ha, ...)
  Stage 2  this script: your high-resolution GeoTIFF(s) at ~0.3-3 m
           -> confirmed pits with boxes, plus every Stage 1 candidate marked
              confirmed / not confirmed

Commands
  chips   Cut 1 km x 1 km chips around the candidates, pre-labelled by the
          model, to correct in LabelMe. This is your local training data.
  train   Fine-tune the detector on the corrected chips (train/val split by
          area, so neighbouring chips never end up on both sides).
  detect  Run the detector around every candidate, or over the whole image
          with --scan, and write the results.

Typical run
  python pit_verify.py chips  --candidates karnal_pits_list.csv --imagery karnal.tif --weights best.pt --out chips
  (correct the boxes in LabelMe:  labelme chips --labels pit --nodata)
  python pit_verify.py train  --chips chips --weights best.pt --epochs 60
  python pit_verify.py detect --candidates karnal_pits_list.csv --imagery karnal.tif \
         --weights runs/pit_finetune/weights/best.pt --scan --out results

Starting weights: best.pt from
github.com/BapakmuLah/Satellit-Based-Open-Pit-Mining-Detection — YOLOv8 trained
on ~1 m imagery of hillside quarries in China. It has never seen flat-land sand
or brick-kiln pits, so run `chips` + `train` before trusting its output.

Requirements: pip install ultralytics rasterio shapely pyproj pandas pillow
"""

import argparse
import json
import math
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from pyproj import CRS, Transformer
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform
from rasterio.windows import Window
from shapely import STRtree
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform as reproject_geometry

CHIP_PX = 1024          # the starting model was trained on 1024 x 1024 tiles
LABEL = 'pit'


# -----------------------------------------------------------------------------
# Imagery
# -----------------------------------------------------------------------------
def utm_crs(lon, lat):
    zone = int((lon + 180) // 6) + 1
    return CRS.from_epsg((32600 if lat >= 0 else 32700) + zone)


def to_rgb8(chip):
    """(bands, H, W) array of any dtype -> (H, W, 3) uint8, 2-98 % stretch per band."""
    if chip.shape[0] == 1:
        chip = np.repeat(chip, 3, axis=0)
    if chip.dtype != np.uint8:
        out = np.zeros(chip.shape, dtype=np.uint8)
        for i, band in enumerate(chip.astype('float32')):
            valid = band[band > 0]
            if valid.size:
                lo, hi = np.percentile(valid, (2, 98))
                out[i] = np.clip((band - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
        chip = out
    return np.ascontiguousarray(np.transpose(chip[:3], (1, 2, 0)))


class Imagery:
    """GeoTIFFs warped on the fly to one UTM grid at `res` metres per pixel."""

    def __init__(self, paths, crs, res, bands):
        self.crs, self.res, self.bands = crs, res, bands
        self.vrts = []
        for path in paths:
            src = rasterio.open(path)
            transform, width, height = calculate_default_transform(
                src.crs, crs, src.width, src.height, *src.bounds, resolution=res)
            self.vrts.append(WarpedVRT(src, crs=crs, transform=transform, width=width,
                                       height=height, resampling=Resampling.bilinear))

    def chip(self, x, y):
        """CHIP_PX x CHIP_PX RGB chip centred on UTM (x, y) and its transform, or None."""
        for vrt in self.vrts:
            left, bottom, right, top = vrt.bounds
            if left <= x <= right and bottom <= y <= top:
                return self._read(vrt, x, y)
        return None

    def _read(self, vrt, x, y):
        t = vrt.transform
        col0 = int(round((x - t.c) / t.a - CHIP_PX / 2))
        row0 = int(round((y - t.f) / t.e - CHIP_PX / 2))
        c0, r0 = max(col0, 0), max(row0, 0)
        c1, r1 = min(col0 + CHIP_PX, vrt.width), min(row0 + CHIP_PX, vrt.height)
        if c1 <= c0 or r1 <= r0:
            return None
        data = vrt.read(self.bands, window=Window(c0, r0, c1 - c0, r1 - r0))
        chip = np.zeros((len(self.bands), CHIP_PX, CHIP_PX), dtype=data.dtype)
        chip[:, r0 - row0:r1 - row0, c0 - col0:c1 - col0] = data
        if not chip.any():
            return None
        return to_rgb8(chip), t * Affine.translation(col0, row0)

    def scan_centres(self, overlap_px):
        """Chip centres that cover every image, overlapping by `overlap_px`."""
        half = CHIP_PX * self.res / 2
        step = (CHIP_PX - overlap_px) * self.res

        def centres(lo, hi):
            if hi - lo <= 2 * half:
                return [(lo + hi) / 2]
            return list(np.arange(lo + half, hi - half, step)) + [hi - half]

        for vrt in self.vrts:
            left, bottom, right, top = vrt.bounds
            for y in centres(bottom, top):
                for x in centres(left, right):
                    yield x, y


# -----------------------------------------------------------------------------
# Detector + geometry
# -----------------------------------------------------------------------------
class Detector:
    def __init__(self, weights, conf):
        from ultralytics import YOLO
        self.model = YOLO(weights)
        self.conf = conf

    def __call__(self, rgb):
        """[(x1, y1, x2, y2, score), ...] in chip pixels."""
        result = self.model.predict(Image.fromarray(rgb), imgsz=CHIP_PX, conf=self.conf,
                                    verbose=False)[0]
        return [tuple(b) + (float(s),) for b, s in
                zip(result.boxes.xyxy.tolist(), result.boxes.conf.tolist())]


def detect_on_chip(detector, rgb):
    """Detections, minus boxes lying mostly on no-data (black padding at image edges)."""
    nodata = rgb.sum(axis=2) == 0
    kept = []
    for box in detector(rgb):
        x1, y1, x2, y2 = (int(round(v)) for v in box[:4])
        patch = nodata[max(y1, 0):max(y2, 1), max(x1, 0):max(x2, 1)]
        if patch.size and patch.mean() <= 0.5:
            kept.append(box)
    return kept


def box_to_polygon(box, transform):
    x1, y1, x2, y2 = box[:4]
    return Polygon([transform * (x1, y1), transform * (x2, y1),
                    transform * (x2, y2), transform * (x1, y2)])


def merge_duplicates(detections, iou_threshold=0.5, containment=0.8):
    """Non-maximum suppression across overlapping chips (keeps the highest score)."""
    if not detections:
        return []
    geoms = [d['geom'] for d in detections]
    tree = STRtree(geoms)
    suppressed, kept = set(), []
    for i in sorted(range(len(detections)), key=lambda k: -detections[k]['score']):
        if i in suppressed:
            continue
        kept.append(detections[i])
        for j in tree.query(geoms[i]):
            if j == i or j in suppressed:
                continue
            inter = geoms[i].intersection(geoms[j]).area
            union = geoms[i].area + geoms[j].area - inter
            smaller = min(geoms[i].area, geoms[j].area)
            if inter / union >= iou_threshold or inter / smaller >= containment:
                suppressed.add(j)
    return kept


def load_candidates(path):
    df = pd.read_csv(path)
    missing = {'lon', 'lat'} - set(df.columns)
    if missing:
        raise SystemExit(f'{path} has no {sorted(missing)} column(s); '
                         'use the pits_list CSV exported by the Earth Engine script.')
    df = df.reset_index(drop=True)
    df.insert(0, 'cand_id', df.index)
    return df


def project_candidates(df, crs):
    to_utm = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
    xs, ys = to_utm.transform(df['lon'].to_numpy(), df['lat'].to_numpy())
    return np.asarray(xs), np.asarray(ys)


def choose_crs(candidates, imagery_paths):
    if candidates is not None and len(candidates):
        return utm_crs(candidates['lon'].mean(), candidates['lat'].mean())
    with rasterio.open(imagery_paths[0]) as src:
        to_wgs = Transformer.from_crs(src.crs, 'EPSG:4326', always_xy=True)
        lon, lat = to_wgs.transform((src.bounds.left + src.bounds.right) / 2,
                                    (src.bounds.bottom + src.bounds.top) / 2)
    return utm_crs(lon, lat)


# -----------------------------------------------------------------------------
# chips: training data for LabelMe
# -----------------------------------------------------------------------------
def cmd_chips(args, detector=None):
    candidates = load_candidates(args.candidates)
    if 'prob' in candidates.columns:
        candidates = candidates.sort_values('prob', ascending=False)
    crs = choose_crs(candidates, args.imagery)
    imagery = Imagery(args.imagery, crs, args.res, args.bands)
    xs, ys = project_candidates(candidates, crs)
    if detector is None and args.weights:
        detector = Detector(args.weights, args.conf)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for (_, cand), x, y in zip(candidates.iterrows(), xs, ys):
        if len(rows) >= args.max_chips:
            break
        chip = imagery.chip(x, y)
        if chip is None:
            continue
        rgb, transform = chip
        name = f"chip_{int(cand['cand_id']):05d}"
        Image.fromarray(rgb).save(out / f'{name}.png')

        shapes = []
        for x1, y1, x2, y2, score in (detect_on_chip(detector, rgb) if detector else []):
            shapes.append({'label': LABEL, 'points': [[x1, y1], [x2, y2]], 'group_id': None,
                           'description': f'model score {score:.2f}',
                           'shape_type': 'rectangle', 'flags': {}})
        labelme = {'version': '5.4.1', 'flags': {}, 'shapes': shapes,
                   'imagePath': f'{name}.png', 'imageData': None,
                   'imageHeight': CHIP_PX, 'imageWidth': CHIP_PX}
        (out / f'{name}.json').write_text(json.dumps(labelme, indent=1))
        rows.append({'chip': name, 'cand_id': int(cand['cand_id']), 'x': x, 'y': y,
                     'epsg': crs.to_epsg(), 'res': args.res})

    pd.DataFrame(rows).to_csv(out / 'chips_index.csv', index=False)
    print(f'{len(rows)} chips written to {out}/ '
          f'({"pre-labelled by the model" if detector else "no pre-labels"}).')
    print('Next: correct every chip in LabelMe — delete boxes that are not pits, draw the '
          'missed ones, and keep chips with no pits (they teach the model what to ignore).')
    print(f'      labelme {out} --labels {LABEL} --nodata')


# -----------------------------------------------------------------------------
# train: fine-tune on the corrected chips
# -----------------------------------------------------------------------------
def labelme_to_yolo(labelme):
    """LabelMe rectangles / polygons -> YOLO lines 'class cx cy w h' (normalised)."""
    w, h = labelme['imageWidth'], labelme['imageHeight']
    lines = []
    for shape in labelme['shapes']:
        if shape.get('label') != LABEL or shape.get('shape_type') not in ('rectangle', 'polygon'):
            continue
        pts = np.asarray(shape['points'], dtype=float)
        x1, y1 = np.clip(pts.min(axis=0), 0, [w, h])
        x2, y2 = np.clip(pts.max(axis=0), 0, [w, h])
        if x2 - x1 < 2 or y2 - y1 < 2:
            continue
        lines.append(f'0 {(x1 + x2) / 2 / w:.6f} {(y1 + y2) / 2 / h:.6f} '
                     f'{(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}')
    return lines


def build_yolo_dataset(chips_dir, out_dir, val_fraction=0.2, block_m=5000, seed=42):
    """YOLO dataset split by 5 km blocks, so neighbouring chips never land on both sides."""
    chips_dir, out_dir = Path(chips_dir), Path(out_dir)
    index = pd.read_csv(chips_dir / 'chips_index.csv')
    index = index[[(chips_dir / f'{c}.json').exists() for c in index['chip']]]
    if index.empty:
        raise SystemExit(f'No labelled chips found in {chips_dir}.')

    blocks = (index['x'] // block_m).astype(int).astype(str) + '_' + \
             (index['y'] // block_m).astype(int).astype(str)
    if blocks.nunique() < 2:
        print(f'All chips lie in one {block_m / 1000:g} km block, so the split is by chip; '
              'label chips from more of the district for an honest validation score.')
        blocks = index['chip']
    unique_blocks = sorted(blocks.unique())
    random.Random(seed).shuffle(unique_blocks)
    val_blocks, n_val = set(), 0
    for b in unique_blocks:
        if n_val >= val_fraction * len(index) or len(val_blocks) == len(unique_blocks) - 1:
            break
        val_blocks.add(b)
        n_val += int((blocks == b).sum())

    counts = {'train': [0, 0], 'val': [0, 0]}   # chips, boxes
    for (_, row), block in zip(index.iterrows(), blocks):
        split = 'val' if block in val_blocks else 'train'
        (out_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
        (out_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)
        lines = labelme_to_yolo(json.loads((chips_dir / f"{row['chip']}.json").read_text()))
        shutil.copy(chips_dir / f"{row['chip']}.png", out_dir / 'images' / split)
        (out_dir / 'labels' / split / f"{row['chip']}.txt").write_text('\n'.join(lines))
        counts[split][0] += 1
        counts[split][1] += len(lines)

    data_yaml = out_dir / 'data.yaml'
    data_yaml.write_text(f'path: {out_dir.resolve()}\ntrain: images/train\n'
                         f'val: images/val\nnames:\n  0: {LABEL}\n')
    for split, (n_chips, n_boxes) in counts.items():
        print(f'{split}: {n_chips} chips, {n_boxes} pit boxes')
    return data_yaml


def cmd_train(args):
    data_yaml = build_yolo_dataset(args.chips, args.dataset)
    from ultralytics import YOLO
    YOLO(args.weights).train(
        data=str(data_yaml), imgsz=CHIP_PX, epochs=args.epochs, batch=args.batch,
        patience=20, seed=42, project=args.project, name='pit_finetune', exist_ok=True,
        # Satellite images have no "up": flips and rotations are free extra examples.
        fliplr=0.5, flipud=0.5, degrees=90)
    print(f'Fine-tuned weights: {Path(args.project) / "pit_finetune" / "weights" / "best.pt"}')


# -----------------------------------------------------------------------------
# detect: confirm candidates / scan the whole image
# -----------------------------------------------------------------------------
def cmd_detect(args, detector=None):
    candidates = load_candidates(args.candidates) if args.candidates else None
    if candidates is None and not args.scan:
        raise SystemExit('Give --candidates, or --scan to search the whole image.')
    crs = choose_crs(candidates, args.imagery)
    imagery = Imagery(args.imagery, crs, args.res, args.bands)
    detector = detector or Detector(args.weights, args.conf)

    centres = []
    if candidates is not None:
        centres += list(zip(*project_candidates(candidates, crs)))
    if args.scan:
        centres += list(imagery.scan_centres(args.overlap))

    detections = []
    for i, (x, y) in enumerate(centres, 1):
        chip = imagery.chip(x, y)
        if chip is not None:
            rgb, transform = chip
            for box in detect_on_chip(detector, rgb):
                detections.append({'geom': box_to_polygon(box, transform), 'score': box[4]})
        if i % 100 == 0:
            print(f'  {i}/{len(centres)} chips, {len(detections)} raw detections')
    pits = merge_duplicates(detections)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    to_wgs = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True).transform
    tree = STRtree([p['geom'] for p in pits]) if pits else None

    near_candidate = {}
    if candidates is not None:
        xs, ys = project_candidates(candidates, crs)
        results = []
        for (_, cand), x, y in zip(candidates.iterrows(), xs, ys):
            covered = imagery.chip(x, y) is not None
            area_ha = float(cand['area_ha']) if 'area_ha' in cand else 0.0
            radius = max(args.match_m, math.sqrt(area_ha * 1e4 / math.pi) + args.match_m / 2)
            zone = Point(x, y).buffer(radius)
            hits = [int(j) for j in tree.query(zone)
                    if pits[j]['geom'].intersects(zone)] if tree is not None else []
            for j in hits:
                near_candidate.setdefault(j, int(cand['cand_id']))
            results.append({**cand.to_dict(), 'imagery_covers': covered,
                            'confirmed': bool(hits),
                            'best_score': max((pits[j]['score'] for j in hits), default=None)})
        checked = pd.DataFrame(results)
        checked.to_csv(out / 'candidates_checked.csv', index=False)
        covered = checked['imagery_covers']
        print(f"Stage 1 candidates: {len(checked)} | covered by your imagery: {int(covered.sum())} | "
              f"confirmed: {int(checked.loc[covered, 'confirmed'].sum())}")

    features = []
    for j, pit in enumerate(pits):
        centroid = reproject_geometry(to_wgs, pit['geom'].centroid)
        features.append({'type': 'Feature',
                         'geometry': mapping(reproject_geometry(to_wgs, pit['geom'])),
                         'properties': {'score': round(pit['score'], 3),
                                        'area_m2': round(pit['geom'].area, 1),
                                        'lon': round(centroid.x, 6), 'lat': round(centroid.y, 6),
                                        'stage1_candidate': near_candidate.get(j)}})
    (out / 'pits_detected.geojson').write_text(
        json.dumps({'type': 'FeatureCollection', 'features': features}))
    print(f'{len(pits)} pits detected -> {out / "pits_detected.geojson"} '
          f'({sum(1 for f in features if f["properties"]["stage1_candidate"] is None)} '
          f'not flagged by Stage 1)')


# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    def imagery_args(p):
        p.add_argument('--imagery', nargs='+', required=True, help='high-resolution GeoTIFF(s)')
        p.add_argument('--bands', type=lambda s: [int(b) for b in s.split(',')], default=[1, 2, 3],
                       help='red,green,blue band numbers (PlanetScope 4-band: 3,2,1)')
        p.add_argument('--res', type=float, default=1.0,
                       help='metres per pixel for the chips (the starting model saw ~1 m)')
        p.add_argument('--conf', type=float, default=0.25, help='minimum detection score')

    p = sub.add_parser('chips', help='cut pre-labelled chips around candidates for LabelMe')
    p.add_argument('--candidates', required=True, help='pits_list CSV from Earth Engine')
    p.add_argument('--weights', help='detector used to pre-label the chips (optional)')
    p.add_argument('--max-chips', type=int, default=300)
    p.add_argument('--out', default='chips')
    imagery_args(p)

    p = sub.add_parser('train', help='fine-tune on corrected chips')
    p.add_argument('--chips', default='chips')
    p.add_argument('--weights', required=True, help='starting weights, e.g. best.pt from the repo')
    p.add_argument('--dataset', default='pit_dataset')
    p.add_argument('--project', default='runs')
    p.add_argument('--epochs', type=int, default=60)
    p.add_argument('--batch', type=int, default=8)

    p = sub.add_parser('detect', help='confirm candidates and/or scan the whole image')
    p.add_argument('--candidates', help='pits_list CSV from Earth Engine')
    p.add_argument('--weights', required=True)
    p.add_argument('--scan', action='store_true', help='also search the whole image')
    p.add_argument('--overlap', type=int, default=192, help='chip overlap in pixels for --scan')
    p.add_argument('--match-m', type=float, default=60,
                   help='a detection this close to a candidate confirms it')
    p.add_argument('--out', default='results')
    imagery_args(p)

    args = parser.parse_args()
    {'chips': cmd_chips, 'train': cmd_train, 'detect': cmd_detect}[args.command](args)


if __name__ == '__main__':
    main()
