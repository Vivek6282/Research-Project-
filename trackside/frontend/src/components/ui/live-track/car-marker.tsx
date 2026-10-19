/**
 * Trackside Live Track View — Car Marker Component.
 * Displays the car's current position on the track with glowing animated pulses
 * colored by trajectory severity stage (Nominal, Monitoring, Intervene).
 */

import { SvgPoint } from "./geo-utils";

interface CarMarkerProps {
  position: SvgPoint;
  stageColor: string;
}

export function CarMarker({ position, stageColor }: CarMarkerProps) {
  return (
    <>
      {/* Outer animated pulse glow */}
      <circle
        cx={position.x}
        cy={position.y}
        r="14"
        fill={stageColor}
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
        cx={position.x}
        cy={position.y}
        r="8"
        fill={stageColor}
        opacity="0.25"
      />

      {/* Core marker dot */}
      <circle
        data-testid="driver-dot"
        cx={position.x}
        cy={position.y}
        r="5"
        fill={stageColor}
        stroke="#0A0E13"
        strokeWidth="1.5"
        style={{
          filter: `drop-shadow(0 0 6px ${stageColor})`,
          transition: "cx 200ms ease, cy 200ms ease, fill 150ms ease",
        }}
      />
    </>
  );
}
