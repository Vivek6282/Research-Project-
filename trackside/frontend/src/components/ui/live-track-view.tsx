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

import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../../lib/api";
import { getTrajectoryStage } from "./signal-strip";
import {
  GpsPoint,
  SvgPoint,
  gpsToSvgPoints,
  buildTrackPath,
  gpsPointToSvg,
  findNearestPointOnPath,
} from "./live-track/geo-utils";
import { TrackFallback } from "./live-track/track-fallback";
import { TrackCanvas } from "./live-track/track-canvas";

interface LiveTrackViewProps {
  trackId: string | null;
  gpsLat: number | null;
  gpsLng: number | null;
  currentG: number | null;
  threshold: number;
}

export function LiveTrackView({
  trackId,
  gpsLat,
  gpsLng,
  currentG,
  threshold,
}: LiveTrackViewProps) {
  const [referenceLine, setReferenceLine] = useState<GpsPoint[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const pathRef = useRef<SVGPathElement>(null);

  // Fetch reference line when trackId changes
  useEffect(() => {
    if (!trackId) {
      setReferenceLine(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(false);

    api
      .get<{ track_id: string; reference_line: GpsPoint[] | null }>(
        `/api/tracks/${trackId}/reference-line/`,
      )
      .then((res) => {
        if (!cancelled) {
          setReferenceLine(res.reference_line);
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

  // Compute SVG data from reference line
  const svgData =
    referenceLine && referenceLine.length >= 2
      ? gpsToSvgPoints(referenceLine)
      : null;

  const trackPathD = svgData ? buildTrackPath(svgData.svgPoints) : "";

  // Compute driver dot position via nearest-point-on-path
  const computeDotPosition = useCallback((): SvgPoint | null => {
    if (!svgData || gpsLat == null || gpsLng == null || !pathRef.current) {
      return null;
    }

    const driverSvg = gpsPointToSvg(
      gpsLat,
      gpsLng,
      svgData.minLat,
      svgData.maxLat,
      svgData.minLng,
      svgData.maxLng,
    );

    return findNearestPointOnPath(pathRef.current, driverSvg.x, driverSvg.y);
  }, [svgData, gpsLat, gpsLng]);

  const dotPosition = computeDotPosition();

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
        pathRef={pathRef as any}
        svgData={svgData}
        dotPosition={dotPosition}
        stageColor={stageDetails.color}
      />
    </div>
  );
}
