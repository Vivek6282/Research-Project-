/**
 * Trackside Live Track View — SVG Track Canvas Component.
 * Draws the surveyed track reference line, grid guidelines, start/finish line,
 * and positions the active car marker.
 */

import { RefObject } from "react";
import { NormalizedSvgData, VIEW_WIDTH, VIEW_HEIGHT } from "./geo-utils";
import { AnimatedCarMarker } from "./animated-car-marker";
import { ProgressSample } from "./use-smooth-marker";
import { CornerLayer } from "./corner-layer";
import { CornerSegment } from "./corner-segments";

interface TrackCanvasProps {
  trackPathD: string;
  pathRef: RefObject<SVGPathElement | null>;
  svgData: NormalizedSvgData | null;
  carSample: ProgressSample | null;
  stageColor: string;
  cornerSegments?: CornerSegment[];
  activeZoneId?: string | null;
}

export function TrackCanvas({
  trackPathD,
  pathRef,
  svgData,
  carSample,
  stageColor,
  cornerSegments = [],
  activeZoneId = null,
}: TrackCanvasProps) {
  return (
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

        {/* Corners: short highlighted pieces of the outline with their names */}
        <CornerLayer segments={cornerSegments} activeZoneId={activeZoneId} activeColor={stageColor} />

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

        {/* Driver dot — glides along the path toward the latest GPS reading */}
        <AnimatedCarMarker pathRef={pathRef} sample={carSample} stageColor={stageColor} />
      </svg>
    </div>
  );
}
