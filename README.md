# Karnal pit detection — sand, mining and brick-kiln pits from free satellite data

Finds excavation pits — including small ones — in Karnal district, Haryana (India) using only free data:
Sentinel-2, Sentinel-1, Dynamic World, building maps and AlphaEarth AI embeddings, processed in
Google Earth Engine and at full 10 m detail in Python.

![All detected pits](results/karnal_2026-06-30_to_2026-09-30/jpg/00_pit_map_full_resolution.jpg)

## Results — Karnal district, 30 June to 30 September 2026

| | Pits | Area |
|---|---:|---:|
| Outside the Yamuna riverbed | 584 | 196 ha |
| In the Yamuna riverbed | 44 | 17 ha |
| **Total in Karnal** | **628** | **213 ha** |
| New since the same months of 2025 | 35 | |
| Likely village ponds (listed separately, not counted above) | 53 | 17 ha |
| Just across the district border (Kurukshetra 13, Kaithal 9, Panipat 8, Jind 3, Samli 2, Saharanpur 1) | 36 | 19 ha |

By size: 157 tiny (< 0.1 ha), 353 small (0.1–0.5 ha), 109 medium (0.5–2 ha), 9 large (> 2 ha).
2,588 km² analysed with 88 Sentinel-2 and 24 Sentinel-1 scenes. The analysis area is FAO's 2015 outline of
Karnal, which does not match today's boundary exactly (see Limitations), so the 36 pits found just across
the border are listed with their own district and not counted for Karnal.

### Pits by tehsil

| Tehsil | Pits | Area (ha) | New pits |
|---|---:|---:|---:|
| Karnal | 144 | 46.4 | 10 |
| Assandh | 91 | 36.3 | 6 |
| Indri | 85 | 26.9 | 1 |
| Gharaunda | 84 | 25.0 | 12 |
| Nilokheri | 74 | 30.2 | 4 |
| Nigdu (sub-tehsil) | 64 | 18.1 | 0 |
| Ballah (sub-tehsil) | 55 | 21.4 | 1 |
| Nising (sub-tehsil) | 31 | 9.0 | 1 |
| **Total** | **628** | **213.3** | **35** |

Villages with the most pits are in [`pits_by_village.csv`](results/karnal_2026-06-30_to_2026-09-30/pits_by_village.csv).

**Treat these as candidates to verify, not confirmed pits.** There is no ground truth yet, so the pit
threshold is the default 0.6. A visual review of the gallery found real excavations (for example a
1.1 ha water-filled pit dug around February 2026, and a new pit beside what looks like a brick kiln) but also remaining
false detections: pieces of canals wider than ~60 m, specks on roads, fish-pond clusters and flood
pools in the riverbed. Labelling a few dozen examples (below) is the way to fix these.

| Gallery (10 m view · water · radar · probability) | Statistics |
|---|---|
| ![Gallery](results/karnal_2026-06-30_to_2026-09-30/jpg/05_gallery_1_most_confident.jpg) | ![Statistics](results/karnal_2026-06-30_to_2026-09-30/jpg/07_statistics.jpg) ![Pit history](results/karnal_2026-06-30_to_2026-09-30/jpg/06_pit_history_example.jpg) |

Result files in [`results/karnal_2026-06-30_to_2026-09-30/`](results/karnal_2026-06-30_to_2026-09-30/):

| File | What it is |
|---|---|
| `pits.csv` | Every pit: **latitude, longitude, district, tehsil, village**, area, probability, new or older, riverbed or not, pit or likely village pond, Google Maps link |
| `pits_by_tehsil.csv`, `pits_by_village.csv` | Number of pits, hectares and new pits per tehsil and per village |
| `pits.geojson`, `pits.gpkg` | Pit outlines for QGIS / ArcGIS, with latitude / longitude attributes |
| `pits.kml` | Google Earth: outline + numbered pin per pit, coordinates and a Google Maps link in each pin (red = new, magenta = older, blue = likely village pond) |
| `pit_probability.tif` | Pit probability for every 10 m pixel (0–100) |
| `jpg/` | Numbered pit map with tehsil and village boundaries and a latitude / longitude grid, coordinate tables of the new and largest pits (08, 09), pits per tehsil (10), inputs, training examples, validation, probability, 4 gallery pages (coordinates in every title), pit history, statistics |
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

## Pit coordinates

