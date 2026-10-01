/*******************************************************************************
 * SAND / EXCAVATION PIT DETECTION WITH AI — KARNAL DISTRICT, HARYANA, INDIA
 * Past 3 months · multi-sensor · Google Earth Engine Code Editor script
 *
 * Data fused at 10 m (all free in Earth Engine):
 *   - Sentinel-2 (optical): every clear scene of the past 3 months, plus the
 *     same 3 months last year (what the land was before it was dug).
 *   - Sentinel-1 (radar): sees through monsoon cloud.
 *   - Dynamic World (Google's AI land-cover model, one map per Sentinel-2 scene).
 *   - AlphaEarth Foundations embeddings (Google DeepMind's AI foundation model).
 *
 * Building knowledge (pits vs buildings)
 *   Roofs, shadows and construction sites can look like bare / wet ground in
 *   optical images. The script tells them apart with:
 *   - Four independent building sources that "vote":
 *       Open Buildings 2.5D Temporal (Google AI building map, 4 m, latest year),
 *       ESA WorldCover built-up (2021), Dynamic World "built" during the window
 *       (catches new buildings), and Sentinel-1 radar double bounce — walls and
 *       ground form corner reflectors, so buildings are very bright in radar
 *       while water and smooth sand in pits are dark.
 *   - Physical rules: automatic pit examples must be radar-dark, have no
 *     building evidence and lie outside settlements; buildings are a large,
 *     dedicated "not pit" class, and pit look-alikes that turn out to be
 *     buildings / construction sites are kept as "not pit" examples.
 *   - Knowledge features given to the model: building presence and height,
 *     number of agreeing sources, share of buildings within 50 m, local
 *     texture, radar VV/VH ratio.
 *   - A final filter: pixels where 2+ sources agree on "building" are removed
 *     (shown in grey), and outlines that are mostly building are dropped.
 *
 * If you get "Computation timed out"
 *   Automatic examples are collected in sample cells (see CONFIG.trainingCells),
 *   not the whole district. If it still times out, halve trainingCells /
 *   riverCells, or cache the samples once as a batch task (no time limit):
 *   1. Tasks tab -> RUN "cache_training_samples_v3_..." and wait for it to finish.
 *   2. Put its asset ID in CONFIG.samplesAsset, and set CONFIG.endDate to the
 *      end date printed in the Console so the map uses the same period.
 *   3. Run again — training then takes seconds.
 *   (Caches from earlier versions lack the new features; re-run the v3 task.
 *   The cache includes your points as they were when it ran — re-run it after
 *   adding more.)
 *
 * Ideas taken from deep-learning pit detectors (e.g. the YOLOv8 open-pit
 * notebook), rebuilt for Sentinel data inside Earth Engine
 *   - Context: a CNN judges a pit by its surroundings. Context features here
 *     compare each pixel with the ring around it (a bare / wet / radar-dark
 *     patch inside green fields is pit-like; the same values inside a village
 *     are not).
 *   - Shape: pits are compact (aspect ratio ~0.5-2). Long thin outlines —
 *     canals, roads, river channels — are dropped (CONFIG.minCompactness).
 *   - Honest validation: samples are split by ~5 km blocks, never by random
 *     pixels, so neighbouring pixels of one pit can't sit in both training
 *     and validation. Scores are reported for several thresholds, and against
 *     YOUR labels when you add them.
 *   - Local labels: a detector is only as good as its local examples.
 *
 * Improving results: label pits yourself (no extra imagery needed)
 *   The script adds two point layers, `pits` (red) and `nonPits` (blue), to
 *   the drawing tools. The Satellite basemap under the map is high resolution,
 *   so zoom to 16-18, pick a layer and click to add points:
 *     pits    : sand-mining pits in the Yamuna bed and khadar (dry and
 *               water-filled), brick-kiln clay pits, soil / borrow pits.
 *     nonPits : everything it got wrong — roofs, construction sites, natural
 *               sand bars, flood sand on fields, brick kilns themselves,
 *               canals, fish ponds, fallow fields.
 *   Then press Run. Your points are combined with the automatic examples and
 *   get their own accuracy table in the Console. The "Model unsure" layer
 *   shows where new points help most. The basemap may be a few months or
 *   years older than the Sentinel window, so label pits that are visible in
 *   both.
 *******************************************************************************/


