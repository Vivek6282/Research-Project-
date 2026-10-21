/**
 * Trackside Maps — shared types for the Maps page and the Add map wizard.
 */

export interface LatLng {
  lat: number;
  lng: number;
}

export interface MapZone {
  id: string;
  label: string;
  threshold_g: number;
}

/** A track as returned by /api/tracks/ */
export interface MapTrack {
  id: string;
  name: string;
  source: "manual" | "builtin" | "racechrono_csv" | "vbo";
  is_builtin: boolean;
  is_archived: boolean;
  zones: MapZone[];
  /** The stored GPS outline (custom maps) */
  reference_line?: LatLng[] | null;
  /** The built-in map's drawn-shape outline: a schematic picture, not a survey */
  schematic_outline?: LatLng[] | null;
  is_schematic?: boolean;
}

/** One corner found in an uploaded file (from the import preview) */
export interface CornerPreview {
  number: number;
  suggested_name: string;
  start: LatLng;
  end: LatLng;
  apex: LatLng;
  start_index: number;
  end_index: number;
  apex_index: number;
  tightest_radius_m: number;
  length_m: number;
  safe_speed_kmh_at_default: number;
}

export interface LimitRange {
  min: number;
  max: number;
  default: number;
}

/** What POST /api/tracks/import/preview/ returns */
export interface ImportPreview {
  source: string;
  session_title: string;
  track_name: string;
  rows_total: number;
  rows_used: number;
  rows_rejected: number;
  outline: LatLng[];
  outline_length_m: number;
  corner_radius_m: number;
  limit_range_g: LimitRange;
  corners: CornerPreview[];
}

/** What the user types for each corner (limit is text so half-typed numbers work) */
export interface CornerChoice {
  number: number;
  label: string;
  limit: string;
}

export const SOURCE_LABELS: Record<MapTrack["source"], string> = {
  manual: "Added by hand",
  builtin: "Built-in",
  racechrono_csv: "RaceChrono CSV",
  vbo: "Racelogic VBO",
};
