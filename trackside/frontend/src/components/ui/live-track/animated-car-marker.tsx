/**
 * Trackside Live Track View — Animated Car Marker.
 *
 * Wraps CarMarker so only this small piece re-renders every animation frame;
 * the rest of the track view stays untouched.
 */

import { RefObject } from "react";
import { CarMarker } from "./car-marker";
import { ProgressSample, useSmoothMarker } from "./use-smooth-marker";

interface AnimatedCarMarkerProps {
  pathRef: RefObject<SVGPathElement | null>;
  sample: ProgressSample | null;
  stageColor: string;
}

export function AnimatedCarMarker({ pathRef, sample, stageColor }: AnimatedCarMarkerProps) {
  const position = useSmoothMarker(pathRef, sample);
  if (!position) return null;
  return <CarMarker position={position} stageColor={stageColor} />;
}