// =============================================================================
// 1. CONFIGURATION
// =============================================================================
var CONFIG = {
  // Area of interest: districts from FAO GAUL 2015 (to use your own polygon
  // instead, draw a geometry import named `aoi`).
  state: 'Haryana',
  districts: [['Karnal']],   // one entry per district: spellings to try, e.g. [['Karnal'], ['Sonipat', 'Sonepat']]
  fallbackAoi: ee.Geometry.Rectangle([76.55, 29.4, 77.25, 30.0]),  // if no name is found

  // Time window: the months up to endDate (null = today). Compared with the
  // same months one year earlier to spot newly dug pits.
  endDate: null,              // e.g. '2026-09-29' to freeze the window
  monthsBack: 3,

  // Cached training samples (see "Computation timed out" above). Overrides
  // `pits` / `nonPits` when set. Example: 'projects/my-project/assets/pit_samples'
  samplesAsset: null,

  scale: 10,                  // analysis resolution (m)
  cloudScoreMin: 0.6,         // Cloud Score+ clear-sky threshold (lower = more scenes kept)

  // Building knowledge
  builtPresence: 0.5,         // Open Buildings presence above this = a building vote
  builtDW: 0.35,              // Dynamic World "built" share above this = a building vote
  builtVV: -6,                // dB; radar median brighter than this = a building vote
  pitMaxVV: -11,              // dB; automatic pit examples must be darker than this
  settlementRadius: 50,       // m; "buildings nearby" neighbourhood
  maxBuiltShare: 0.5,         // drop outlines where more than this share has building evidence

  // Auto labels (used only without `pits` / `nonPits` or a samples asset).
  // Examples are collected inside random sample cells rather than the whole
  // district, which keeps the interactive run inside Earth Engine's time limit.
  trainingCells: 30,          // random cells spread over the district
  riverCells: 10,             // extra cells along the Yamuna (sand mining)
  cellSize: 3000,             // m, side of each cell
  labelScale: 20,             // m; strata sampling resolution inside the cells
  pitSamples: 1000,           // pit points
  builtSamples: 600,          // building points (hard negatives)
  otherSamples: 250,          // points for each of water, crops/trees, dry bare land
  neverGreenNdvi: 0.25,       // NDVI 90th percentile below this = bare the whole window
  greenNdvi: 0.45,            // NDVI 90th percentile above this = crops / trees
  wetNdwi: 0.0,               // NDWI 90th percentile above this = holds water at times
  permanentWaterNdwi: 0.0,    // NDWI median above this = water most of the window
  riverMinDischarge: 50,      // m3/s; rivers at least this big count as "riverbed"
  riverbedBuffer: 1500,       // m either side of the river line

  // Your labels (`pits` / `nonPits`)
  useAutoLabels: true,        // false = learn only from your points (once you have ~100+ of each)
  userLabelBuffer: 15,        // m; each point is sampled as a small disc (several pixels)

  // Context features
  contextRadius: 60,          // m; each pixel is compared with its surroundings out to here

  // Model + validation
  numberOfTrees: 100,
  blockDeg: 0.05,             // validation blocks (~5 km); whole blocks go to train or validation
  validationPercent: 25,      // share of blocks held out; 0 = train on everything (for the final run)
  probabilityThreshold: 0.6,  // pick from the threshold table against your points in the Console

  // Output
  minPitAreaHa: 0.05,         // 5 pixels: smallest patch kept...
  smallPitAreaHa: 0.1,        // ...but patches below this size
  smallPitMinProb: 0.65,      // must have at least this mean probability
  minCompactness: 0.2,        // 4*pi*area/perimeter^2; drops canals, roads, riverbank strips
  minZoomForOutlines: 13,
  similarityMin: 0.85,        // click-to-search display cut-off
  exportFolder: 'GEE_pits'
};

// --- Area of interest ----------------------------------------------------------
var gaulState = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.eq('ADM1_NAME', CONFIG.state));
var districts = gaulState
  .filter(ee.Filter.inList('ADM2_NAME', [].concat.apply([], CONFIG.districts)))
  .map(function (d) {
    return ee.Feature(d.geometry(), {name: d.get('ADM2_NAME'), zone: d.get('ADM2_CODE')});
  });

// `zones` = the polygons results are reported by (districts, or a single AOI).
var zones = (typeof aoi !== 'undefined')
  ? ee.FeatureCollection([ee.Feature(ee.FeatureCollection(aoi).geometry(), {name: 'AOI', zone: 1})])
  : ee.FeatureCollection(ee.Algorithms.If(
      districts.size().gt(0),
      districts,
      ee.FeatureCollection([ee.Feature(CONFIG.fallbackAoi, {name: 'fallback AOI', zone: 1})])));
var region = zones.geometry();

if (typeof aoi === 'undefined') {
  districts.aggregate_array('name').evaluate(function (found) {
    if (!found || found.length < CONFIG.districts.length) {
      print('Warning: only matched ' + JSON.stringify(found) + '. District names in ' +
            CONFIG.state + ' (fix CONFIG.districts):', gaulState.aggregate_array('ADM2_NAME'));
    }
  });
}

var areaLabel = CONFIG.districts.map(function (d) { return d[0]; }).join(' + ');
var areaName = CONFIG.districts.map(function (d) { return d[0].toLowerCase(); }).join('_');
var hasUserLabels = (typeof pits !== 'undefined') && (typeof nonPits !== 'undefined');

// Point layers for labelling. Drawing-tool layers are saved as imports, so the
// points you click are still there (as `pits` / `nonPits`) on the next Run.
var drawingTools = Map.drawingTools();
if (typeof pits === 'undefined') {
  drawingTools.addLayer([], 'pits', 'ff0000');
}
if (typeof nonPits === 'undefined') {
  drawingTools.addLayer([], 'nonPits', '0000ff');
}
drawingTools.setShape('point');

// Geometry or FeatureCollection import -> one feature per point / polygon.
function labelFeatures(layer, value) {
  var features = (layer instanceof ee.Geometry)
    ? ee.FeatureCollection(layer.geometries().map(function (g) {
        return ee.Feature(ee.Geometry(g));
      }))
    : ee.FeatureCollection(layer);
  return features.map(function (f) {
    return f.set('class', value);
  });
}

// --- Time windows ------------------------------------------------------------------
function isoDate(d) {
  return d.toISOString().slice(0, 10);
}
var endJs = CONFIG.endDate ? new Date(CONFIG.endDate) : new Date();
var startJs = new Date(endJs.getTime());
startJs.setMonth(startJs.getMonth() - CONFIG.monthsBack);

var startStr = isoDate(startJs);
var endStr = isoDate(endJs);
var start = ee.Date(startStr);
var end = ee.Date(endStr);
var periodTag = startStr.replace(/-/g, '') + '_' + endStr.replace(/-/g, '');
print('Period analysed: ' + startStr + ' to ' + endStr +
      ' (compared with the same months of the previous year)');


// =============================================================================
// 2. INPUT DATA
// =============================================================================

// --- 2a. Sentinel-2, cloud-masked with Cloud Score+ ---------------------------
var csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');

function sentinel2(from, to) {
  return ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(region)
    .filterDate(from, to)
    .linkCollection(csPlus, ['cs_cdf'])
    .map(function (img) {
      var sr = img.select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12']).divide(10000);
      var bsi = sr.expression(
        '((S1 + R) - (N + B)) / ((S1 + R) + (N + B))', {
          S1: sr.select('B11'),
          R: sr.select('B4'),
          N: sr.select('B8'),
          B: sr.select('B2')
        }).rename('BSI');                                                   // bare soil
      return sr
        .addBands(sr.normalizedDifference(['B8', 'B4']).rename('NDVI'))   // 10 m
        .addBands(sr.normalizedDifference(['B3', 'B8']).rename('NDWI'))   // 10 m water
        .addBands(bsi)
        .updateMask(img.select('cs_cdf').gte(CONFIG.cloudScoreMin));
    });
}