Every pit's latitude, longitude, tehsil and village are in [`pits.csv`](results/karnal_2026-06-30_to_2026-09-30/pits.csv) (also in the
GeoJSON, GeoPackage and KML). The tables below list the new pits and the largest pits; **Map** opens the
spot in Google Maps.

| New pits — coordinates | Largest pits — coordinates |
|---|---|
| ![New pits](results/karnal_2026-06-30_to_2026-09-30/jpg/08_new_pits_coordinates.jpg) | ![Largest pits](results/karnal_2026-06-30_to_2026-09-30/jpg/09_largest_pits_coordinates.jpg) |

<details>
<summary><b>40 new pits</b> (cropland in the same months of 2025, bare or flooded now) — largest first</summary>

| Pit | Latitude | Longitude | Village | Tehsil | Area (ha) | Setting | Map |
|---:|---:|---:|---|---|---:|---|---|
| 81 | 29.551990 | 77.106034 | Khwajpur | Gharaunda | 4.68 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.551990,77.106034) |
| 120 | 29.544302 | 76.812257 | Pabana Hassanpur (72) | Ballah ST | 3.75 | outside riverbed | [open](https://www.google.com/maps?q=29.544302,76.812257) |
| 34 | 29.584420 | 77.093854 |  | (Samli district) | 3.32 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.584420,77.093854) |
| 4 | 29.810760 | 77.003337 | Smora(55) | Indri | 1.11 | outside riverbed | [open](https://www.google.com/maps?q=29.810760,77.003337) |
| 204 | 29.478478 | 77.069607 | Garhi Bhalal(43) | Gharaunda | 1.11 | outside riverbed | [open](https://www.google.com/maps?q=29.478478,77.069607) |
| 91 | 29.749565 | 76.858769 | Bir Naraina (59) | Nilokheri | 1.06 | outside riverbed | [open](https://www.google.com/maps?q=29.749565,76.858769) |
| 224 | 29.860365 | 76.904257 | Raipur Roran (44) | Nilokheri | 0.91 | outside riverbed | [open](https://www.google.com/maps?q=29.860365,76.904257) |
| 47 | 29.733917 | 77.090244 | Mohamadpur (76) | Karnal | 0.64 | outside riverbed | [open](https://www.google.com/maps?q=29.733917,77.090244) |
| 221 | 29.669008 | 76.695528 | Ichhanpur (40) | Assandh | 0.57 | outside riverbed | [open](https://www.google.com/maps?q=29.669008,76.695528) |
| 67 | 29.527347 | 76.678371 | Phaphrana (94) | Assandh | 0.52 | outside riverbed | [open](https://www.google.com/maps?q=29.527347,76.678371) |
| 350 | 29.620713 | 76.742982 | Dachaur (62) | Nising ST | 0.50 | outside riverbed | [open](https://www.google.com/maps?q=29.620713,76.742982) |
| 186 | 29.475289 | 76.895936 |  | (Panipat district) | 0.45 | outside riverbed | [open](https://www.google.com/maps?q=29.475289,76.895936) |
| 97 | 29.744403 | 76.851811 | Bahlolpur Mushtarka (19) | Karnal | 0.40 | outside riverbed | [open](https://www.google.com/maps?q=29.744403,76.851811) |
| 193 | 29.476199 | 76.895850 |  | (Panipat district) | 0.37 | outside riverbed | [open](https://www.google.com/maps?q=29.476199,76.895850) |
| 78 | 29.559661 | 76.885625 | Gagsina (16) | Gharaunda | 0.32 | outside riverbed | [open](https://www.google.com/maps?q=29.559661,76.885625) |
| 183 | 29.628630 | 76.581756 |  | (Kaithal district) | 0.29 | outside riverbed | [open](https://www.google.com/maps?q=29.628630,76.581756) |
| 266 | 29.591407 | 77.076752 | Lalupura (109) | Gharaunda | 0.19 | outside riverbed | [open](https://www.google.com/maps?q=29.591407,77.076752) |
| 349 | 29.523390 | 76.667479 | Phaphrana (94) | Assandh | 0.19 | outside riverbed | [open](https://www.google.com/maps?q=29.523390,76.667479) |
| 95 | 29.745930 | 76.857138 | Saga (58) | Nilokheri | 0.18 | outside riverbed | [open](https://www.google.com/maps?q=29.745930,76.857138) |
| 90 | 29.747861 | 77.085840 | Baragaon (69) | Karnal | 0.17 | outside riverbed | [open](https://www.google.com/maps?q=29.747861,77.085840) |
| 331 | 29.475677 | 77.073346 | Garhi Bhalal(43) | Gharaunda | 0.16 | outside riverbed | [open](https://www.google.com/maps?q=29.475677,77.073346) |
| 6 | 29.533573 | 76.578337 | Assandh (Rural)(Part)(84) | Assandh | 0.16 | outside riverbed | [open](https://www.google.com/maps?q=29.533573,76.578337) |
| 470 | 29.576145 | 76.947126 | Upli (9) | Gharaunda | 0.16 | outside riverbed | [open](https://www.google.com/maps?q=29.576145,76.947126) |
| 257 | 29.656760 | 77.121982 | Dhakwala (121) | Karnal | 0.14 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.656760,77.121982) |
| 93 | 29.747587 | 76.859285 | Bir Naraina (59) | Nilokheri | 0.13 | outside riverbed | [open](https://www.google.com/maps?q=29.747587,76.859285) |
| 534 | 29.478606 | 76.628123 | Theh Malakpur (91) | Assandh | 0.11 | outside riverbed | [open](https://www.google.com/maps?q=29.478606,76.628123) |
| 387 | 29.591788 | 77.077265 | Lalupura (109) | Gharaunda | 0.11 | outside riverbed | [open](https://www.google.com/maps?q=29.591788,77.077265) |
| 367 | 29.558354 | 77.017418 | Arainpura (12) | Gharaunda | 0.10 | outside riverbed | [open](https://www.google.com/maps?q=29.558354,77.017418) |
| 255 | 29.656974 | 77.121328 | Dhakwala (121) | Karnal | 0.08 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.656974,77.121328) |
| 279 | 29.577853 | 76.962126 | Gharaunda (Rural)(Part) (27) | Gharaunda | 0.08 | outside riverbed | [open](https://www.google.com/maps?q=29.577853,76.962126) |
| 547 | 29.902955 | 76.781180 |  | (Kurukshetra district) | 0.06 | outside riverbed | [open](https://www.google.com/maps?q=29.902955,76.781180) |
| 378 | 29.711122 | 77.132891 | Kunda Kalan (114) | Karnal | 0.06 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.711122,77.132891) |
| 480 | 29.523947 | 76.666929 | Phaphrana (94) | Assandh | 0.05 | outside riverbed | [open](https://www.google.com/maps?q=29.523947,76.666929) |
| 697 | 29.569891 | 77.104186 | Khwajpur | Gharaunda | 0.05 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.569891,77.104186) |
| 212 | 29.660110 | 77.123478 | Dhakwala (121) | Karnal | 0.05 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.660110,77.123478) |
| 525 | 29.734211 | 77.089524 | Mohamadpur (76) | Karnal | 0.04 | outside riverbed | [open](https://www.google.com/maps?q=29.734211,77.089524) |
| 556 | 29.559058 | 76.885420 | Gagsina (16) | Gharaunda | 0.04 | outside riverbed | [open](https://www.google.com/maps?q=29.559058,76.885420) |
| 635 | 29.487498 | 77.030094 | Pundri (40) | Gharaunda | 0.04 | outside riverbed | [open](https://www.google.com/maps?q=29.487498,77.030094) |
| 281 | 29.686111 | 76.870618 | Mandhai (41) | Karnal | 0.03 | outside riverbed | [open](https://www.google.com/maps?q=29.686111,76.870618) |
| 80 | 29.720678 | 77.132387 | Kunda Kalan (114) | Karnal | 0.03 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.720678,77.132387) |

</details>

<details>
<summary><b>15 largest pits</b></summary>

| Pit | Latitude | Longitude | Village | Tehsil | Area (ha) | Setting | Map |
|---:|---:|---:|---|---|---:|---|---|
| 51 | 29.840733 | 76.976821 | Amargarh (66) | Nilokheri | 5.75 | outside riverbed | [open](https://www.google.com/maps?q=29.840733,76.976821) |
| 81 | 29.551990 | 77.106034 | Khwajpur | Gharaunda | 4.68 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.551990,77.106034) |
| 120 | 29.544302 | 76.812257 | Pabana Hassanpur (72) | Ballah ST | 3.75 | outside riverbed | [open](https://www.google.com/maps?q=29.544302,76.812257) |
| 34 | 29.584420 | 77.093854 |  | (Samli district) | 3.32 | Yamuna riverbed | [open](https://www.google.com/maps?q=29.584420,77.093854) |
| 190 | 29.606444 | 76.835694 | Bansa (57) | Karnal | 3.25 | outside riverbed | [open](https://www.google.com/maps?q=29.606444,76.835694) |
| 128 | 29.552063 | 76.810161 | Balran Gran (70) | Ballah ST | 2.83 | outside riverbed | [open](https://www.google.com/maps?q=29.552063,76.810161) |
| 195 | 29.607638 | 76.571657 | Rahra (73) | Assandh | 2.58 | outside riverbed | [open](https://www.google.com/maps?q=29.607638,76.571657) |
| 179 | 29.903693 | 76.781160 |  | (Kurukshetra district) | 2.32 | outside riverbed | [open](https://www.google.com/maps?q=29.903693,76.781160) |
| 77 | 29.576189 | 76.796276 | Bhambar Heri (69) | Ballah ST | 2.19 | outside riverbed | [open](https://www.google.com/maps?q=29.576189,76.796276) |
| 37 | 29.841095 | 76.891809 | Seedpur (41) | Nilokheri | 2.16 | outside riverbed | [open](https://www.google.com/maps?q=29.841095,76.891809) |
| 114 | 29.551416 | 76.659306 | Jhabala (81) | Assandh | 2.09 | outside riverbed | [open](https://www.google.com/maps?q=29.551416,76.659306) |
| 389 | 29.728846 | 76.880177 | Kachhwa (11) | Karnal | 1.98 | outside riverbed | [open](https://www.google.com/maps?q=29.728846,76.880177) |
| 36 | 29.795283 | 76.980188 | Ramba(62) | Karnal | 1.83 | outside riverbed | [open](https://www.google.com/maps?q=29.795283,76.980188) |
| 313 | 29.835544 | 76.896958 | Dheru Majra (42) | Nilokheri | 1.79 | outside riverbed | [open](https://www.google.com/maps?q=29.835544,76.896958) |
| 191 | 29.479668 | 76.529161 | Ardana (64) | Assandh | 1.70 | outside riverbed | [open](https://www.google.com/maps?q=29.479668,76.529161) |

</details>

## Repository

| Path | What it is |
|---|---|
| [`notebooks/karnal_pit_detection.ipynb`](notebooks/karnal_pit_detection.ipynb) | Main workflow: Earth Engine features → download → features, training, pit outlines, gallery, maps, pit history, statistics, exports |
| [`gee/mine_pit_detection.js`](gee/mine_pit_detection.js) | The same idea entirely in the Earth Engine Code Editor (no download), with click-to-label layers — see [Use it in Google Earth Engine only](#use-it-in-google-earth-engine-only-no-python) |
| [`data/`](data/) | Tehsil, village and neighbouring-district boundaries of Karnal (GeoJSON + shapefile zip) |
| [`tools/get_boundaries.py`](tools/get_boundaries.py) | Makes the tehsil and village boundary files for any Indian district: `python tools/get_boundaries.py Panipat` |
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
   water / bare / vegetation / building fractions, automatic training examples plus your own points,
   a gradient-boosting model validated on 5 km blocks it never trained on.
4. **Pit objects**: hysteresis outlines; building pixels removed; tiny pits kept only when very
   confident; canals, drains, roads and thin lines dropped; village ponds tagged; riverbed pits tagged.
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
- Tehsil boundaries are from 2018 and village boundaries from the 2011 Census; their edges do not match
  exactly, and newer administrative changes are not included. Pits right at a boundary may be assigned
  to the neighbouring unit.

## Data and credits

Copernicus Sentinel-1 and Sentinel-2; Cloud Score+; Google Dynamic World; Google DeepMind AlphaEarth
Foundations satellite embeddings; Google Open Buildings 2.5D Temporal; ESA WorldCover; WWF HydroSHEDS
Free-Flowing Rivers; FAO GAUL 2015 boundaries — all via Google Earth Engine. Tehsil (2018) and village
(2011 Census) boundaries: [geoBoundaries](https://www.geoboundaries.org) gbOpen India ADM3 / ADM5
(source: Pathways Data, Local Government Directory and Census of India), Open Data Commons ODbL 1.0. Optional SEN2SR
super-resolution by ESA OpenSR. The detection ideas (context, shape, block validation, local labels)
were informed by [BapakmuLah/Satellit-Based-Open-Pit-Mining-Detection](https://github.com/BapakmuLah/Satellit-Based-Open-Pit-Mining-Detection).
