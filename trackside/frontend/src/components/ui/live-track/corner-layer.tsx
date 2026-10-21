/**
 * Trackside Live Track View — corner layer.
 * Draws every active corner as a short highlighted piece of the outline with its
 * name; the corner the kart is in (zone of the latest reading) is brighter.
 */

import { CornerSegment } from "./corner-segments";

interface CornerLayerProps {
  segments: CornerSegment[];
  activeZoneId: string | null;
  activeColor: string;
}

export function CornerLayer({ segments, activeZoneId, activeColor }: CornerLayerProps) {
  return (
    <g data-testid="live-track-corners">
      {segments.map((segment) => {
        const isActive = segment.zoneId === activeZoneId;
        return (
          <g key={segment.zoneId} data-testid={`live-track-corner-${segment.label}`} data-active={isActive}>
            <path
              d={segment.path}
              fill="none"
              stroke={isActive ? activeColor : "#3FA6E0"}
              strokeWidth={isActive ? 6 : 4}
              strokeLinecap="round"
              strokeLinejoin="round"
              opacity={isActive ? 0.95 : 0.55}
            />
            <text
              x={segment.labelAt.x}
              y={segment.labelAt.y}
              fill={isActive ? "#E7EDF3" : "#7C8898"}
              fontSize="10"
              fontWeight={isActive ? "bold" : "normal"}
              fontFamily="monospace"
            >
              {segment.label}
            </text>
          </g>
        );
      })}
    </g>
  );
}