var s2 = sentinel2(start, end);

var composite = s2.select(['B2', 'B3', 'B4', 'B8', 'B11', 'B12']).median().clip(region);
var ndbi = composite.normalizedDifference(['B11', 'B8']).rename('NDBI');
var ironOxide = composite.select('B4').divide(composite.select('B2')).rename('IRON_OXIDE');
var clay = composite.select('B11').divide(composite.select('B12')).rename('CLAY');

// Behaviour over the window: NDVI_p90 = greenest moment, NDWI_p90 = wettest, etc.
var periodStats = s2.select(['NDVI', 'NDWI', 'BSI'])
  .reduce(ee.Reducer.percentile([10, 50, 90]))
  .clip(region);

// Same months last year — what the land was before it was dug.
var previous = sentinel2(start.advance(-1, 'year'), end.advance(-1, 'year'))
  .select(['NDVI', 'NDWI'])
  .reduce(ee.Reducer.percentile([50, 90]))
  .regexpRename('_p', '_prev_p')
  .clip(region);

var change = ee.Image.cat([
  periodStats.select('NDVI_p90').subtract(previous.select('NDVI_prev_p90')).rename('dNDVI_p90'),
  periodStats.select('NDWI_p50').subtract(previous.select('NDWI_prev_p50')).rename('dNDWI_p50')
]);

