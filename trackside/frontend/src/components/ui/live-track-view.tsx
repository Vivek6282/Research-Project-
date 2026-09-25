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

/* ─── Types ───────────────────────────────────────────────────────── */

interface GpsPoint {
  lat: number;
  lng: number;
}

interface SvgPoint {
  x: number;
  y: number;
}

interface LiveTrackViewProps {
  trackId: string | null;
  gpsLat: number | null;
  gpsLng: number | null;
  currentG: number;
  threshold: number;
}

/* ─── Constants ───────────────────────────────────────────────────── */

const VIEW_WIDTH = 600;
const VIEW_HEIGHT = 300;
const PADDING_RATIO = 0.10; // 10% padding on each side
const NEAREST_POINT_STEPS = 200; // sample count for getPointAtLength search

/* ─── Helpers ─────────────────────────────────────────────────────── */

/**
 * Convert an array of GPS {lat, lng} points to SVG viewBox coordinates.
 * Normalizes against the survey's min/max bounds with padding.
 * Y-axis is inverted (latitude increases upward, SVG Y increases downward).
 */
function gpsToSvgPoints(gpsPoints: GpsPoint[]): {
  svgPoints: SvgPoint[];
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
} {
  const lats = gpsPoints.map((p) => p.lat);
  const lngs = gpsPoints.map((p) => p.lng);

  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);

  const latRange = maxLat - minLat || 0.0001; // avoid division by zero
  const lngRange = maxLng - minLng || 0.0001;

  const padX = VIEW_WIDTH * PADDING_RATIO;
  const padY = VIEW_HEIGHT * PADDING_RATIO;
  const drawWidth = VIEW_WIDTH - 2 * padX;
  const drawHeight = VIEW_HEIGHT - 2 * padY;

  const svgPoints: SvgPoint[] = gpsPoints.map((p) => ({
    x: padX + ((p.lng - minLng) / lngRange) * drawWidth,
    y: padY + (1 - (p.lat - minLat) / latRange) * drawHeight, // Y inverted
  }));

  return { svgPoints, minLat, maxLat, minLng, maxLng };
}

/**
 * Build an SVG path 'd' attribute from an array of SVG points.
 */
function buildTrackPath(points: SvgPoint[]): string {
  if (points.length === 0) return "";
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");
}

/**
 * Convert a single GPS coordinate to SVG space using the same normalization
 * parameters as the track reference line.
 */
function gpsPointToSvg(
  lat: number,
  lng: number,
  minLat: number,
  maxLat: number,
  minLng: number,
  maxLng: number,
): SvgPoint {
  const latRange = maxLat - minLat || 0.0001;
  const lngRange = maxLng - minLng || 0.0001;

  const padX = VIEW_WIDTH * PADDING_RATIO;
  const padY = VIEW_HEIGHT * PADDING_RATIO;
  const drawWidth = VIEW_WIDTH - 2 * padX;
  const drawHeight = VIEW_HEIGHT - 2 * padY;

  return {
    x: padX + ((lng - minLng) / lngRange) * drawWidth,
    y: padY + (1 - (lat - minLat) / latRange) * drawHeight,
  };
}

/**
 * Find the nearest point on an SVG <path> element to a target (x, y) point
 * using getPointAtLength() sampling. Returns the closest path point.
 */
function findNearestPointOnPath(
  pathEl: SVGPathElement,
  targetX: number,
  targetY: number,
): SvgPoint {
  const totalLength = pathEl.getTotalLength();
  let bestDist = Infinity;
  let bestPoint: SvgPoint = { x: 0, y: 0 };

  for (let i = 0; i <= NEAREST_POINT_STEPS; i++) {
    const len = (i / NEAREST_POINT_STEPS) * totalLength;
    const pt = pathEl.getPointAtLength(len);
    const dx = pt.x - targetX;
    const dy = pt.y - targetY;
    const dist = dx * dx + dy * dy; // squared distance (no sqrt needed)
    if (dist < bestDist) {
      bestDist = dist;
      bestPoint = { x: pt.x, y: pt.y };
    }
  }

  return bestPoint;
}

