/**
 * Trackside Live Track View — Path Progress Helpers.
 *
 * Describes a position on the track as "progress": a number from 0.0 (the
 * start/finish line) to 1.0 (back at the start/finish line after one lap).
 * Working in progress instead of raw x/y lets the marker glide along the
 * exact curves of the track instead of cutting straight across corners.
 */

import { SvgPoint } from "./geo-utils";

/** How many evenly spaced points we test first when looking for the nearest spot. */
const COARSE_SAMPLE_COUNT = 200;
/** How many extra points we test around the best coarse spot to sharpen the answer. */
const FINE_SAMPLE_COUNT = 20;
/** A backwards step smaller than this (a share of one lap) is treated as GPS noise. */
export const BACKWARD_NOISE_LIMIT = 0.02;

/** Keep any number inside 0.0 – 1.0 by wrapping it around the lap (1.02 becomes 0.02). */
export function wrapProgress(value: number): number {
  return ((value % 1) + 1) % 1;
}

/** Blend between two numbers; ratio 0 gives "from", ratio 1 gives "to". */
export function interpolate(from: number, to: number, ratio: number): number {
  return from + (to - from) * ratio;
}

/**
 * Decide where the marker should glide to next.
 *
 * "currentProgress" is the marker's running (unwrapped) position, so it can be
 * above 1 after crossing the line. The result is also unwrapped, and it always
 * takes the short way round: going from 0.99 to 0.01 moves forward by 0.02
 * across the start/finish line instead of rewinding the whole lap.
 */
export function resolveNextProgress(
  currentProgress: number,
  newProgress: number,
): number {
  let difference = newProgress - wrapProgress(currentProgress);

  if (difference < -0.5) difference += 1; // crossed the line going forward
  else if (difference > 0.5) difference -= 1; // jittered back over the line

  // Tiny backwards steps are GPS noise, so the marker stays where it is.
  if (difference < 0 && difference > -BACKWARD_NOISE_LIMIT) difference = 0;

  return currentProgress + difference;
}

/** True when the browser can measure SVG paths (older test environments cannot). */
function canMeasurePath(pathElement: SVGPathElement): boolean {
  return typeof pathElement.getTotalLength === "function";
}

/** Find the x/y point on the path at a given progress (0.0 – 1.0). */
export function pointAtProgress(
  pathElement: SVGPathElement,
  progress: number,
): SvgPoint {
  const totalLength = pathElement.getTotalLength();
  const point = pathElement.getPointAtLength(wrapProgress(progress) * totalLength);
  return { x: point.x, y: point.y };
}

/** Distance squared between the path at a progress value and a target point. */
function distanceSquaredAt(
  pathElement: SVGPathElement,
  progress: number,
  targetX: number,
  targetY: number,
): number {
  const point = pointAtProgress(pathElement, progress);
  return (point.x - targetX) ** 2 + (point.y - targetY) ** 2;
}

/**
 * Find how far round the lap the closest point on the track is to (x, y).
 * First a coarse scan, then a finer scan around the best spot so the result
 * is precise enough to animate smoothly. Returns null if the path is empty.
 */
export function findNearestProgressOnPath(
  pathElement: SVGPathElement,
  targetX: number,
  targetY: number,
): number | null {
  if (!canMeasurePath(pathElement) || pathElement.getTotalLength() <= 0) {
    return null;
  }

  let bestProgress = 0;
  let bestDistance = Infinity;
  for (let step = 0; step <= COARSE_SAMPLE_COUNT; step++) {
    const progress = step / COARSE_SAMPLE_COUNT;
    const distance = distanceSquaredAt(pathElement, progress, targetX, targetY);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestProgress = progress;
    }
  }

  const coarseStep = 1 / COARSE_SAMPLE_COUNT;
  const fineStart = bestProgress - coarseStep;
  for (let step = 0; step <= FINE_SAMPLE_COUNT; step++) {
    const progress = fineStart + (2 * coarseStep * step) / FINE_SAMPLE_COUNT;
    const distance = distanceSquaredAt(pathElement, progress, targetX, targetY);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestProgress = progress;
    }
  }

  return wrapProgress(bestProgress);
}
