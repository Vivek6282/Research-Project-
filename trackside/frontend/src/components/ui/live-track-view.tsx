/**
 * Trackside — Live Track View Component
 *
 * Renders the active track's surveyed GPS shape as an SVG path and positions
 * a colored dot showing the driver's live location from real GPS telemetry.
 *
 * The dot color is driven by getTrajectoryStage() — the same single source
 * of truth used by the SignalStrip component — ensuring visual consistency
 * across the Coach dashboard.
 *
 * When the track has no reference_line (not yet surveyed), a graceful
 * placeholder state is shown instead of a broken/empty map.
 */

import { lazy, Suspense, useState, useEffect, useRef, useMemo, ReactNode } from "react";
import { api } from "../../lib/api";
import { liveStage } from "./live-stage";
import {
  GpsPoint,
  gpsToSvgPoints,
  buildTrackPath,
  gpsPointToSvg,
} from "./live-track/geo-utils";
import { findNearestProgressOnPath } from "./live-track/path-progress";
import { ProgressSample } from "./live-track/use-smooth-marker";
import { TrackFallback } from "./live-track/track-fallback";
import { TrackCanvas } from "./live-track/track-canvas";
import { TrackCorner, buildCornerSegments } from "./live-track/corner-segments";
import { readMapMode, saveMapMode, type MapMode } from "./live-track/map-mode";

// The real map (and Leaflet with it) is loaded only when a track with real coordinates is shown
const GpsMapCanvas = lazy(() => import("./live-track/gps-map-canvas"));

interface LiveTrackViewProps {
  trackId: string | null;
  gpsLat: number | null;
  gpsLng: number | null;
  currentG: number | null;
  threshold: number | null;
  zoneId?: string | null;
  isStraight?: boolean;
  readouts?: ReactNode;
  children?: ReactNode;
}

export function LiveTrackView({
  trackId,
  gpsLat,
  gpsLng,
  currentG,
  threshold,
  zoneId = null,
  isStraight = false,
  readouts,
  children,
}: LiveTrackViewProps) {
  const [referenceLine, setReferenceLine] = useState<GpsPoint[] | null>(null);
  const [isSchematic, setIsSchematic] = useState(false);
  const [corners, setCorners] = useState<TrackCorner[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [carSample, setCarSample] = useState<ProgressSample | null>(null);
  const [mapMode, setMapMode] = useState<MapMode>(readMapMode);
  const pathRef = useRef<SVGPathElement>(null);

  // Fetch reference line when trackId changes
  useEffect(() => {
    setCarSample(null);
    if (!trackId) {
      setReferenceLine(null);
      setIsSchematic(false);
      setCorners([]);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(false);

    api
      .get<{
        track_id: string;
        reference_line: GpsPoint[] | null;
        is_schematic?: boolean;
        corners?: TrackCorner[];
      }>(
        `/api/tracks/${trackId}/reference-line/`,
      )
      .then((res) => {
        if (!cancelled) {
          setReferenceLine(res.reference_line);
          setIsSchematic(res.is_schematic === true);
          setCorners(res.corners ?? []);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [trackId]);

  // Compute SVG data from reference line (only when the survey itself changes)
  const svgData = useMemo(
    () =>
      referenceLine && referenceLine.length >= 2
        ? gpsToSvgPoints(referenceLine)
        : null,
    [referenceLine],
  );

  const trackPathD = svgData ? buildTrackPath(svgData.svgPoints) : "";
  const cornerSegments = svgData ? buildCornerSegments(corners, svgData) : [];

  // Each new GPS reading becomes a destination (how far round the lap the
  // nearest track point is). The marker then glides there smoothly instead of
  // jumping, see use-smooth-marker.ts.
  useEffect(() => {
    if (!svgData || gpsLat == null || gpsLng == null || !pathRef.current) {
      setCarSample(null);
      return;
    }

    const driverSvg = gpsPointToSvg(
      gpsLat,
      gpsLng,
      svgData.minLat,
      svgData.maxLat,
      svgData.minLng,
      svgData.maxLng,
    );
    const progress = findNearestProgressOnPath(pathRef.current, driverSvg.x, driverSvg.y);
    setCarSample(progress === null ? null : { progress });
  }, [svgData, gpsLat, gpsLng]);

  // Get trajectory stage for dot coloring
  const stageDetails = liveStage(currentG ?? 0, threshold, isStraight);

  /* ─── Fallbacks ─── */
  if (!trackId) {
    return <TrackFallback type="no-track" />;
  }

  if (loading) {
    return <TrackFallback type="loading" />;
  }

  if (error) {
    return <TrackFallback type="error" />;
  }

  if (!referenceLine || referenceLine.length < 2) {
    return <TrackFallback type="unsurveyed" />;
  }

  /* ─── Main render: SVG track with driver dot ─── */
  return (
    <div
      data-testid="coach-panel-live-track-view"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
    >
      {/* Panel Header */}
      <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRACK VIEW
          </span>
          <span className="text-xs text-[#7C8898]">
            {referenceLine.length} survey points
          </span>
          {isSchematic && (
            <span
              data-testid="schematic-tag"
              className="text-[10px] uppercase tracking-wider text-[#E0A93F] border border-[#E0A93F]/40 px-1.5 py-0.5 rounded-[2px]"
            >
              Schematic map
            </span>
          )}
        </div>
        {/* Live stage indicator */}
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ backgroundColor: stageDetails.color }}
          />
          <span
            className="text-[10px] font-bold uppercase tracking-wider"
            style={{ color: stageDetails.color }}
          >
            {stageDetails.label}
          </span>
        </div>
      </div>

      {readouts}

      {/* The track: on a real map when it has real coordinates (and the map view is chosen), otherwise the plain drawing */}
      {!isSchematic && (
        <div className="flex justify-end gap-1 mb-1" role="group" aria-label="Track view">
          {(["map", "plain"] as MapMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              data-testid={`live-view-${mode}`}
              aria-pressed={mapMode === mode}
              onClick={() => { setMapMode(mode); saveMapMode(mode); }}
              className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-[2px] border cursor-pointer"
              style={{ borderColor: mapMode === mode ? "#3FA6E0" : "#232B35", color: mapMode === mode ? "#3FA6E0" : "#7C8898" }}
            >
              {mode === "map" ? "Map" : "Plain"}
            </button>
          ))}
        </div>
      )}
      {!isSchematic && mapMode === "map" ? (
        <Suspense fallback={<div className="h-[300px] flex items-center justify-center text-[10px] font-mono text-[#7C8898] border border-[#232B35]">Loading map…</div>}>
          <GpsMapCanvas
            line={referenceLine}
            corners={corners}
            activeZoneId={zoneId}
            gpsLat={gpsLat}
            gpsLng={gpsLng}
            stageColor={stageDetails.color}
          />
        </Suspense>
      ) : (
        <TrackCanvas
          trackPathD={trackPathD}
          pathRef={pathRef}
          svgData={svgData}
          carSample={carSample}
          stageColor={stageDetails.color}
          cornerSegments={cornerSegments}
          activeZoneId={zoneId}
        />
      )}
      {children}
    </div>
  );
}
