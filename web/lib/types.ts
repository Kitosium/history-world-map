export type Lang = string;
export type Theme = "dark" | "light";
export type TabId = "territories" | "civilizations" | "events";
export type Confidence = "high" | "medium" | "low";
export type Variant = "card" | "sheet";

export interface View {
  lon: number;
  lat: number;
  zoom: number;
}

export interface UserLocation {
  lon: number;
  lat: number;
}

export interface MapSize {
  width: number;
  height: number;
}

export interface Transform {
  scale: number;
  tx: number;
  ty: number;
}

export interface FeatureMetrics {
  area: number;
  cx: number;
  cy: number;
  bbox: [number, number, number, number];
}

export interface LayerToggles {
  labels: boolean;
  borders: boolean;
  graticule: boolean;
}

export type Position = [number, number];
export type PolygonCoordinates = Position[][];
export type MultiPolygonCoordinates = Position[][][];

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: PolygonCoordinates;
}

export interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: MultiPolygonCoordinates;
}

export type GeoGeometry = PolygonGeometry | MultiPolygonGeometry;

export type NamesMap = Record<
  string,
  string | Record<string, string> | Record<string, string[]>
>;

export interface EntityLike {
  id?: string;
  names?: NamesMap | null;
  name_en?: string | null;
  name_vi?: string | null;
  description_en?: string | null;
  description_vi?: string | null;
  descriptions?: Record<string, string> | null;
  type?: string | null;
  from_year?: number | null;
  to_year?: number | null;
  observed_years?: number[] | null;
  observed_year_count?: number | null;
  confidence?: string | null;
  confidence_basis?: string | null;
  boundary_precision?: string | null;
  source_ids?: string[] | null;
  wikidata_id?: string | null;
  [key: string]: unknown;
}

export interface EntityIndex extends EntityLike {
  id: string;
  path: string;
  name_vi: string;
  name_en: string;
  type: string;
  type_category?: string;
  from_year: number;
  from_month?: number | null;
  from_day?: number | null;
  from_precision?: string;
  from_label?: string;
  to_year: number;
  to_month?: number | null;
  to_day?: number | null;
  to_precision?: string;
  to_label?: string;
  status?: string;
  existence_basis?: string;
  is_approximate?: boolean;
  observed_years?: number[];
  observed_year_count?: number;
  confidence?: Confidence;
  confidence_basis?: string;
  boundary_confidence?: Confidence;
  boundary_precision?: string;
  feature_count?: number;
  source_ids?: string[];
  wikidata_id?: string;
  description_vi?: string;
  description_en?: string;
}

export interface YearPoint {
  year: number;
  month?: number | null;
  day?: number | null;
  year_system?: string;
  precision?: string;
  label?: string;
}

export interface Existence {
  from?: YearPoint | null;
  to?: YearPoint | null;
  duration_years?: number;
  status?: string;
  foundation_reason?: string | null;
  dissolution_reason?: string | null;
  basis?: string;
  continuity_asserted?: boolean;
  is_approximate?: boolean;
}

export interface SpatialCoverage {
  observed_years?: number[];
  first_observed_year?: number;
  last_observed_year?: number;
  feature_count?: number;
  boundary_source_ids?: string[];
  boundary_confidence?: Confidence;
  boundary_precision?: string;
  border_precision?: number;
}

export interface BoundaryReference {
  year: number;
  year_system?: string;
  file_path: string;
  source_ids?: string[];
  boundary_confidence?: Confidence;
  boundary_precision?: string;
}

export interface EntityDocument extends EntityLike {
  id: string;
  schema_version?: string;
  type: string;
  wikidata_id?: string;
  names?: NamesMap;
  descriptions?: Record<string, string>;
  existence?: Existence;
  observed_periods?: number[];
  spatial_coverage?: SpatialCoverage;
  confidence?: Confidence;
  confidence_basis?: string;
  source_ids?: string[];
  external_links?: {
    wikipedia?: string;
    wikidata?: string;
  };
  provenance?: Record<string, unknown>;
  boundary_references?: BoundaryReference[];
  last_updated?: string;
  last_verified?: string;
}

