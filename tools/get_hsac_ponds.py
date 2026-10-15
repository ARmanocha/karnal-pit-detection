#!/usr/bin/env python3
"""
Registered ponds of a Haryana district and its surroundings from the Haryana Space Applications Centre (HSAC)
pond inventory (Haryana Pond & Waste Water Management Authority, https://hsac.org.in/pond_mis/), read from
HSAC's public map service "Ponds/Waterbodies Haryana".

Writes to the output folder every registered pond / tank / lake / water-logged area / mining pit within ~5 km
of the district (so pits just across the border are checked too), with its id, name, type (pond_type),
category, condition, area and administrative names (hsac_id = the register's OBJECTID; its uid field is often
empty). The register's few "Mining Pit" entries are kept with that type; in Karnal they are village ponds:
  <district>_hsac_ponds.geojson     (used by the notebook)
  <district>_hsac_ponds_shp.zip     (shapefile for an Earth Engine table upload)

usage: python get_hsac_ponds.py Karnal [--out data]
"""
import argparse
import json
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd

SERVICE = 'https://hsacggm.in/server/rest/services/Water/Waterbody/MapServer/0/query'
KEEP = ['OBJECTID', 'uid', 'district', 'tehsil', 'block', 'village', 'pond_name', 'type', 'category', 'pond_categ',
        'pond_condi', 'area_acre', 'latitude', 'longitude']


def query(**params):
    with urllib.request.urlopen(SERVICE + '?' + urllib.parse.urlencode(params), timeout=300) as response:
        return json.load(response)


def write_shapefile_zip(ponds, out, name):
    shp_dir = out / f'_{name}_hsac_ponds_shp'
    shp_dir.mkdir(exist_ok=True)
    ponds.to_file(shp_dir / f'{name}_hsac_ponds.shp')
    with zipfile.ZipFile(out / f'{name}_hsac_ponds_shp.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(shp_dir.iterdir()):
            zf.write(path, path.name)
            path.unlink()
    shp_dir.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('district', help='Haryana district, e.g. Karnal')
    parser.add_argument('--out', default='data')
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Extent of the district's own ponds, widened by ~5 km.
    where = f"upper(district)='{args.district.upper()}'"
    extent = query(where=where, returnExtentOnly='true', outSR=4326, f='json')['extent']
    if not extent or extent.get('xmin') is None:
        raise SystemExit(f'No ponds found for district "{args.district}".')
    pad = 0.05
    envelope = f"{extent['xmin'] - pad},{extent['ymin'] - pad},{extent['xmax'] + pad},{extent['ymax'] + pad}"
    area = dict(geometry=envelope, geometryType='esriGeometryEnvelope', inSR=4326,
                spatialRel='esriSpatialRelIntersects')

    total = query(where='1=1', returnCountOnly='true', f='json', **area)['count']
    features = []
    while len(features) < total:
        page = query(where='1=1', outFields=','.join(KEEP), outSR=4326, f='geojson', orderByFields='OBJECTID',
                     resultOffset=len(features), resultRecordCount=2000, **area)
        if not page['features']:
            break
        features += page['features']
        print(f'  {len(features)} / {total}')

    ponds = gpd.GeoDataFrame.from_features(features, crs=4326)[KEEP + ['geometry']]
    ponds = ponds.rename(columns={'OBJECTID': 'hsac_id', 'type': 'pond_type'})   # 'type' clashes with GeoDataFrame.type
    ponds['geometry'] = ponds.geometry.make_valid()
    name = args.district.lower().replace(' ', '_')
    ponds.to_file(out / f'{name}_hsac_ponds.geojson', driver='GeoJSON', COORDINATE_PRECISION=6)
    write_shapefile_zip(ponds, out, name)
    print(f'{len(ponds)} registered water bodies ({ponds.pond_type.value_counts().to_dict()}), '
          f'{(ponds.district.str.lower() == args.district.lower()).sum()} of them in {args.district}; '
          f'written to {out}/{name}_hsac_ponds.geojson and {name}_hsac_ponds_shp.zip')


if __name__ == '__main__':
    main()