// --- 2b. Sentinel-1 radar -----------------------------------------------------
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(region)
  .filterDate(start, end)
  .filter(ee.Filter.eq('instrumentMode', 'IW'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
  .select(['VV', 'VH'])
  .map(function (img) {
    return img.updateMask(img.select('VV').gt(-30));   // drop scene-edge noise
  });

var radar = s1.reduce(ee.Reducer.percentile([10, 50, 90])).clip(region);
var radarVV = radar.select('VV_p50');

// --- 2c. Dynamic World (AI land cover per Sentinel-2 scene) ------------------
var DW_CLASSES = ['water', 'trees', 'grass', 'flooded_vegetation', 'crops',
                  'shrub_and_scrub', 'built', 'bare'];
var DW_BANDS = DW_CLASSES.map(function (c) { return 'dw_' + c; });

var dynamicWorld = ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
  .filterBounds(region)
  .filterDate(start, end)
  .select(DW_CLASSES)
  .mean()
  .rename(DW_BANDS)
  .clip(region);

// --- 2d. AlphaEarth Foundations embeddings (AI foundation model) -------------
// Released per calendar year, so use the latest year available before `end`.
var embeddingCollection = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')
  .filterBounds(region);
var embeddingYear = ee.Date(embeddingCollection.filterDate('2017-01-01', end)
  .aggregate_max('system:time_start')).get('year');
var embeddingStart = ee.Date.fromYMD(embeddingYear, 1, 1);
var embeddingsFull = embeddingCollection
  .filterDate(embeddingStart, embeddingStart.advance(1, 'year'))
  .mosaic();
var embeddings = embeddingsFull.clip(region);

var EMBEDDING_BANDS = [];
for (var i = 0; i < 64; i++) {
  EMBEDDING_BANDS.push('A' + (i < 10 ? '0' + i : i));
}

// --- 2e. Building knowledge ------------------------------------------------------
// Open Buildings 2.5D Temporal: Google's AI building map (latest year available).
var openBuildingsTemporal = ee.ImageCollection('GOOGLE/Research/open-buildings-temporal/v1')
  .filterBounds(region);
var openBuildingsLatest = openBuildingsTemporal
  .filter(ee.Filter.eq('system:time_start', openBuildingsTemporal.aggregate_max('system:time_start')))
  .mosaic();
var buildingPresence = openBuildingsLatest.select('building_presence').unmask(0)
  .rename('built_presence');
var buildingHeight = openBuildingsLatest.select('building_height').unmask(0)
  .rename('built_height');

var worldCoverBuilt = ee.ImageCollection('ESA/WorldCover/v200').first().select('Map').eq(50);

// Each source casts one vote for "building here" (0-4).
var builtVotes = ee.Image.cat([
  worldCoverBuilt.unmask(0),
  buildingPresence.gt(CONFIG.builtPresence),
  dynamicWorld.select('dw_built').gt(CONFIG.builtDW).unmask(0),
  radarVV.gt(CONFIG.builtVV).unmask(0)                  // radar double bounce
]).reduce(ee.Reducer.sum()).clip(region).rename('built_votes');

var anyBuilt = builtVotes.gte(1);
var confidentBuilt = builtVotes.gte(2);

var builtNearby = anyBuilt.reduceNeighborhood({
  reducer: ee.Reducer.mean(),
  kernel: ee.Kernel.circle(CONFIG.settlementRadius, 'meters')
}).rename('built_nearby');

// Villages are patchy at 10 m; water and sand in pits are smooth.
var nirTexture = composite.select('B8').reduceNeighborhood({
  reducer: ee.Reducer.stdDev(),
  kernel: ee.Kernel.square(1)
}).rename('NIR_texture');

var radarRatio = radarVV.subtract(radar.select('VH_p50')).rename('VV_VH_ratio');

var BUILT_BANDS = ['built_presence', 'built_height', 'built_votes', 'built_nearby',
                   'NIR_texture', 'VV_VH_ratio'];
var buildingKnowledge = ee.Image.cat([
  buildingPresence, buildingHeight, builtVotes, builtNearby, nirTexture, radarRatio
]);

// --- Context: each pixel compared with its surroundings ------------------------
// What a CNN learns from image patches: a pit is a bare / wet / radar-dark
// patch that differs from the land around it. Built from Dynamic World, radar
// and the median image (not from the auto-label rule bands, so no leakage).
function contrastWithSurroundings(image, name) {
  return image.subtract(image.focalMean(CONFIG.contextRadius, 'circle', 'meters')).rename(name);
}
var CONTEXT_BANDS = ['ctx_crops', 'ctx_water', 'ctx_bare', 'ctx_vv', 'ctx_nir', 'crops_around'];
var context = ee.Image.cat([
  contrastWithSurroundings(dynamicWorld.select('dw_crops'), 'ctx_crops'),
  contrastWithSurroundings(dynamicWorld.select('dw_water'), 'ctx_water'),
  contrastWithSurroundings(dynamicWorld.select('dw_bare'), 'ctx_bare'),
  contrastWithSurroundings(radarVV, 'ctx_vv'),
  contrastWithSurroundings(composite.select('B8'), 'ctx_nir'),
  dynamicWorld.select('dw_crops').focalMean(150, 'circle', 'meters').rename('crops_around')
]);

// --- 2f. Rule layers (auto labels + "new pit" flag) --------------------------
var bigRivers = ee.FeatureCollection('WWF/HydroSHEDS/v1/FreeFlowingRivers')
  .filterBounds(region.bounds().buffer(5000))
  .filter(ee.Filter.gte('DIS_AV_CMS', CONFIG.riverMinDischarge));
var riverZone = bigRivers.map(function (f) {
  return f.buffer(CONFIG.riverbedBuffer, 50);
});
var riverbed = ee.Image(0).paint(riverZone, 1);

var ndviP90 = periodStats.select('NDVI_p90');
var ndwiP50 = periodStats.select('NDWI_p50');
var ndwiP90 = periodStats.select('NDWI_p90');
var prevNdviP90 = previous.select('NDVI_prev_p90');

var neverGreen = ndviP90.lt(CONFIG.neverGreenNdvi);
var neverGreenBefore = prevNdviP90.lt(CONFIG.neverGreenNdvi);
var croppedBefore = prevNdviP90.gt(CONFIG.greenNdvi);
var wetAtTimes = ndwiP90.gt(CONFIG.wetNdwi);
var waterNow = ndwiP50.gt(CONFIG.permanentWaterNdwi);
var waterBefore = previous.select('NDWI_prev_p50').gt(CONFIG.permanentWaterNdwi);

// Vegetated in these months last year, never green now = newly dug (or built).
var clearedSinceLastYear = croppedBefore.and(neverGreen).rename('new');

var newPitRule = clearedSinceLastYear.and(wetAtTimes);               // incl. riverbed sand pits
var olderPitRule = neverGreen.and(neverGreenBefore).and(wetAtTimes)
  .and(waterNow.not()).and(riverbed.not());                          // not natural sand bars

// The strata only use Sentinel-2 and the static building maps, so they are
// cheap to compute. The radar / Dynamic World building checks are applied later,
// only at the sampled points (see section 3).
var staticBuilt = worldCoverBuilt.or(buildingPresence.gt(CONFIG.builtPresence));
var pitCandidate = newPitRule.or(olderPitRule).and(staticBuilt.not());

// 1 = pit candidate, 2 = stable water, 3 = buildings, 4 = crops/trees,
// 5 = dry bare land. Pixels that match none of the rules stay unlabelled.
var strata = ee.Image(0)
  .where(ndviP90.gt(CONFIG.greenNdvi).and(staticBuilt.not()), 4)
  .where(neverGreen.and(ndwiP90.lt(-0.1)).and(staticBuilt.not()), 5)
  .where(staticBuilt, 3)
  .where(waterNow.and(waterBefore), 2)
  .where(pitCandidate, 1)
  .selfMask()
  .rename('stratum');

// Sample cells: random squares across the district plus some along the river,
// where most sand mining happens.
function sampleCells(geometry, count, seed) {
  return ee.FeatureCollection.randomPoints(geometry, count, seed).map(function (p) {
    return p.buffer(CONFIG.cellSize / 2).bounds();
  });
}
var riverZoneInRegion = riverZone.union(50).geometry().intersection(region, 100);
var trainingCells = sampleCells(region, CONFIG.trainingCells, 1).merge(
  ee.FeatureCollection(ee.Algorithms.If(
    riverZoneInRegion.area(100).gt(0),
    sampleCells(riverZoneInRegion, CONFIG.riverCells, 2),
    ee.FeatureCollection([]))));
var trainingArea = trainingCells.union(1).geometry();

// --- 2g. Feature stack -------------------------------------------------------
var OPTICAL_BANDS = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12', 'NDBI', 'IRON_OXIDE', 'CLAY',
                     'BSI_p10', 'BSI_p50', 'BSI_p90'];
var RADAR_BANDS = ['VV_p10', 'VV_p50', 'VV_p90', 'VH_p10', 'VH_p50', 'VH_p90'];
// Bands the auto-label pit rules are built from (used only when learning from
// your labels alone, CONFIG.useAutoLabels = false).
var RULE_BANDS = ['NDVI_p10', 'NDVI_p50', 'NDVI_p90', 'NDWI_p10', 'NDWI_p50', 'NDWI_p90',
                  'NDVI_prev_p50', 'NDVI_prev_p90', 'NDWI_prev_p50', 'NDWI_prev_p90',
                  'dNDVI_p90', 'dNDWI_p50'];

var stack = ee.Image.cat([
  embeddings.select(EMBEDDING_BANDS),
  composite, ndbi, ironOxide, clay,
  periodStats, previous, change,
  radar,
  dynamicWorld,
  buildingKnowledge,
  context
]).clip(region);


// =============================================================================
// 3. TRAINING SAMPLES
// =============================================================================
var useAuto = CONFIG.useAutoLabels || !hasUserLabels;
var samples, autoSamples, userSamples, userLabels;
var labelSource = useAuto && hasUserLabels ? 'auto + your points'
                : useAuto ? 'auto (rules + change + building knowledge)'
                : 'your points only';

if (useAuto && !CONFIG.samplesAsset) {
  // 1. Pick points from the cheap strata image, inside the sample cells only.
  var strataPoints = strata.stratifiedSample({
    numPoints: CONFIG.otherSamples,
    classBand: 'stratum',
    classValues: [1, 2, 3, 4, 5],
    classPoints: [CONFIG.pitSamples, CONFIG.otherSamples, CONFIG.builtSamples,
                  CONFIG.otherSamples, CONFIG.otherSamples],
    region: trainingArea,
    scale: CONFIG.labelScale,
    seed: 42,
    tileScale: 16,
    geometries: true
  });

  // 2. Read the full feature stack at those points only.
  // 3. Building knowledge at each pit candidate:
  //      building evidence (any source, or buildings within 50 m) -> it is a
  //        building / construction site that looks like a pit: keep it as a
  //        "not pit" example (stratum 6) so the model learns the difference;
  //      radar-dark with no building evidence -> a clean pit example;
  //      radar-bright with no building evidence -> ambiguous, dropped.
  autoSamples = stack.sampleRegions({
    collection: strataPoints,
    properties: ['stratum'],
    scale: CONFIG.scale,
    tileScale: 16,
    geometries: true
  }).map(function (f) {
    var candidate = ee.Number(f.get('stratum')).eq(1);
    var buildingLike = ee.Number(f.get('built_votes')).gte(1)
      .or(ee.Number(f.get('built_nearby')).gte(0.2));
    var radarDark = ee.Number(f.get('VV_p50')).lt(CONFIG.pitMaxVV);
    var stratum = ee.Number(ee.Algorithms.If(candidate.and(buildingLike), 6, f.get('stratum')));
    return f.set({
      stratum: stratum,
      class: stratum.eq(1),
      source: 'auto',
      keep: candidate.not().or(buildingLike).or(radarDark)
    });
  }).filter(ee.Filter.eq('keep', 1));
}

if (hasUserLabels && !CONFIG.samplesAsset) {
  userLabels = labelFeatures(pits, 1).merge(labelFeatures(nonPits, 0));
  userSamples = stack.sampleRegions({
    collection: userLabels.map(function (f) {
      return f.buffer(CONFIG.userLabelBuffer);
    }),
    properties: ['class'],
    scale: CONFIG.scale,
    tileScale: 16,
    geometries: true
  }).map(function (f) {
    return f.set('source', 'user');
  });
  // Your points overrule automatic examples next to them.
  if (autoSamples) {
    autoSamples = autoSamples.filter(
      ee.Filter.bounds(userLabels.geometry().buffer(50)).not());
  }
}

if (CONFIG.samplesAsset) {
  samples = ee.FeatureCollection(CONFIG.samplesAsset);
  labelSource = 'cached samples asset';
} else {
  samples = autoSamples && userSamples ? autoSamples.merge(userSamples)
          : autoSamples || userSamples;
  // Batch task with no time limit; see "Computation timed out" at the top.
  Export.table.toAsset({
    collection: samples,
    description: 'cache_training_samples_v3_' + periodTag,
    assetId: areaName + '_pit_samples_v3_' + periodTag
  });
}

// Auto labels come from the NDVI / NDWI rules, so those bands are withheld while
// auto labels are used: otherwise the model just memorises the rule. Building
// knowledge and context are always included — that is what tells pits apart.
var featureBands = EMBEDDING_BANDS
  .concat(OPTICAL_BANDS)
  .concat(RADAR_BANDS)
  .concat(DW_BANDS)
  .concat(BUILT_BANDS)
  .concat(CONTEXT_BANDS);
if (!useAuto) {
  featureBands = featureBands.concat(RULE_BANDS);
}


// =============================================================================
// 4. RANDOM FOREST
// =============================================================================
// Split by ~5 km blocks, not by random pixels: neighbouring pixels of the same
// pit are near-copies, and a random split would put them on both sides and
// inflate the scores. Each block gets a fixed pseudo-random number 0-99.
samples = samples.map(function (f) {
  var lonLat = f.geometry().coordinates();
  var bx = ee.Number(lonLat.get(0)).divide(CONFIG.blockDeg).floor();
  var by = ee.Number(lonLat.get(1)).divide(CONFIG.blockDeg).floor();
  return f.set('block', bx.multiply(7919).add(by.multiply(104729)).abs().mod(100));
});
var training = samples.filter(ee.Filter.gte('block', CONFIG.validationPercent));
var validation = samples.filter(ee.Filter.lt('block', CONFIG.validationPercent));

var classifier = ee.Classifier.smileRandomForest({
  numberOfTrees: CONFIG.numberOfTrees,
  minLeafPopulation: 2,
  bagFraction: 0.7,
  seed: 42
}).setOutputMode('PROBABILITY').train({
  features: training,
  classProperty: 'class',
  inputProperties: featureBands
});

var validated = validation.classify(classifier);

// Precision / recall / F1 for the pit class at several thresholds, so the
// threshold can be chosen from evidence rather than guessed.
var THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7];
function thresholdTable(set) {
  var pitSet = set.filter(ee.Filter.eq('class', 1));
  var otherSet = set.filter(ee.Filter.eq('class', 0));
  return ee.Dictionary({
    pits: pitSet.size(),
    others: otherSet.size(),
    rows: ee.List(THRESHOLDS).map(function (t) {
      var tp = pitSet.filter(ee.Filter.gte('classification', t)).size();
      var fp = otherSet.filter(ee.Filter.gte('classification', t)).size();
      var recall = tp.divide(pitSet.size().max(1));
      var precision = tp.divide(tp.add(fp).max(1));
      var f1 = precision.multiply(recall).multiply(2).divide(precision.add(recall).max(1e-9));
      return ee.List([t, precision, recall, f1]);
    })
  });
}


