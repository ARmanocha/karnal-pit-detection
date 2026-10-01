"""Save every figure of an executed notebook as JPG, plus a numbered full-resolution pit map with a
latitude / longitude grid and coordinate tables of the new and the largest pits.

usage: python export_jpgs.py executed.ipynb pit_outputs/<run> jpg_folder
"""
import base64
import io
import json
import re
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.patheffects as effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from PIL import Image
from pyproj import Transformer

notebook, run_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)
OUTLINE = [effects.withStroke(linewidth=2, foreground='black')]


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

# 2. Full-resolution map: Sentinel-2 true colour, every pit outlined and numbered, latitude / longitude grid.
with rasterio.open(run_dir / 'stack.tif') as src:
    names = list(src.descriptions)             # band names were stored when downloading
    rgb = np.stack([src.read(names.index(b) + 1) for b in ('B4', 'B3', 'B2')]).astype('float32')
    rgb = np.where((rgb == -32768).any(axis=0), np.nan, rgb / 1e4)
    bounds, crs = src.bounds, src.crs
lo, hi = np.nanpercentile(rgb, [2, 98])
rgb = np.clip(np.nan_to_num((np.transpose(rgb, (1, 2, 0)) - lo) / (hi - lo)), 0, 1)
pits = gpd.read_file(run_dir / 'pits.gpkg').to_crs(crs) if (run_dir / 'pits.gpkg').exists() else None

height, width = rgb.shape[:2]
scale = min(1.0, 5000 / max(width, height))            # keep the JPG under ~5000 px
fig = plt.figure(figsize=(width * scale / 100, height * scale / 100), dpi=100)
ax = fig.add_axes([0, 0, 1, 1])
ax.imshow(rgb, extent=(bounds.left, bounds.right, bounds.bottom, bounds.top), interpolation='nearest')

# Latitude / longitude grid, drawn as curves (UTM is not aligned with degrees).
to_utm = Transformer.from_crs('EPSG:4326', crs, always_xy=True)
to_wgs = Transformer.from_crs(crs, 'EPSG:4326', always_xy=True)
corner_lon, corner_lat = to_wgs.transform([bounds.left, bounds.right, bounds.left, bounds.right],
                                          [bounds.bottom, bounds.bottom, bounds.top, bounds.top])
step = 0.05 if max(corner_lon) - min(corner_lon) > 0.3 else 0.02
lat_span = np.linspace(min(corner_lat) - step, max(corner_lat) + step, 200)
lon_span = np.linspace(min(corner_lon) - step, max(corner_lon) + step, 200)
for lon in np.arange(np.ceil(min(corner_lon) / step) * step, max(corner_lon), step):
    x, y = to_utm.transform(np.full_like(lat_span, lon), lat_span)
    ax.plot(x, y, color='white', linewidth=0.7, alpha=0.55, linestyle='--')
    bottom_x = np.interp(bounds.bottom + 0.01 * (bounds.top - bounds.bottom), y, x)
    ax.text(bottom_x, bounds.bottom + 0.01 * (bounds.top - bounds.bottom), f'{lon:.2f}°E', color='white',
            fontsize=13, ha='center', va='bottom', path_effects=OUTLINE)
for lat in np.arange(np.ceil(min(corner_lat) / step) * step, max(corner_lat), step):
    x, y = to_utm.transform(lon_span, np.full_like(lon_span, lat))
    ax.plot(x, y, color='white', linewidth=0.7, alpha=0.55, linestyle='--')
    left_y = np.interp(bounds.left + 0.005 * (bounds.right - bounds.left), x, y)
    ax.text(bounds.left + 0.005 * (bounds.right - bounds.left), left_y, f'{lat:.2f}°N', color='white',
            fontsize=13, ha='left', va='bottom', path_effects=OUTLINE)

if pits is not None and len(pits):
    colour = np.where(pits.category != 'pit', '#00aaff', np.where(pits.new_pit == 1, '#ff2020', '#ff00ff'))
    pits.boundary.plot(ax=ax, color=colour, linewidth=0.9)
    offset = 0.002 * (bounds.right - bounds.left)
    for (_, p), c in zip(pits.iterrows(), colour):
        x, y = to_utm.transform(p.longitude, p.latitude)
        ax.text(x + offset, y + offset, str(p.pit_id), color=c, fontsize=7, path_effects=OUTLINE)
ax.set_xlim(bounds.left, bounds.right)
ax.set_ylim(bounds.bottom, bounds.top)
ax.axis('off')
n_pits = 0 if pits is None else int((pits.category == 'pit').sum())
n_new = 0 if pits is None else int(((pits.category == 'pit') & (pits.new_pit == 1)).sum())
n_ponds = 0 if pits is None else int((pits.category != 'pit').sum())
ax.text(0.01, 0.995, f'{n_pits} pits ({n_new} new = red, {n_pits - n_new} older = magenta), {n_ponds} likely village '
        f'ponds (blue) — numbers = pit_id in pits.csv, which lists each pit\'s latitude / longitude — '
        f'Sentinel-2 10 m, {run_dir.name}', transform=ax.transAxes, color='white', fontsize=16, va='top',
        path_effects=OUTLINE)
fig.savefig(out_dir / 'pit_map_full_resolution.jpg', dpi=100, pil_kwargs={'quality': 90})
plt.close(fig)


# 3. Coordinate tables: the new pits and the largest pits.
def table_jpg(rows, title, path):
    shown = rows[['pit_id', 'latitude', 'longitude', 'area_ha', 'prob_max', 'setting']].copy()
    shown['latitude'] = shown.latitude.map('{:.6f}° N'.format)
    shown['longitude'] = shown.longitude.map('{:.6f}° E'.format)
    shown['area_ha'] = shown.area_ha.map('{:.2f}'.format)
    shown['prob_max'] = shown.prob_max.map('{:.2f}'.format)
    shown.columns = ['Pit', 'Latitude', 'Longitude', 'Area (ha)', 'Probability', 'Setting']
    fig, ax = plt.subplots(figsize=(11, 0.32 * len(shown) + 1.1))
    ax.axis('off')
    ax.set_title(title, fontsize=13, loc='left')
    table = ax.table(cellText=shown.values, colLabels=shown.columns, loc='upper center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.3)
    for (r, _), cell in table.get_celld().items():
        if r == 0:
            cell.set_facecolor('#e8e8e8')
            cell.set_text_props(weight='bold')
    fig.savefig(path, dpi=110, bbox_inches='tight', pil_kwargs={'quality': 92})
    plt.close(fig)


csv = pd.read_csv(run_dir / 'pits.csv')
real = csv[csv.category == 'pit']
new = real[real.new_pit == 1].sort_values('area_ha', ascending=False)
if len(new):
    table_jpg(new, f'New pits since this time last year ({len(new)}) — coordinates', out_dir / 'new_pits_coordinates.jpg')
table_jpg(real.sort_values('area_ha', ascending=False).head(30), 'Largest 30 pits — coordinates',
          out_dir / 'largest_pits_coordinates.jpg')

for path in sorted(out_dir.glob('*.jpg')):
    print(f'{path.name:45s} {Image.open(path).size}')
