#!/usr/bin/env python3
"""
Tehsil (sub-district) and village boundaries for one Indian district, from geoBoundaries (gbOpen, ODbL 1.0):
  sub-districts / tehsils: 2018, Local Government Directory (lgdirectory.gov.in) via Pathways Data
  villages and towns:      2011 Census of India via Pathways Data

Writes to the output folder:
  <district>_tehsils.geojson, <district>_villages.geojson   (used by the notebook)
  <district>_districts.geojson                               (the district and its neighbours, 2021)
  <district>_boundaries_shp.zip                              (shapefiles for an Earth Engine table upload)

usage: python get_boundaries.py Karnal [--out data] [--cache ~/.cache/geoboundaries]

The India-wide source files are downloaded once to the cache folder (district 48 MB, sub-districts 106 MB,
villages 1.1 GB) and reused for any district.
"""
import argparse
import re
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd

RELEASE = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND'


def source(level, cache):
    path = cache / f'geoBoundaries-IND-{level}.geojson'
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        print(f'Downloading India {level} boundaries to {path} (once) ...')
        urllib.request.urlretrieve(f'{RELEASE}/{level}/geoBoundaries-IND-{level}.geojson', path)
    return path


def key(name):
    """'Nissing (MC)' -> 'nising', 'Nigdu ST' -> 'nigdu': letters only, repeated letters collapsed, no suffixes."""
    name = re.sub(r'\(.*?\)|\bST\b|\bMC\b', ' ', name).lower()
    return re.sub(r'(.)\1+', r'\1', re.sub(r'[^a-z]', '', name))


def fix_swapped_names(tehsils, villages):
    """Swap tehsil labels where each tehsil's namesake town lies in the other's polygon (seen in the source)."""
    home = {}
    for t in tehsils.itertuples():
        prefix = key(t.tehsil)[:4]
        towns = villages[villages.village.map(lambda v: key(v).startswith(prefix))]
        found = [u.tehsil for p in towns.representative_point() for u in tehsils.itertuples() if u.geometry.contains(p)]
        if found:
            home[t.tehsil] = max(set(found), key=found.count)
    for a, b in list(home.items()):
        if a < b and home.get(b) == a:
            print(f'Note: "{a}" and "{b}" are labelled the other way round in the source '
                  f'(each one\'s namesake town lies in the other); swapping the labels.')
            tehsils['tehsil'] = tehsils.tehsil.replace({a: b, b: a})
    return tehsils


def inside(gdf, area):
    """Units whose interior point lies in the district (neighbouring units only touch its edge)."""
    return gdf[gdf.representative_point().within(area)].copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('district', help='district name as in geoBoundaries, e.g. Karnal')
    parser.add_argument('--out', default='data')
    parser.add_argument('--cache', default=str(Path.home() / '.cache' / 'geoboundaries'))
    args = parser.parse_args()
    cache, out = Path(args.cache).expanduser(), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = args.district.lower().replace(' ', '_')

    districts = gpd.read_file(source('ADM2', cache))
    match = districts[districts.shapeName.str.lower() == args.district.lower()]
    if match.empty:
        raise SystemExit(f'"{args.district}" not found. Similar names: '
                         f'{sorted(n for n in districts.shapeName if n.lower()[:3] == args.district.lower()[:3])}')
    area = match.union_all()
    bbox = tuple(match.total_bounds + [-0.05, -0.05, 0.05, 0.05])

    tehsils = inside(gpd.read_file(source('ADM3', cache), bbox=bbox), area)
    tehsils = tehsils.rename(columns={'shapeName': 'tehsil', 'shapeID': 'tehsil_id'})[['tehsil', 'tehsil_id', 'geometry']]
    tehsils['area_km2'] = (tehsils.to_crs(tehsils.estimate_utm_crs()).area / 1e6).round(1)

    villages = inside(gpd.read_file(source('ADM5', cache), bbox=bbox), area)
    villages = villages.rename(columns={'shapeName': 'village', 'shapeID': 'village_id'})[['village', 'village_id', 'geometry']]
    tehsils = fix_swapped_names(tehsils, villages)
    # Each village belongs to the tehsil it overlaps most (the two layers come from different years and
    # their edges do not match exactly); villages that touch no tehsil take the nearest one.
    utm = villages.estimate_utm_crs()
    overlap = gpd.overlay(villages[['village_id', 'geometry']].to_crs(utm),
                          tehsils[['tehsil', 'geometry']].to_crs(utm), how='intersection')
    overlap['shared'] = overlap.area
    best = overlap.sort_values('shared').drop_duplicates('village_id', keep='last').set_index('village_id').tehsil
    villages['tehsil'] = villages.village_id.map(best)
    missing = villages.tehsil.isna()
    if missing.any():
        nearest = gpd.sjoin_nearest(villages[missing].to_crs(utm), tehsils[['tehsil', 'geometry']].to_crs(utm),
                                    how='left', rsuffix='near')
        villages.loc[missing, 'tehsil'] = nearest.groupby(level=0).tehsil_near.first()
    villages['area_km2'] = (villages.to_crs(utm).area / 1e6).round(2)

    # The district and its neighbours: pits just across the border get the right district name.
    nearby = districts[districts.intersects(match.to_crs(match.estimate_utm_crs()).buffer(5000)
                                            .to_crs(districts.crs).union_all())]
    nearby = nearby.rename(columns={'shapeName': 'district', 'shapeID': 'district_id'})[['district', 'district_id',
                                                                                         'geometry']]
    nearby.to_file(out / f'{name}_districts.geojson', driver='GeoJSON')
    tehsils.to_file(out / f'{name}_tehsils.geojson', driver='GeoJSON')
    villages.to_file(out / f'{name}_villages.geojson', driver='GeoJSON')
    shp_dir = out / f'_{name}_shp'
    shp_dir.mkdir(exist_ok=True)
    tehsils.to_file(shp_dir / f'{name}_tehsils.shp')
    villages.to_file(shp_dir / f'{name}_villages.shp')
    with zipfile.ZipFile(out / f'{name}_boundaries_shp.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(shp_dir.iterdir()):
            zf.write(path, path.name)
            path.unlink()
    shp_dir.rmdir()

    print(f'{len(tehsils)} tehsils: {", ".join(tehsils.tehsil)}')
    print(f'{len(villages)} villages and towns; neighbouring districts: '
          f'{", ".join(d for d in nearby.district if d.lower() != args.district.lower())}; written to {out}/')


if __name__ == '__main__':
    main()
