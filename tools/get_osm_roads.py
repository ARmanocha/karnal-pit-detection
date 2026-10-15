#!/usr/bin/env python3
"""
Roads and highways of a district and its surroundings from OpenStreetMap (ODbL 1.0), via the Overpass API.

Writes to the output folder every road within ~5 km of the district (so pits just across the border are checked
too), including roads under construction (e.g. new expressways), with its class, name, number (ref) and the
half-width of the road corridor used to remove detections that lie on a road:
  <district>_roads.geojson     (used by the notebook)
  <district>_roads_shp.zip     (shapefile for an Earth Engine table upload)

Farm tracks and paths are not included: they run along field edges and into pits, so they would remove real pits.

usage: python get_osm_roads.py Karnal [--out data] [--boundary data/karnal_districts.geojson]
       (the boundary file is made by get_boundaries.py)
"""
import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
            'https://overpass.private.coffee/api/interpreter']
# Half-width of the road corridor in metres, by OSM class: the carriageway plus shoulders and a margin for
# mapping offsets. National highways in Haryana are 4-8 lanes with service roads.
HALF_WIDTH = {'motorway': 30, 'trunk': 25, 'primary': 15, 'secondary': 12, 'tertiary': 10,
              'unclassified': 7, 'residential': 6,
              'motorway_link': 12, 'trunk_link': 12, 'primary_link': 10, 'secondary_link': 8, 'tertiary_link': 8}
UNDER_CONSTRUCTION = 25        # a road being built without a class, e.g. an expressway corridor
KEEP = ['osm_id', 'road_class', 'construction', 'name', 'ref', 'lanes', 'half_width_m']


def overpass(query):
    """Runs the query on the public Overpass servers in turn (they are often busy)."""
    data = urllib.parse.urlencode({'data': query}).encode()
    for attempt in range(2):
        for server in OVERPASS:
            request = urllib.request.Request(server, data=data, headers={'User-Agent': 'karnal-pit-detection'})
            try:
                with urllib.request.urlopen(request, timeout=600) as response:
                    return json.load(response)
            except (urllib.error.URLError, TimeoutError) as error:
                print(f'  {server}: {error}; trying the next server')
        time.sleep(30)
    raise SystemExit('All Overpass servers failed; try again later.')


def write_shapefile_zip(roads, out, name):
    shp_dir = out / f'_{name}_roads_shp'
    shp_dir.mkdir(exist_ok=True)
    # Shapefile field names are limited to 10 characters.
    roads.rename(columns={'construction': 'construct', 'half_width_m': 'half_width'}).to_file(shp_dir / f'{name}_roads.shp')
    with zipfile.ZipFile(out / f'{name}_roads_shp.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(shp_dir.iterdir()):
            zf.write(path, path.name)
            path.unlink()
    shp_dir.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('district', help='district name, e.g. Karnal')
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

    classes = '|'.join(HALF_WIDTH) + '|construction'
    result = overpass(f'[out:json][timeout:600];way["highway"~"^({classes})$"]'
                      f'({south},{west},{north},{east});out tags geom;')
    rows = []
    for way in result['elements']:
        tags = way.get('tags', {})
        if len(way.get('geometry', [])) < 2:
            continue
        road_class = tags['highway']
        building = tags.get('construction', '') if road_class == 'construction' else ''
        if road_class == 'construction' and building not in HALF_WIDTH:
            if building in ('track', 'path', 'footway', 'service', 'living_street', 'pedestrian'):
                continue
            half_width = UNDER_CONSTRUCTION
        else:
            half_width = HALF_WIDTH[building or road_class]
        rows.append({'osm_id': way['id'], 'road_class': road_class, 'construction': building,
                     'name': tags.get('name', tags.get('name:en', '')), 'ref': tags.get('ref', ''),
                     'lanes': tags.get('lanes', ''), 'half_width_m': half_width,
                     'geometry': LineString([(p['lon'], p['lat']) for p in way['geometry']])})
    roads = gpd.GeoDataFrame(rows, crs=4326)
    roads = roads[roads.to_crs(utm).intersects(area)][KEEP + ['geometry']]
    roads.to_file(out / f'{name}_roads.geojson', driver='GeoJSON', COORDINATE_PRECISION=6)
    write_shapefile_zip(roads, out, name)
    length = roads.to_crs(utm).length.groupby(roads.road_class).sum().div(1000).round(0).sort_values(ascending=False)
    print(f'{len(roads)} road segments within 5 km of {args.district} (km by class: {length.to_dict()}); '
          f'written to {out}/{name}_roads.geojson and {name}_roads_shp.zip')


if __name__ == '__main__':
    main()