// =============================================================================
// 5. PIT MAP + BUILDING FILTER + VECTORISATION
// =============================================================================
var pitProbability = stack.select(featureBands)
  .classify(classifier)
  .rename('pit_probability');

// Final knowledge filter: where 2+ building sources agree, it is not a pit.
var modelSaysPit = pitProbability.gte(CONFIG.probabilityThreshold);
var pitMask = modelSaysPit.and(confidentBuilt.not()).rename('pit');
var removedAsBuilding = modelSaysPit.and(confidentBuilt);
var newPitMask = pitMask.and(clearedSinceLastYear);

// Each district is painted with its own code so every pit polygon knows which
// district it belongs to.
var zoneImage = ee.Image(0).int32().paint(zones, 'zone').rename('zone');
var zoneNames = ee.Dictionary.fromLists(
  zones.aggregate_array('zone').map(function (z) {
    return ee.Number(z).toInt().format('%d');
  }),
  zones.aggregate_array('name'));

// Outlines every connected patch of pit pixels inside `geometry` at 10 m.
// Small patches are kept only if the model is confident, and outlines that
// are mostly building evidence are dropped.
function vectorisePits(geometry) {
  return zoneImage.updateMask(pitMask)
    .addBands(ee.Image.cat([
      pitProbability,
      clearedSinceLastYear.unmask(0),
      dynamicWorld.select('dw_water'),
      anyBuilt
    ]))
    .reduceToVectors({
      geometry: geometry,
      scale: CONFIG.scale,
      geometryType: 'polygon',
      eightConnected: true,
      labelProperty: 'zone',
      reducer: ee.Reducer.mean().forEach(['prob', 'new_frac', 'water_frac', 'built_frac']),
      maxPixels: 1e10,
      tileScale: 16
    })
    .map(function (f) {
      var geometry = f.geometry();
      var area = geometry.area(1);
      var centroid = geometry.centroid(1).coordinates();
      return f.set({
        district: zoneNames.get(ee.Number(f.get('zone')).toInt().format('%d')),
        area_ha: area.divide(1e4),
        compact: area.multiply(4 * Math.PI).divide(geometry.perimeter(1).pow(2)),
        new_pit: ee.Number(f.get('new_frac')).gte(0.5),
        latitude: centroid.get(1),
        longitude: centroid.get(0),
        // Short name: shapefile field names are limited to 10 characters.
        maps_link: ee.String('https://www.google.com/maps?q=')
          .cat(ee.Number(centroid.get(1)).format('%.6f')).cat(',')
          .cat(ee.Number(centroid.get(0)).format('%.6f'))
      });
    })
    .filter(ee.Filter.gte('area_ha', CONFIG.minPitAreaHa))
    .filter(ee.Filter.or(
      ee.Filter.gte('area_ha', CONFIG.smallPitAreaHa),
      ee.Filter.gte('prob', CONFIG.smallPitMinProb)))
    .filter(ee.Filter.lte('built_frac', CONFIG.maxBuiltShare))
    .filter(ee.Filter.gte('compact', CONFIG.minCompactness))       // not canals / roads
    .select(['district', 'latitude', 'longitude', 'area_ha', 'prob', 'new_pit', 'water_frac',
             'built_frac', 'compact', 'maps_link']);
}


