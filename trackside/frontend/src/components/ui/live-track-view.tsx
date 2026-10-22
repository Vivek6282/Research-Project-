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

import { useState, useEffect, useRef, useMemo } from "react";
import { api } from "../../lib/api";
import { getTrajectoryStage } from "./signal-strip";
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

interface LiveTrackViewProps {
  trackId: string | null;
  gpsLat: number | null;
  gpsLng: number | null;
  currentG: number | null;
  threshold: number;
  zoneId?: string | null;
}

export function LiveTrackView({
  trackId,
  gpsLat,
  gpsLng,
  currentG,
  threshold,
  zoneId = null,
}: LiveTrackViewProps) {
  const [referenceLine, setReferenceLine] = useState<GpsPoint[] | null>(null);
  const [isSchematic, setIsSchematic] = useState(false);
  const [corners, setCorners] = useState<TrackCorner[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [carSample, setCarSample] = useState<ProgressSample | null>(null);
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
  const stageDetails = getTrajectoryStage(currentG ?? 0, threshold);

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

      {/* SVG Track Map */}
      <TrackCanvas
        trackPathD={trackPathD}
        pathRef={pathRef}
        svgData={svgData}
        carSample={carSample}
        stageColor={stageDetails.color}
        cornerSegments={cornerSegments}
        activeZoneId={zoneId}
      />
    </div>
  );
}
