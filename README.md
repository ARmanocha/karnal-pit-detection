# Karnal pit detection — sand, mining and brick-kiln pits from free satellite data

Finds excavation pits — including small ones — in Karnal district, Haryana (India) using only free data:
Sentinel-2, Sentinel-1, Dynamic World, building maps and AlphaEarth AI embeddings, processed in
Google Earth Engine and at full 10 m detail in Python.

![All detected pits](results/karnal_2026-06-30_to_2026-09-30/jpg/00_pit_map_full_resolution.jpg)

## Results — Karnal district, 30 June to 30 September 2026

| | Pits | Area |
|---|---:|---:|
| Outside the Yamuna riverbed | 257 | 63 ha |
| In the Yamuna riverbed | 42 | 18 ha |
| **Total in Karnal** | **299** | **81 ha** |
| New since the same months of 2025 | 34 | |
| Removed: registered ponds (HSAC pond register) | 58 | 13 ha |
| Removed: likely village ponds (water next to a village) | 6 | 2 ha |
| Just across the district border (Panipat 5, Kurukshetra 2, Kaithal 2, Jind 1, Samli 1, Saharanpur 1) | 12 | 3 ha |

By size: 120 tiny (< 0.1 ha), 143 small (0.1–0.5 ha), 33 medium (0.5–2 ha), 3 large (> 2 ha).
2,588 km² analysed with 88 Sentinel-2 and 24 Sentinel-1 scenes. Removed ponds are listed in
[`ponds_excluded.csv`](results/karnal_2026-06-30_to_2026-09-30/ponds_excluded.csv) with the register's id and name, and are not counted above.
The analysis area is FAO's 2015 outline of Karnal, which does not match today's boundary exactly (see
Limitations), so the 12 pits found just across the border are listed with their own district and not
counted for Karnal.

### Pits by tehsil

| Tehsil | Pits | Area (ha) | New pits |
|---|---:|---:|---:|
| Karnal | 70 | 17.4 | 10 |
| Gharaunda | 51 | 16.6 | 12 |
| Indri | 49 | 20.8 | 1 |
| Nilokheri | 35 | 8.0 | 7 |
| Assandh | 34 | 8.3 | 3 |
| Ballah (sub-tehsil) | 27 | 3.4 | 0 |
| Nigdu (sub-tehsil) | 19 | 3.9 | 0 |
| Nising (sub-tehsil) | 14 | 2.3 | 1 |
| **Total** | **299** | **80.5** | **34** |

Villages with the most pits are in [`pits_by_village.csv`](results/karnal_2026-06-30_to_2026-09-30/pits_by_village.csv).

**Registered ponds are removed.** Every detection lying in a water body of the Haryana pond register
(HSAC Pond MIS, see below) is taken out of the pit list and written to `ponds_excluded.csv` with the
register's id and name, and the model is trained with registered ponds as "not pit" examples. In the
previous version of these results 331 of the 664 detected "pits" — about half — lay in registered ponds.

**Treat these as candidates to verify, not confirmed pits.** There is no ground truth yet, so the pit
threshold is the default 0.6. The gallery shows plausible pits (for example pit 4, a 1.5 ha wet, bare
patch among fields at Halwana) but also remaining false detections: pieces of a canal (pits 3 and 5),
specks at the edge of the analysis area, and edges of water bodies that are not in the register.
Labelling a few dozen examples (below) is the way to fix these.

| Gallery (10 m view · water · radar · probability) | Statistics |
|---|---|
| ![Gallery](results/karnal_2026-06-30_to_2026-09-30/jpg/05_gallery_1_most_confident.jpg) | ![Statistics](results/karnal_2026-06-30_to_2026-09-30/jpg/07_statistics.jpg) ![Pit history](results/karnal_2026-06-30_to_2026-09-30/jpg/06_pit_history_example.jpg) |

Result files in [`results/karnal_2026-06-30_to_2026-09-30/`](results/karnal_2026-06-30_to_2026-09-30/):