// =============================================================================
// 6. MAP DISPLAY + UI
// =============================================================================
var PROB_PALETTE = ['3b0f70', '8c2981', 'de4968', 'fe9f6d', 'fcfdbf'];
var PIT_COLOR = 'ff00ff';
var NEW_PIT_COLOR = 'ff2020';
var REMOVED_COLOR = '9e9e9e';
var OUTLINE_COLOR = '00ffff';

Map.centerObject(region, 10);
Map.setOptions('SATELLITE');

// Input layers (don't need the model).
Map.addLayer(composite, {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3, gamma: 1.2},
  'Sentinel-2 median ' + startStr + ' to ' + endStr);
Map.addLayer(periodStats.select('NDWI_p90'), {min: -0.5, max: 0.3, palette: ['f5deb3', 'ffffff', '2166ac']},
  'Wettest NDWI of the window (pits often hold water)', false);
Map.addLayer(radarVV, {min: -22, max: -2},
  'Sentinel-1 radar VV (bright = buildings, dark = water / sand)', false);
Map.addLayer(dynamicWorld.select(['dw_bare', 'dw_crops', 'dw_water']), {min: 0, max: 0.8},
  'Dynamic World share of time: R bare, G crops, B water', false);
Map.addLayer(builtVotes.selfMask(), {min: 1, max: 4, palette: ['fee391', 'fe9929', 'cc4c02', '662506']},
  'Building knowledge: sources agreeing (1-4)', false);
Map.addLayer(ee.FeatureCollection('GOOGLE/Research/open-buildings/v3/polygons')
    .filterBounds(region)
    .filter(ee.Filter.gte('confidence', 0.7))
    .style({color: 'ffffff', fillColor: '00000000', width: 1}), {},
  'Open Buildings footprints 2023 (zoom 15+)', false);
Map.addLayer(clearedSinceLastYear.selfMask(), {palette: ['ffa500']},
  'Cropland this time last year, bare/flooded now', false);
Map.addLayer(riverbed.selfMask().clip(region), {palette: ['00bfff']}, 'Yamuna riverbed zone', false);
Map.addLayer(strata.clip(region),
  {min: 1, max: 5, palette: ['ff0000', '0000ff', '808080', '00aa00', 'f4a460']},
  'Auto label strata (red pit candidate, blue water, grey buildings, green crops, tan dry bare)', false);
if (useAuto && !CONFIG.samplesAsset) {
  Map.addLayer(trainingCells.style({color: 'ffffff', fillColor: '00000000', width: 1}), {},
    'Training sample cells', false);
}
Map.addLayer(ee.Image().byte().paint({featureCollection: zones, color: 1, width: 2}),
  {palette: ['ffff00']}, 'District boundaries');