export interface GeoFeatureProperties extends EntityLike {
  entity_id?: string;
  name_en?: string;
  name_vi?: string;
  type?: string;
  layer_type?: string;
  border_precision?: number;
  confidence?: Confidence;
  source_ids?: string[];
  wikidata_id?: string;
  valid_year?: number;
  valid_month?: number | null;
  valid_day?: number | null;
  valid_from?: string;
  valid_to?: string;
  precision?: string;
  color_index?: number;
}

export interface GeoFeature {
  type: "Feature";
  id?: string | number;
  properties?: GeoFeatureProperties;
  geometry: GeoGeometry | null;
}

export interface FeatureCollection {
  type: "FeatureCollection" | string;
  features: GeoFeature[];
}

export interface TimelineEntry {
  year: number;
  month?: number | null;
  day?: number | null;
  label_vi: string;
  label_en: string;
  era_vi: string;
  era_en: string;
  feature_count: number;
  entity_count?: number;
  file_path: string;
  valid_from?: string;
  valid_to?: string;
  precision?: string;
  event_name_vi?: string;
  event_name_en?: string;
  confidence_counts?: Record<string, number>;
}

export interface SourceCreator {
  name: string;
  role?: string;
}

export interface SourceRecord {
  id: string;
  title?: string | Record<string, string>;
  title_en?: string;
  title_vi?: string;
  type?: string;
  tier?: string;
  tier_rank?: number;
  creators?: SourceCreator[];
  publication_year?: number;
  publisher?: string;
  edition?: string;
  license?: string;
  urls?: string[];
  coverage?: string;
  last_verified?: string;
  [key: string]: unknown;
}

export interface Catalog {
  timeline: TimelineEntry[];
  entities: EntityIndex[];
  sources: SourceRecord[];
}

export interface UILabels {
  appTitle: string;
  appSubtitle: string;
  searchPlaceholder: string;
  searchPlaceholderCompact: string;
  territories: string;
  civilizations: string;
  events: string;
  loading: string;
  error: string;
  retry: string;
  jumpToYear: string;
  paused: string;
  playing: string;
  dragHint: string;
  play: string;
  pause: string;
  legend: string;
  approximate: string;
  sources: string;
  sourcesShort: string;
  confidence: string;
  period: string;
  observed: string;
  type: string;
  historical: string;
  contemporary: string;
  approximateNote: string;
  boundaryModernNote: string;
  noDescription: string;
  loadingRecord: string;
  wikipedia: string;
  wikidata: string;
  noResults: string;
  eventsTitle: string;
  eventsHint: string;
  close: string;
  resetView: string;
  zoomIn: string;
  zoomOut: string;
  layers: string;
  labels: string;
  borders: string;
  graticule: string;
  theme: string;
  language: string;
  attribution: string;
  regional: string;
  approximateShort: string;
  schematicExtent: string;
  featureCount: string;
  event: string;
  snapshot: string;
  layerNote: string;
  names: string;
  confidenceBasis: string;
  boundary: string;
  boundaryApproximate: string;
  boundaryApproximateShort: string;
  boundaryGeoreferenced: string;
  openSource: string;
  showMore: string;
  showLess: string;
  ancient: string;
  modern: string;
  allSnapshots: string;
  noSelection: string;
  noSelectionHint: string;
  zoomHint: string;
  dataSources: string;
  record: string;
  status: string;
  externalLinks: string;
  confidenceHigh: string;
  confidenceMedium: string;
  confidenceLow: string;
  founded: string;
  dissolved: string;
  stepMode: string;
  step100y: string;
  step10y: string;
  step1y: string;
  stepMonth: string;
  prevStep: string;
  nextStep: string;
  currentLocation: string;
  historicalPeriods: string;
  periodsSuffix: string;
  timeRangePresent: string;
  present: string;
}

export type StepMode = "month" | "1y" | "10y" | "100y";

export type UIDictionary = Record<Lang, UILabels>;