| File | What it is |
|---|---|
| `pits.csv` | Every pit: **latitude, longitude, district, tehsil, village**, area, probability, new or older, riverbed or not, Google Maps link |
| `ponds_excluded.csv`, `ponds_excluded.geojson` | Detections removed because they are ponds: registered ponds (with the register's `hsac_id`, name and type, and the share of the detection inside it) and likely village ponds (water next to a village) |
| `pits_by_tehsil.csv`, `pits_by_village.csv` | Number of pits, hectares and new pits per tehsil and per village |
| `pits.geojson`, `pits.gpkg` | Pit outlines for QGIS / ArcGIS, with latitude / longitude attributes |
| `pits.kml` | Google Earth: outline + numbered pin per pit, coordinates and a Google Maps link in each pin (red = new, magenta = older) |
| `pit_probability.tif` | Pit probability for every 10 m pixel (0–100) |
| `jpg/` | Numbered pit map with tehsil and village boundaries, registered ponds (light blue) and a latitude / longitude grid, coordinate tables of the new and largest pits (08, 09), pits per tehsil (10), inputs, training examples, validation, probability, 4 gallery pages (coordinates in every title), pit history, statistics |
| `karnal_pit_detection_executed.ipynb` | The notebook with all outputs from this run |

Coordinates are WGS84 decimal degrees (6 decimals ≈ 0.1 m) of each pit's centre — or of a point
inside the pit when its shape is curved — so every pin falls on its pit. The numbers on the map are
the `pit_id` column of `pits.csv`. Each pit's tehsil and village are the boundaries its location falls
in (or the nearest one); pits just across the district border get their own district's name instead.

**Boundaries** ([`data/`](data/)): Karnal's 8 tehsils / sub-tehsils (2018), 448 villages and towns
(2011 Census) and the neighbouring districts (2021) from [geoBoundaries](https://www.geoboundaries.org) —
GeoJSON for the notebook and
`karnal_boundaries_shp.zip` (shapefiles) for an Earth Engine upload. In the source, the sub-tehsils
Nigdu and Nising carry each other's names (each one's namesake town lies in the other's polygon);
[`tools/get_boundaries.py`](tools/get_boundaries.py) detects this and swaps them back.

**Registered ponds** ([`data/karnal_hsac_ponds.geojson`](data/karnal_hsac_ponds.geojson)): the pond inventory of
the Haryana Pond & Waste Water Management Authority, mapped by the Haryana Space Applications Centre
([HSAC Pond MIS](https://hsac.org.in/pond_mis/)) — 3,957 water bodies in and within ~5 km of Karnal
(3,758 ponds, 180 tanks, 11 water-logged areas, 2 lakes and 6 entries typed "Mining Pit"), read from
HSAC's public map service by [`tools/get_hsac_ponds.py`](tools/get_hsac_ponds.py), which works for any
Haryana district. The six "Mining Pit" entries are village ponds (named e.g. "Near School"), so they
are treated as ponds as well. `karnal_hsac_ponds_shp.zip` is the same layer as a shapefile for an Earth
Engine upload.

## Pit coordinates

Every pit's latitude, longitude, tehsil and village are in [`pits.csv`](results/karnal_2026-06-30_to_2026-09-30/pits.csv) (also in the
GeoJSON, GeoPackage and KML). The tables below list the new pits and the largest pits; **Map** opens the
spot in Google Maps.

| New pits — coordinates | Largest pits — coordinates |
|---|---|
| ![New pits](results/karnal_2026-06-30_to_2026-09-30/jpg/08_new_pits_coordinates.jpg) | ![Largest pits](results/karnal_2026-06-30_to_2026-09-30/jpg/09_largest_pits_coordinates.jpg) |

<details>
<summary><b>37 new pits</b> (cropland in the same months of 2025, bare or flooded now) — largest first</summary>

| Pit | Latitude | Longitude | Village | Tehsil | Area (ha) | Setting | Map |
|---:|---:|---:|---|---|---:|---|---|
| 87 | 29.552032 | 77.106018 | Khwajpur | Gharaunda | 4.79 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.552032,77.106018) |
| 82 | 29.516034 | 77.092861 | Kalri | Gharaunda | 1.95 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.516034,77.092861) |
| 75 | 29.478458 | 77.069611 | Garhi Bhalal(43) | Gharaunda | 1.21 | outside riverbed | [open](https://www.google.com/maps?q=29.478458,77.069611) |
| 32 | 29.749540 | 76.858752 | Bir Naraina (59) | Nilokheri | 1.05 | outside riverbed | [open](https://www.google.com/maps?q=29.749540,76.858752) |
| 57 | 29.860365 | 76.904257 | Raipur Roran (44) | Nilokheri | 0.96 | outside riverbed | [open](https://www.google.com/maps?q=29.860365,76.904257) |
| 31 | 29.733920 | 77.090221 | Mohamadpur (76) | Karnal | 0.68 | outside riverbed | [open](https://www.google.com/maps?q=29.733920,77.090221) |
| 192 | 29.810776 | 77.003219 | Smora(55) | Indri | 0.67 | outside riverbed | [open](https://www.google.com/maps?q=29.810776,77.003219) |
| 27 | 29.669008 | 76.695528 | Ichhanpur (40) | Assandh | 0.57 | outside riverbed | [open](https://www.google.com/maps?q=29.669008,76.695528) |
| 172 | 29.620743 | 76.742969 | Dachaur (62) | Nising ST | 0.56 | outside riverbed | [open](https://www.google.com/maps?q=29.620743,76.742969) |
| 77 | 29.476167 | 76.895833 |  | (Panipat district) | 0.45 | outside riverbed | [open](https://www.google.com/maps?q=29.476167,76.895833) |
| 79 | 29.475289 | 76.895936 |  | (Panipat district) | 0.45 | outside riverbed | [open](https://www.google.com/maps?q=29.475289,76.895936) |
| 22 | 29.744409 | 76.851842 | Bahlolpur Mushtarka (19) | Karnal | 0.44 | outside riverbed | [open](https://www.google.com/maps?q=29.744409,76.851842) |
| 118 | 29.628652 | 76.581730 |  | (Kaithal district) | 0.35 | outside riverbed | [open](https://www.google.com/maps?q=29.628652,76.581730) |
| 34 | 29.729562 | 77.128471 | Nabipur (78) | Karnal | 0.30 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.729562,77.128471) |
| 145 | 29.745877 | 76.857142 | Saga (58) | Nilokheri | 0.22 | outside riverbed | [open](https://www.google.com/maps?q=29.745877,76.857142) |
| 112 | 29.523390 | 76.667479 | Phaphrana (94) | Assandh | 0.19 | outside riverbed | [open](https://www.google.com/maps?q=29.523390,76.667479) |
| 35 | 29.747869 | 77.085852 | Baragaon (69) | Karnal | 0.18 | outside riverbed | [open](https://www.google.com/maps?q=29.747869,77.085852) |
| 150 | 29.591390 | 77.076752 | Lalupura (109) | Gharaunda | 0.18 | outside riverbed | [open](https://www.google.com/maps?q=29.591390,77.076752) |
| 95 | 29.533566 | 76.578321 | Assandh (Rural)(Part)(84) | Assandh | 0.18 | outside riverbed | [open](https://www.google.com/maps?q=29.533566,76.578321) |
| 12 | 29.656811 | 77.121983 | Dhakwala (121) | Karnal | 0.16 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.656811,77.121983) |
| 76 | 29.475692 | 77.073346 | Garhi Bhalal(43) | Gharaunda | 0.15 | outside riverbed | [open](https://www.google.com/maps?q=29.475692,77.073346) |
| 193 | 29.576161 | 76.947129 | Upli (9) | Gharaunda | 0.15 | outside riverbed | [open](https://www.google.com/maps?q=29.576161,76.947129) |
| 30 | 29.747593 | 76.859317 | Bir Naraina (59) | Nilokheri | 0.15 | outside riverbed | [open](https://www.google.com/maps?q=29.747593,76.859317) |
| 161 | 29.734247 | 77.089026 | Mohamadpur (76) | Karnal | 0.14 | outside riverbed | [open](https://www.google.com/maps?q=29.734247,77.089026) |
| 106 | 29.577910 | 76.962067 | Gharaunda (Rural)(Part) (27) | Gharaunda | 0.12 | outside riverbed | [open](https://www.google.com/maps?q=29.577910,76.962067) |
| 245 | 29.591788 | 77.077265 | Lalupura (109) | Gharaunda | 0.11 | outside riverbed | [open](https://www.google.com/maps?q=29.591788,77.077265) |
| 97 | 29.558369 | 77.017431 | Arainpura (12) | Gharaunda | 0.11 | outside riverbed | [open](https://www.google.com/maps?q=29.558369,77.017431) |
| 156 | 29.569381 | 77.003800 | Gianpura (11) | Gharaunda | 0.08 | outside riverbed | [open](https://www.google.com/maps?q=29.569381,77.003800) |
| 24 | 29.581300 | 77.095913 | Khwajpur | Gharaunda | 0.08 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.581300,77.095913) |
| 163 | 29.751118 | 76.846043 | Saga (58) | Nilokheri | 0.06 | outside riverbed | [open](https://www.google.com/maps?q=29.751118,76.846043) |
| 183 | 29.711122 | 77.132891 | Kunda Kalan (114) | Karnal | 0.06 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.711122,77.132891) |
| 221 | 29.487535 | 77.030090 | Pundri (40) | Gharaunda | 0.05 | outside riverbed | [open](https://www.google.com/maps?q=29.487535,77.030090) |
| 263 | 29.734233 | 77.089540 | Mohamadpur (76) | Karnal | 0.05 | outside riverbed | [open](https://www.google.com/maps?q=29.734233,77.089540) |
| 267 | 29.751160 | 76.845610 | Saga (58) | Nilokheri | 0.05 | outside riverbed | [open](https://www.google.com/maps?q=29.751160,76.845610) |
| 167 | 29.870309 | 76.956853 | Kalsi (69) | Nilokheri | 0.04 | outside riverbed | [open](https://www.google.com/maps?q=29.870309,76.956853) |
| 37 | 29.720678 | 77.132387 | Kunda Kalan (114) | Karnal | 0.03 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.720678,77.132387) |
| 195 | 29.686111 | 76.870618 | Mandhai (41) | Karnal | 0.03 | outside riverbed | [open](https://www.google.com/maps?q=29.686111,76.870618) |

</details>

<details>
<summary><b>15 largest pits</b></summary>

| Pit | Latitude | Longitude | Village | Tehsil | Area (ha) | Setting | Map |
|---:|---:|---:|---|---|---:|---|---|
| 87 | 29.552032 | 77.106018 | Khwajpur | Gharaunda | 4.79 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.552032,77.106018) |
| 61 | 29.885663 | 77.069563 | Khera (23) | Indri | 4.37 | outside riverbed | [open](https://www.google.com/maps?q=29.885663,77.069563) |
| 62 | 29.887393 | 77.051478 | Badheri (2) | Indri | 4.32 | outside riverbed | [open](https://www.google.com/maps?q=29.887393,77.051478) |
| 82 | 29.516034 | 77.092861 | Kalri | Gharaunda | 1.95 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.516034,77.092861) |
| 78 | 29.479661 | 76.529160 | Ardana (64) | Assandh | 1.77 | outside riverbed | [open](https://www.google.com/maps?q=29.479661,76.529160) |
| 54 | 29.682128 | 76.956603 | Karnal (Rural)(Part)(1) | Karnal | 1.63 | outside riverbed | [open](https://www.google.com/maps?q=29.682128,76.956603) |
| 41 | 29.706463 | 77.132010 | Chusana (115) | Karnal | 1.60 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.706463,77.132010) |
| 4 | 29.823660 | 77.139928 | Halwana (105) | Indri | 1.48 | outside riverbed | [open](https://www.google.com/maps?q=29.823660,77.139928) |
| 50 | 29.700295 | 77.136592 | Bhari (85) | Karnal | 1.47 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.700295,77.136592) |
| 131 | 29.890501 | 77.180958 | Chandraon (10) | Indri | 1.35 | outside riverbed | [open](https://www.google.com/maps?q=29.890501,77.180958) |
| 89 | 29.528667 | 76.617388 | Assandh (Rural)(Part)(84) | Assandh | 1.32 | outside riverbed | [open](https://www.google.com/maps?q=29.528667,76.617388) |
| 72 | 29.894305 | 76.955535 | Bairsal (27) | Nilokheri | 1.25 | outside riverbed | [open](https://www.google.com/maps?q=29.894305,76.955535) |
| 75 | 29.478458 | 77.069611 | Garhi Bhalal(43) | Gharaunda | 1.21 | outside riverbed | [open](https://www.google.com/maps?q=29.478458,77.069611) |
| 91 | 29.557121 | 77.104161 | Khwajpur | Gharaunda | 1.21 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.557121,77.104161) |
| 32 | 29.749540 | 76.858752 | Bir Naraina (59) | Nilokheri | 1.05 | outside riverbed | [open](https://www.google.com/maps?q=29.749540,76.858752) |

</details>

## Repository

| Path | What it is |
|---|---|
| [`notebooks/karnal_pit_detection.ipynb`](notebooks/karnal_pit_detection.ipynb) | Main workflow: Earth Engine features → download → features, training, pit outlines, gallery, maps, pit history, statistics, exports |
| [`gee/mine_pit_detection.js`](gee/mine_pit_detection.js) | The same idea entirely in the Earth Engine Code Editor (no download), with click-to-label layers — see [Use it in Google Earth Engine only](#use-it-in-google-earth-engine-only-no-python) |
| [`data/`](data/) | Tehsil, village and neighbouring-district boundaries and the registered ponds of Karnal (GeoJSON + shapefile zips) |
| [`tools/get_boundaries.py`](tools/get_boundaries.py) | Makes the tehsil and village boundary files for any Indian district: `python tools/get_boundaries.py Panipat` |
| [`tools/get_hsac_ponds.py`](tools/get_hsac_ponds.py) | Downloads the registered ponds (HSAC pond inventory) of any Haryana district: `python tools/get_hsac_ponds.py Panipat` |
| [`tools/pit_verify.py`](tools/pit_verify.py) | Optional stage 2 for high-resolution imagery: confirm / outline candidates with a YOLOv8 detector |
| [`tools/export_jpgs.py`](tools/export_jpgs.py) | Saves every figure of an executed notebook as JPG, plus a numbered full-resolution pit map with tehsil / village boundaries and a latitude / longitude grid, coordinate tables and a pits-per-tehsil table |

## How it works

1. **Earth Engine** builds features for the analysis window and the same months a year earlier:
   cloud-free Sentinel-2 statistics (10 m vegetation / water / bare-soil indices), Sentinel-1 radar,
   Dynamic World land-cover shares, four building sources that "vote" (Open Buildings, WorldCover,
   Dynamic World, radar double bounce), the Yamuna riverbed zone, and AlphaEarth similarity to typical
   pits / buildings / water / crops.
2. The features are **downloaded** as one GeoTIFF (resumable, with timeouts).
3. **Locally at 10 m**: context features (each pixel vs. its 130 m surroundings), sub-pixel
   water / bare / vegetation / building fractions, automatic training examples (registered ponds as
   "not pit" examples) plus your own points, a gradient-boosting model validated on 5 km blocks it
   never trained on.
4. **Pit objects**: hysteresis outlines; building pixels removed; tiny pits kept only when very
   confident; canals, drains, roads and thin lines dropped; registered ponds and likely village ponds
   removed to `ponds_excluded.csv`; riverbed pits tagged.
5. Optional **2.5 m super-resolution** (SEN2SR) for close-ups and refined outlines.

## Run it

1. Open `notebooks/karnal_pit_detection.ipynb` in Jupyter or Google Colab.
2. In **Settings**, set `PROJECT_ID` to the Google Cloud project you use with Earth Engine.
   Keep `AREA = 'test'` for a quick first run (14 × 13 km along the Yamuna, a few minutes),
   then use `AREA = 'district'` (≈ 2.5 GB download, roughly 10–30 minutes).
3. Run all cells.

**Improve the results:** in section 3, zoom the Satellite basemap to 16–18 and save 30–50 points on
real pits and 30–50 on false detections (canals, fish ponds, roads, roofs). Re-run from section 6 —
no new download. The validation table then shows real accuracy against your points and the
threshold is tuned on them.

Optional super-resolution: `pip install sen2sr mlstac torch`, then re-run from section 10.

## Use it in Google Earth Engine only (no Python)

[`gee/mine_pit_detection.js`](gee/mine_pit_detection.js) does the detection entirely in the
[Earth Engine Code Editor](https://code.earthengine.google.com) — nothing to install or download.
You only need an Earth Engine account with a Cloud project (free for non-commercial use:
[register here](https://code.earthengine.google.com/register)).

**1. Open the script**

1. Go to [code.earthengine.google.com](https://code.earthengine.google.com) and pick your Cloud project
   (top-right, next to your profile picture).
2. **Scripts** panel (left) → **NEW** → **File**, name it e.g. `karnal_pits`.
3. Paste the whole of `gee/mine_pit_detection.js` into the editor and press **Save**.

**2. Choose the area and dates** in the `CONFIG` block at the top of the script:

| Setting | Default | Change it to… |
|---|---|---|
| `state`, `districts` | `'Haryana'`, `[['Karnal']]` | another district, e.g. `[['Sonipat', 'Sonepat']]` (alternative spellings), or several: `[['Karnal'], ['Panipat']]` |
| `endDate` | `null` (today) | a fixed date such as `'2026-09-30'`, so later runs use the same period |
| `monthsBack` | `3` | the length of the window; it is always compared with the same months a year earlier |
| `probabilityThreshold` | `0.6` | lower (e.g. `0.4`) to catch more pits with more false alarms, higher for fewer |
| `minPitAreaHa` | `0.05` | the smallest pit kept (0.05 ha = 5 Sentinel-2 pixels) |

To use your own area instead of a district, draw a polygon with the geometry tools and name the
import `aoi`.

**3. Run** — press **Run** and wait 1–3 minutes until the panel (bottom-left) says *Model ready*.

- **Map** (Layers menu, top-right of the map): *Pit pixels* (magenta), *New pits since this time last
  year* (red), *Removed: looks like a building* (grey) and *District boundaries* are on; *Pit probability*,
  *Model unsure*, Sentinel-2, radar, Dynamic World, building and riverbed layers can be switched on.
  Zoom to level 13+ to see small pits.
- **Console** (right): the period, Sentinel scene counts, training samples, a validation table per
  threshold, and the features the model relies on most.
- **Panel**: **Outline + count pits in current view** (zoom 13+) draws the outlines and counts pits —
  total, new, under 0.5 ha, hectares. Tick **Click map to find pits similar to the clicked one** and
  click any pit to highlight everything that looks like it (AlphaEarth similarity).

**4. Download every pit with its latitude and longitude** — open the **Tasks** tab (top-right) and
press **RUN** on:

| Task | Saved to Google Drive folder `GEE_pits` |
|---|---|
| `karnal_pits_list_<dates>` | CSV: district, tehsil, village, **latitude, longitude**, area_ha, prob, new_pit, water_frac, built_frac, compact, `maps_link` (Google Maps) |
| `karnal_pits_polygons_<dates>` | Shapefile of the pit outlines with the same attributes (change `fileFormat` to `'KML'` for Google Earth) |
| `karnal_pit_probability_<dates>` | GeoTIFF of the pit probability (0–100) for every 10 m pixel |
| `karnal_ponds_excluded_<dates>` | Only with `pondAsset` (below): CSV of the detections removed as registered ponds, with the register's `hsac_id`, name and type |

**Optional — tehsil and village boundaries in Earth Engine.** Earth Engine has no tehsil or village
layer for India, so upload the repository's ones once:

1. Unzip [`data/karnal_boundaries_shp.zip`](data/karnal_boundaries_shp.zip).
2. **Assets** tab (top-left) → **NEW** → **Shape files** → select the five `karnal_tehsils.*` files
   (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`) → name the asset `karnal_tehsils` → **UPLOAD**. Do the same
   for the five `karnal_villages.*` files as `karnal_villages`. The upload runs in the Tasks tab.
3. In `CONFIG`, set `tehsilAsset: 'projects/<your-project>/assets/karnal_tehsils'` and
   `villageAsset: 'projects/<your-project>/assets/karnal_villages'`, then **Run**.

The map then shows *Tehsil boundaries* (orange) and *Village boundaries* (white, in the Layers menu), the
panel counts pits per tehsil, and the exported CSV and shapefile fill the `tehsil` and `village` columns.
For another district, make its files first with `python tools/get_boundaries.py <District>`.

**Optional — remove registered ponds in Earth Engine.** Upload
[`data/karnal_hsac_ponds_shp.zip`](data/karnal_hsac_ponds_shp.zip) the same way (unzip, **NEW** →
**Shape files**, the five `karnal_hsac_ponds.*` files, asset name `karnal_hsac_ponds`) and set
`pondAsset: 'projects/<your-project>/assets/karnal_hsac_ponds'`. Registered ponds then become "not pit"
training examples, detections with at least `pondMatch` (25 %) of their area in a registered pond (widened
by `pondTolerance`, 15 m) leave the pit list and the counts, the *Registered ponds (HSAC)* layer is added,
and the Tasks tab gets a `ponds_excluded` export. For another Haryana district run
`python tools/get_hsac_ponds.py <District>` first.

**5. Improve it by labelling** — after the first run the drawing tools (top-left of the map) contain
two point layers, `pits` (red) and `nonPits` (blue). Zoom the Satellite basemap to 16–18, start where
the *Model unsure* layer is, select a layer and click to add points — real pits as `pits`, false
detections (roofs, canals, fish ponds, roads, brick kilns, sand bars) as `nonPits`. 30–50 of each is a
good start. Press **Run** again: the Console now shows a table *Against YOUR points (real accuracy)* —
set `probabilityThreshold` to the row with the best balance. The points are saved with the script, so
keep adding where it is still wrong. With ~100+ of each, `useAutoLabels: false` learns from your
points only.

**If you get "Computation timed out"**: halve `trainingCells` and `riverCells`, or run the
`cache_training_samples_v3_<dates>` task in the Tasks tab, put its asset ID in `samplesAsset`, set
`endDate` to the printed end date and run again — training then takes seconds.

**GEE-only vs the notebook:** the Code Editor script uses the same data, building knowledge,
automatic labels, context features and block validation, with a Random Forest. The notebook adds
gradient boosting at full 10 m, sub-pixel fractions, removal of canal / drain / road fragments and thin
lines, village-pond and riverbed tags, the gallery, pit histories and JPGs — so its counts are cleaner.
The results in this repository come from the notebook.

## Limitations

- Sentinel-2 pixels are 10 m: about 3 pixels (≈ 0.03 ha, e.g. 15 × 20 m) is the smallest pit
  detected reliably.
- Without your labels the model learns from rules, so accuracy is unknown.
- Riverbed detections can be sand mining but also natural sand bars, flood pools or bank erosion.
- AlphaEarth embeddings are annual (2025 for this run); recent change comes from Sentinel-2,
  Sentinel-1 and Dynamic World.
- Super-resolved images are an AI estimate, useful for viewing — not real high-resolution imagery.
- The analysis area is FAO's 2015 outline of Karnal. Compared with today's boundary it misses about
  106 km² (4 %) of Karnal — mostly along the Yamuna on the east edge, the largest piece 35 km² east of
  Indri — and includes 202 km² of neighbouring districts (pits there are listed with their own district).
- Only ponds in the HSAC register are removed by name; unregistered ponds and fish ponds can remain.
  Training on registered ponds also teaches the model what a pond looks like, which removes many
  unregistered ponds — but a water-filled pit looks the same at 10 m. Compared with training without
  them, about 120 small water bodies outside the register were dropped (13 of them in the Yamuna
  riverbed). To only remove registered ponds, set `SAMPLES['registered_pond'] = 0` in the notebook
  (`pondSamples: 0` in the Earth Engine script).
- Tehsil boundaries are from 2018 and village boundaries from the 2011 Census; their edges do not match
  exactly, and newer administrative changes are not included. Pits right at a boundary may be assigned
  to the neighbouring unit.

## Data and credits

Copernicus Sentinel-1 and Sentinel-2; Cloud Score+; Google Dynamic World; Google DeepMind AlphaEarth
Foundations satellite embeddings; Google Open Buildings 2.5D Temporal; ESA WorldCover; WWF HydroSHEDS
Free-Flowing Rivers; FAO GAUL 2015 boundaries — all via Google Earth Engine. Tehsil (2018) and village
(2011 Census) boundaries: [geoBoundaries](https://www.geoboundaries.org) gbOpen India ADM3 / ADM5
(source: Pathways Data, Local Government Directory and Census of India), Open Data Commons ODbL 1.0. Registered
ponds: Haryana Pond & Waste Water Management Authority / Haryana Space Applications Centre (HSAC) pond
inventory, [Pond MIS](https://hsac.org.in/pond_mis/), from HSAC's public map service. Optional SEN2SR
super-resolution by ESA OpenSR. The detection ideas (context, shape, block validation, local labels)
were informed by [BapakmuLah/Satellit-Based-Open-Pit-Mining-Detection](https://github.com/BapakmuLah/Satellit-Based-Open-Pit-Mining-Detection).