// --- Panel -------------------------------------------------------------------
function legendRow(color, text) {
  return ui.Panel([
    ui.Label('', {backgroundColor: '#' + color, padding: '7px', margin: '2px 6px 2px 0'}),
    ui.Label(text, {fontSize: '12px', margin: '2px 0'})
  ], ui.Panel.Layout.flow('horizontal'));
}

var panel = ui.Panel({style: {width: '330px', position: 'bottom-left', padding: '8px'}});
panel.add(ui.Label('Sand / excavation pits — ' + areaLabel + ', ' + CONFIG.state,
  {fontWeight: 'bold', fontSize: '15px', margin: '0 0 4px 0'}));
panel.add(ui.Label('Period: ' + startStr + ' to ' + endStr, {fontSize: '12px', margin: '0'}));
panel.add(ui.Label('Data: Sentinel-2 + Sentinel-1 + Dynamic World + AlphaEarth\n' +
  '+ building knowledge (Open Buildings, WorldCover, radar)',
  {fontSize: '12px', margin: '0', whiteSpace: 'pre'}));
panel.add(ui.Label('Labels: ' + labelSource, {fontSize: '12px', margin: '0 0 6px 0'}));
panel.add(legendRow(NEW_PIT_COLOR, 'New pit (cropland this time last year)'));
panel.add(legendRow(PIT_COLOR, 'Older pit'));
panel.add(legendRow(REMOVED_COLOR, 'Removed: looks like a building'));
panel.add(legendRow(OUTLINE_COLOR, 'Outlined pits (≥ ' + CONFIG.minPitAreaHa + ' ha)'));
panel.add(legendRow('ffff00', 'District boundaries'));

var statusLabel = ui.Label('Training the model… (usually 1–3 minutes)',
  {fontSize: '12px', fontWeight: 'bold', whiteSpace: 'pre'});

var modelReady = false;
var pitsLayer = null;

function showPits(geometry, scopeText) {
  var found = vectorisePits(geometry);
  if (pitsLayer) {
    Map.layers().remove(pitsLayer);
  }
  pitsLayer = ui.Map.Layer(
    found.style({color: OUTLINE_COLOR, fillColor: OUTLINE_COLOR + '33', width: 2}), {},
    'Outlined pits (' + scopeText + ')');
  Map.layers().add(pitsLayer);

  statusLabel.setValue('Counting pits in ' + scopeText + '…');
  ee.Dictionary({
    count: found.size(),
    area: found.aggregate_sum('area_ha'),
    newCount: found.filter(ee.Filter.eq('new_pit', 1)).size(),
    small: found.filter(ee.Filter.lt('area_ha', 0.5)).size(),
    byDistrict: found.aggregate_histogram('district')
  }).evaluate(function (r, error) {
    if (error) {
      statusLabel.setValue('Could not finish (' + error + ').\n' +
        'Zoom in further, or use the exports in the Tasks tab.');
      return;
    }
    var lines = [r.count + ' pits in ' + scopeText];
    Object.keys(r.byDistrict).forEach(function (name) {
      lines.push('   ' + name + ': ' + r.byDistrict[name]);
    });
    lines.push(r.newCount + ' new since this time last year');
    lines.push(r.small + ' smaller than 0.5 ha');
    lines.push(r.area.toFixed(1) + ' ha total');
    statusLabel.setValue(lines.join('\n'));
  });
}

panel.add(ui.Button({
  label: 'Outline + count pits in current view',
  style: {stretch: 'horizontal'},
  onClick: function () {
    if (!modelReady) {
      statusLabel.setValue('Wait until the model has finished training.');
      return;
    }
    if (Map.getZoom() < CONFIG.minZoomForOutlines) {
      statusLabel.setValue('Zoom in to level ' + CONFIG.minZoomForOutlines + ' or more first.');
      return;
    }
    showPits(ee.Geometry.Rectangle(Map.getBounds()).intersection(region, 1), 'current view');
  }
}));
panel.add(statusLabel);
panel.add(ui.Label('Full pit list for the whole district: Tasks tab → RUN the exports.',
  {fontSize: '11px', color: 'gray'}));
panel.add(ui.Label('Improve it: zoom to 16+, pick the pits (red) or nonPits (blue) layer in ' +
  'the drawing tools, click to add points on the Satellite basemap, then Run again. ' +
  'Start where the "Model unsure" layer is.',
  {fontSize: '11px', color: 'gray'}));

var similarityToggle = ui.Checkbox('Click map to find pits similar to the clicked one', false,
  null, false, {fontSize: '12px'});
panel.add(similarityToggle);
Map.add(panel);

// --- Train once, then add the model layers --------------------------------------
// Everything that needs the trained model is fetched in ONE request, so the
// samples are collected once instead of once per Console item.
var summary = {
  s2Scenes: s2.size(),
  s1Scenes: s1.size(),
  embeddingYear: embeddingYear,
  trainAuto: training.filter(ee.Filter.eq('source', 'auto')).aggregate_histogram('class'),
  trainUser: training.filter(ee.Filter.eq('source', 'user')).aggregate_histogram('class'),
  validAuto: thresholdTable(validated.filter(ee.Filter.eq('source', 'auto'))),
  validUser: thresholdTable(validated.filter(ee.Filter.eq('source', 'user'))),
  importance: classifier.explain().get('importance')
};
if (useAuto && !CONFIG.samplesAsset) {
  summary.samplesPerStratum = autoSamples.aggregate_histogram('stratum');
}

// Console table: one row per threshold; the configured one is marked.
function printThresholdTable(title, table) {
  if (!table.pits || !table.others) {
    print(title + ': not enough examples in the validation blocks (' + table.pits +
          ' pits, ' + table.others + ' not-pits).');
    return;
  }
  var rows = table.rows.map(function (r) {
    var mark = Math.abs(r[0] - CONFIG.probabilityThreshold) < 1e-9 ? ' ◀ current' : '';
    return [r[0] + mark, Math.round(r[1] * 100) + '%', Math.round(r[2] * 100) + '%',
            r[3].toFixed(2)];
  });
  print(ui.Chart([['Threshold', 'Precision (pits found that are real)',
                   'Recall (real pits found)', 'F1']].concat(rows), 'Table', {
    title: title + ' — ' + table.pits + ' pit / ' + table.others + ' not-pit samples'
  }));
}

