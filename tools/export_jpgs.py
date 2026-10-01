"""Save every figure of an executed notebook as JPG, plus a full-resolution pit map.

usage: python export_jpgs.py executed.ipynb pit_outputs/<run> jpg_folder
"""
import base64
import io
import json
import math
import re
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from PIL import Image

notebook, run_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)


def slug(text):
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')[:40]


# 1. Every figure shown in the notebook, named after its section.
section, count = 'start', {}
for cell in json.load(open(notebook))['cells']:
    if cell['cell_type'] == 'markdown':
        heading = next((l for l in ''.join(cell['source']).splitlines() if l.startswith('## ')), None)
        if heading:
            section = slug(heading[3:])
        continue
    for output in cell.get('outputs', []):
        data = output.get('data', {}).get('image/png')
        if not data:
            continue
        count[section] = count.get(section, 0) + 1
        image = Image.open(io.BytesIO(base64.b64decode(data))).convert('RGB')
        name = f'{section}_{count[section]}.jpg' if count[section] > 1 or section == 'gallery' else f'{section}.jpg'
        image.save(out_dir / name, quality=92)

# 2. Full-resolution map: Sentinel-2 true colour with every pit outlined.
with rasterio.open(run_dir / 'stack.tif') as src:
    names = list(src.descriptions)             # band names were stored when downloading
    rgb = np.stack([src.read(names.index(b) + 1) for b in ('B4', 'B3', 'B2')]).astype('float32')
    nodata = (rgb == -32768).any(axis=0)
    rgb = np.where(nodata, np.nan, rgb / 1e4)
    bounds = src.bounds
lo, hi = np.nanpercentile(rgb, [2, 98])
rgb = np.clip(np.nan_to_num((np.transpose(rgb, (1, 2, 0)) - lo) / (hi - lo)), 0, 1)
pits = gpd.read_file(run_dir / 'pits.gpkg') if (run_dir / 'pits.gpkg').exists() else None

height, width = rgb.shape[:2]
scale = min(1.0, 5000 / max(width, height))            # keep the JPG under ~5000 px
fig = plt.figure(figsize=(width * scale / 100, height * scale / 100 + 0.6), dpi=100)
ax = fig.add_axes([0, 0, 1, height / (height + 60 / scale)])
ax.imshow(rgb, extent=(bounds.left, bounds.right, bounds.bottom, bounds.top), interpolation='nearest')
if pits is not None and len(pits):
    old, new = pits[pits.new_pit == 0], pits[pits.new_pit == 1]
    if len(old):
        old.boundary.plot(ax=ax, color='#ff00ff', linewidth=0.8)
    if len(new):
        new.boundary.plot(ax=ax, color='#ff2020', linewidth=0.8)
ax.set_xlim(bounds.left, bounds.right)
ax.set_ylim(bounds.bottom, bounds.top)
ax.axis('off')
n = 0 if pits is None else len(pits)
n_new = 0 if pits is None else int((pits.new_pit == 1).sum())
fig.text(0.01, 1 - 0.5 / (height * scale / 100 + 0.6),
         f'{n} pits detected ({n_new} new = red, {n - n_new} older = magenta) — Sentinel-2 10 m, {run_dir.name}',
         fontsize=max(8, int(14 * scale)), va='center')
fig.savefig(out_dir / 'pit_map_full_resolution.jpg', dpi=100, pil_kwargs={'quality': 90})
plt.close(fig)

for path in sorted(out_dir.glob('*.jpg')):
    print(f'{path.name:45s} {Image.open(path).size}')