/* ─── Component ───────────────────────────────────────────────────── */

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
      .get<{ track_id: string; reference_line: GpsPoint[] | null }>(`/api/tracks/${trackId}/reference-line/`)
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
  const svgData = referenceLine && referenceLine.length >= 2
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
  const stageDetails = getTrajectoryStage(currentG, threshold);

  /* ─── Fallback: no track selected ─── */
  if (!trackId) {
    return (
      <div
        data-testid="coach-panel-live-track-view"
        className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
      >
        <div className="flex items-center gap-2 mb-3 border-b border-[#232B35]/60 pb-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRACK VIEW
          </span>
        </div>
        <div data-testid="live-track-fallback" className="flex items-center justify-center h-[180px] text-[#7C8898] text-xs">
          No active track selected.
        </div>
      </div>
    );
  }

  /* ─── Fallback: loading ─── */
  if (loading) {
    return (
      <div
        data-testid="coach-panel-live-track-view"
        className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
      >
        <div className="flex items-center gap-2 mb-3 border-b border-[#232B35]/60 pb-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRACK VIEW
          </span>
        </div>
        <div data-testid="live-track-fallback" className="flex items-center justify-center h-[180px] text-[#7C8898] text-xs">
          <span className="animate-pulse">Loading track shape…</span>
        </div>
      </div>
    );
  }

  /* ─── Fallback: error ─── */
  if (error) {
    return (
      <div
        data-testid="coach-panel-live-track-view"
        className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
      >
        <div className="flex items-center gap-2 mb-3 border-b border-[#232B35]/60 pb-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRACK VIEW
          </span>
        </div>
        <div data-testid="live-track-fallback" className="flex items-center justify-center h-[180px] text-[#E5473C] text-xs">
          Failed to load track data.
        </div>
      </div>
    );
  }

  /* ─── Fallback: track not surveyed ─── */
  if (!referenceLine || referenceLine.length < 2) {
    return (
      <div
        data-testid="coach-panel-live-track-view"
        className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
      >
        <div className="flex items-center gap-2 mb-3 border-b border-[#232B35]/60 pb-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
            LIVE TRACK VIEW
          </span>
        </div>
        <div data-testid="live-track-fallback" className="flex flex-col items-center justify-center h-[180px] gap-3">
          {/* Track icon placeholder */}
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
            <circle cx="20" cy="20" r="16" stroke="#232B35" strokeWidth="2" strokeDasharray="4 3" />
            <circle cx="20" cy="20" r="8" stroke="#232B35" strokeWidth="1.5" strokeDasharray="3 2" />
            <circle cx="20" cy="8" r="3" fill="#3A4553" />
          </svg>
          <p className="text-[#7C8898] text-xs text-center leading-relaxed max-w-[320px]">
            Live Track View unavailable — this track hasn't been surveyed yet.
          </p>
          <span className="text-[10px] text-[#3A4553] uppercase tracking-wider">
            Run a survey lap to enable
          </span>
        </div>
      </div>
    );
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
      <div className="relative w-full bg-[#0A0E13] border border-[#232B35] rounded-[2px] overflow-hidden">
        <svg
          data-testid="live-track-svg"
          className="w-full"
          viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
          preserveAspectRatio="xMidYMid meet"
          style={{ height: "220px" }}
        >
          {/* Subtle grid lines */}
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={`h-${ratio}`}
              x1="0"
              y1={VIEW_HEIGHT * ratio}
              x2={VIEW_WIDTH}
              y2={VIEW_HEIGHT * ratio}
              stroke="#232B35"
              strokeWidth="0.5"
              strokeDasharray="4 6"
              opacity="0.3"
            />
          ))}
          {[0.25, 0.5, 0.75].map((ratio) => (
            <line
              key={`v-${ratio}`}
              x1={VIEW_WIDTH * ratio}
              y1="0"
              x2={VIEW_WIDTH * ratio}
              y2={VIEW_HEIGHT}
              stroke="#232B35"
              strokeWidth="0.5"
              strokeDasharray="4 6"
              opacity="0.3"
            />
          ))}

          {/* Track outline (thicker, very dim) */}
          <path
            d={trackPathD}
            fill="none"
            stroke="#3FA6E0"
            strokeWidth="8"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.08"
          />

          {/* Track reference line path */}
          <path
            ref={pathRef}
            data-testid="live-track-path"
            d={trackPathD}
            fill="none"
            stroke="#3FA6E0"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.45"
          />

          {/* Start/Finish marker */}
          {svgData && svgData.svgPoints.length > 0 && (
            <>
              <rect
                x={svgData.svgPoints[0].x - 4}
                y={svgData.svgPoints[0].y - 4}
                width="8"
                height="8"
                rx="1"
                fill="#E7EDF3"
                opacity="0.3"
              />
              <text
                x={svgData.svgPoints[0].x + 8}
                y={svgData.svgPoints[0].y + 3}
                fill="#7C8898"
                fontSize="9"
                fontFamily="monospace"
              >
                S/F
              </text>
            </>
          )}

          {/* Driver dot — positioned at nearest point on path */}
          {dotPosition && (
            <>
              {/* Outer glow */}
              <circle
                cx={dotPosition.x}
                cy={dotPosition.y}
                r="14"
                fill={stageDetails.color}
                opacity="0.12"
              >
                <animate
                  attributeName="r"
                  values="12;18;12"
                  dur="1.8s"
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.15;0.05;0.15"
                  dur="1.8s"
                  repeatCount="indefinite"
                />
              </circle>

              {/* Inner glow */}
              <circle
                cx={dotPosition.x}
                cy={dotPosition.y}
                r="8"
                fill={stageDetails.color}
                opacity="0.25"
              />

              {/* Core dot */}
              <circle
                data-testid="driver-dot"
                cx={dotPosition.x}
                cy={dotPosition.y}
                r="5"
                fill={stageDetails.color}
                stroke="#0A0E13"
                strokeWidth="1.5"
                style={{
                  filter: `drop-shadow(0 0 6px ${stageDetails.color})`,
                  transition: "cx 200ms ease, cy 200ms ease, fill 150ms ease",
                }}
              />
            </>
          )}
        </svg>
      </div>
    </div>
  );
}