ee.Dictionary(summary).evaluate(function (r, error) {
  if (error) {
    var timedOut = String(error).toLowerCase().indexOf('timed out') !== -1;
    statusLabel.setValue('Model training failed' + (timedOut ? ' (timed out).' : '.') + '\n' +
      'Tasks tab → RUN "cache_training_samples_v3_' + periodTag + '",\n' +
      'then set CONFIG.samplesAsset to its asset ID\n' +
      "and CONFIG.endDate = '" + endStr + "', and Run again.");
    print('Model training failed:', error);
    return;
  }

  var report = {
    'Period': startStr + ' to ' + endStr,
    'Labels': labelSource,
    'Sentinel-2 scenes': r.s2Scenes,
    'Sentinel-1 scenes': r.s1Scenes,
    'AlphaEarth embedding year': r.embeddingYear,
    'Training samples, automatic (0 = not pit, 1 = pit)': r.trainAuto,
    'Training samples, your points (0 = not pit, 1 = pit)': r.trainUser
  };
  if (r.samplesPerStratum) {
    report['Auto samples (1 pit, 2 water, 3 buildings, 4 crops/trees, 5 dry bare, ' +
           '6 pit look-alikes at buildings)'] = r.samplesPerStratum;
  }
  print('Model summary', report);

  print('Validation on blocks the model never trained on:');
  if (hasUserLabels) {
    printThresholdTable('Against YOUR points (real accuracy)', r.validUser);
  } else {
    print('Add `pits` / `nonPits` points to get a real accuracy estimate.');
  }
  if (useAuto) {
    printThresholdTable('Against the automatic rules (agreement only)', r.validAuto);
  }
  print('Pick CONFIG.probabilityThreshold from the table: higher = fewer false alarms, ' +
        'lower = fewer missed pits.');

  var rows = Object.keys(r.importance).map(function (k) {
    return [k, r.importance[k]];
  }).sort(function (a, b) {
    return b[1] - a[1];
  }).slice(0, 15);
  print(ui.Chart([['Feature', 'Importance']].concat(rows), 'BarChart', {
    title: 'Top 15 features (Random Forest importance)',
    legend: {position: 'none'},
    colors: ['#d95f02']
  }));

  Map.addLayer(pitProbability.updateMask(pitProbability.gt(0.3)),
    {min: 0.3, max: 1, palette: PROB_PALETTE}, 'Pit probability (AI, before building filter)', false);
  Map.addLayer(pitProbability.gte(0.35).and(pitProbability.lte(0.65)).selfMask(),
    {palette: ['ffff00']}, 'Model unsure (label points here first)', false);
  Map.addLayer(removedAsBuilding.selfMask(), {palette: [REMOVED_COLOR]},
    'Removed: looks like a building');
  Map.addLayer(pitMask.selfMask(), {palette: [PIT_COLOR]}, 'Pit pixels (zoom 13+ for small pits)');
  Map.addLayer(newPitMask.selfMask(), {palette: [NEW_PIT_COLOR]}, 'New pits (since this time last year)');

  modelReady = true;
  statusLabel.setValue('Model ready. Zoom to level ' + CONFIG.minZoomForOutlines +
    '+ and press the button to outline and count pits.');
});

// --- Click-to-search: embedding similarity ------------------------------------
// Embeddings are unit-length vectors, so a dot product is cosine similarity.
var similarityLayer = null;
Map.onClick(function (coords) {
  if (!similarityToggle.getValue()) {
    return;
  }
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var reference = embeddingsFull.select(EMBEDDING_BANDS).reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: point.buffer(10),
    scale: CONFIG.scale
  }).values(EMBEDDING_BANDS);

  var norm = ee.Number(reference.map(function (v) {
    return ee.Number(v).pow(2);
  }).reduce(ee.Reducer.sum())).sqrt();

  var similarity = embeddings.select(EMBEDDING_BANDS)
    .multiply(ee.Image.constant(reference).rename(EMBEDDING_BANDS))
    .reduce(ee.Reducer.sum())
    .divide(norm)
    .rename('similarity');

  if (similarityLayer) {
    Map.layers().remove(similarityLayer);
  }
  similarityLayer = ui.Map.Layer(
    similarity.updateMask(similarity.gte(CONFIG.similarityMin)),
    {min: CONFIG.similarityMin, max: 1, palette: ['ffffcc', '41b6c4', '0c2c84']},
    'Similar to clicked pixel');
  Map.layers().add(similarityLayer);
});


// =============================================================================
// 7. EXPORTS — every pit in the district (open the Tasks tab and click RUN)
// =============================================================================
var allPits = vectorisePits(region);

Export.table.toDrive({
  collection: allPits,
  description: areaName + '_pits_polygons_' + periodTag,
  folder: CONFIG.exportFolder,
  fileFormat: 'SHP'               // or 'KML' to open the pits in Google Earth
});

Export.table.toDrive({
  collection: allPits,
  description: areaName + '_pits_list_' + periodTag,
  folder: CONFIG.exportFolder,
  fileFormat: 'CSV',
  selectors: ['district', 'latitude', 'longitude', 'area_ha', 'prob', 'new_pit', 'water_frac',
              'built_frac', 'compact', 'maps_link']
});

Export.image.toDrive({
  image: pitProbability.updateMask(confidentBuilt.not()).multiply(100).toByte(),   // 0-100 %
  description: areaName + '_pit_probability_' + periodTag,
  folder: CONFIG.exportFolder,
  region: region,
  scale: CONFIG.scale,
  maxPixels: 1e13
});

// Save the trained model to reuse it on other districts without retraining:
// Export.classifier.toAsset(classifier, 'pit_rf', 'projects/<your-project>/assets/pit_rf');
