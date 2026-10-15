#!/usr/bin/env python3
"""
Canals and drains of a Haryana district and its surroundings from the Haryana Space Applications Centre (HSAC)
public map services: the Irrigation & Water Resources Department's canal network (main canals, branches,
distributaries, minors) and drains, and the canal footprint polygons of the state's canal layer.

Writes to the output folder every canal / drain within ~5 km of the district, with its name, kind, category and the
half-width of the corridor used to remove detections that lie in a canal (lines; footprints get a small margin):
  <district>_canals.geojson     (used by the notebook)
  <district>_canals.csv         (WKT geometry, for an Earth Engine table upload: lines and polygons in one table)

usage: python get_hsac_canals.py Karnal [--out data] [--boundary data/karnal_districts.geojson]
       (the boundary file is made by get_boundaries.py)
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = 'https://hsacggm.in/server/rest/services'
LAYERS = {
    'canal': (f'{ROOT}/iwrd/assets/MapServer/4', {'canal_name': 'name', 'category': 'category',
                                                  'discharge_at_start_rd': 'discharge', 'parent_name': 'parent'}),
    'drain': (f'{ROOT}/iwrd/assets/MapServer/14', {'drain_name': 'name'}),
    'canal footprint': (f'{ROOT}/Water/Canal_Haryana/MapServer/2', {}),
}
# Half-width of the corridor in metres: water channel plus banks and a margin for mapping offsets, from the
# category and from the discharge at the head (cusecs) — whichever is wider, since categories are inconsistent
# (e.g. the 8,000-cusec Munak Canal is listed as "Canal").
HALF_WIDTH = {'main': 30, 'branch': 20, 'sub branch': 15, 'feeder': 15, 'distributary': 10, 'minor': 7,
              'sub minor': 5}
BY_DISCHARGE = [(2000, 35), (500, 25), (100, 15), (20, 10), (0, 6)]
DEFAULT_CANAL, DRAIN, FOOTPRINT_MARGIN = 10, 10, 10


def query(url, **params):
    with urllib.request.urlopen(url + '/query?' + urllib.parse.urlencode(params), timeout=300) as response:
        return json.load(response)


def half_width(kind, category, discharge):
    if kind == 'drain':
        return DRAIN
    if kind == 'canal footprint':
        return FOOTPRINT_MARGIN
    category = (category or '').lower()
    matches = [width for name, width in HALF_WIDTH.items() if name in category]   # most specific name last
    by_category = max(matches) if 'main' in category else (matches[-1] if matches else DEFAULT_CANAL)
    try:
        by_discharge = next(width for limit, width in BY_DISCHARGE if float(discharge) >= limit)
    except (TypeError, ValueError):
        by_discharge = 0
    return max(by_category, by_discharge)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('district', help='Haryana district, e.g. Karnal')
    parser.add_argument('--out', default='data')
    parser.add_argument('--boundary', help='GeoJSON with a "district" column (default data/<district>_districts.geojson)')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = args.district.lower().replace(' ', '_')

    boundary = gpd.read_file(args.boundary or out / f'{name}_districts.geojson')
    district = boundary[boundary.district.str.lower() == args.district.lower()]
    if district.empty:
        raise SystemExit(f'"{args.district}" not in the boundary file; run get_boundaries.py first.')
    utm = district.estimate_utm_crs()
    area = district.to_crs(utm).buffer(5000).union_all()
    west, south, east, north = gpd.GeoSeries([area], crs=utm).to_crs(4326).total_bounds
    envelope = dict(geometry=f'{west},{south},{east},{north}', geometryType='esriGeometryEnvelope', inSR=4326,
                    spatialRel='esriSpatialRelIntersects', outSR=4326, f='geojson')

    parts = []
    for kind, (url, fields) in LAYERS.items():
        features = []
        while True:
            page = query(url, where='1=1', outFields=','.join(fields) or 'objectid', orderByFields='objectid',
                         resultOffset=len(features), resultRecordCount=1000, **envelope)
            features += page['features']
            if len(page['features']) < 1000:
                break
        layer = gpd.GeoDataFrame.from_features(features, crs=4326).rename(columns=fields)
        for column in ('name', 'category', 'discharge', 'parent'):
            if column not in layer:
                layer[column] = None
        layer['kind'] = kind
        parts.append(layer[['kind', 'name', 'category', 'parent', 'discharge', 'geometry']])
        print(f'  {kind}: {len(layer)} features')

    canals = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), crs=4326)
    # The layers also hold rivers (the Yamuna, as "River", "Distributary" and drain); river beds are where sand is
    # mined, so they are left out.
    river = (canals.category.fillna('') == 'River') | canals.name.fillna('').str.contains(r'\briver\b', case=False)
    canals = canals[canals.geometry.notna() & ~canals.geometry.is_empty & ~river]
    canals['geometry'] = canals.geometry.make_valid()
    canals = canals[canals.to_crs(utm).intersects(area)].reset_index(drop=True)
    canals['name'] = canals.name.fillna('').str.strip()
    canals['category'] = canals.category.fillna('')
    canals['discharge'] = pd.to_numeric(canals.discharge, errors='coerce')
    canals['half_width_m'] = [half_width(k, c, q) for k, c, q in zip(canals.kind, canals.category, canals.discharge)]
    canals.to_file(out / f'{name}_canals.geojson', driver='GeoJSON', COORDINATE_PRECISION=6)
    canals.assign(geometry=canals.geometry.to_wkt(rounding_precision=6)).to_csv(out / f'{name}_canals.csv', index=False)
    length = canals[canals.kind != 'canal footprint'].to_crs(utm).length.groupby(canals.kind).sum().div(1000).round(0)
    print(f'{len(canals)} canals, drains and canal footprints within 5 km of {args.district} '
          f'(km: {length.to_dict()}; categories: {canals[canals.kind == "canal"].category.value_counts().to_dict()}); '
          f'written to {out}/{name}_canals.geojson and {name}_canals.csv')


if __name__ == '__main__':
    main()
