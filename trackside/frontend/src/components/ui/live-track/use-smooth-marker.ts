/**
 * Trackside Live Track View — Smooth Marker Hook.
 *
 * GPS readings arrive about once a second. If the marker jumped to each new
 * reading it would look like it was teleporting. This hook separates the two
 * jobs: new readings only set a destination, and a requestAnimationFrame loop
 * (about 60 times a second) slides the marker toward it along the track path.
 */

import { RefObject, useCallback, useEffect, useRef, useState } from "react";
import { SvgPoint } from "./geo-utils";
import {
  interpolate,
  pointAtProgress,
  resolveNextProgress,
  wrapProgress,
} from "./path-progress";

/** One new GPS-based destination. A fresh object each time, even for equal progress. */
export interface ProgressSample {
  progress: number;
}

const DEFAULT_GLIDE_MS = 1000;
const MIN_GLIDE_MS = 150;
const MAX_GLIDE_MS = 2000;

interface MotionState {
  from: number;
  to: number;
  current: number;
  startedAt: number;
  glideMs: number;
  lastSampleAt: number | null;
}

function clamp(value: number, low: number, high: number): number {
  return Math.min(high, Math.max(low, value));
}

/** Respect the operating-system "reduce motion" setting by skipping the glide. */
function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Returns the marker's on-screen position, updated every animation frame.
 * Returns null until the first GPS sample arrives (or when there is none).
 */
export function useSmoothMarker(
  pathRef: RefObject<SVGPathElement | null>,
  sample: ProgressSample | null,
): SvgPoint | null {
  const [position, setPosition] = useState<SvgPoint | null>(null);
  const motion = useRef<MotionState>({
    from: 0,
    to: 0,
    current: 0,
    startedAt: 0,
    glideMs: DEFAULT_GLIDE_MS,
    lastSampleAt: null,
  });
  const frameId = useRef<number | null>(null);

  /** One animation frame: move the marker part-way and ask for the next frame. */
  const runFrame = useCallback(
    (now: number) => {
      const state = motion.current;
      const ratio = clamp((now - state.startedAt) / state.glideMs, 0, 1);
      state.current = interpolate(state.from, state.to, ratio);

      if (pathRef.current) {
        setPosition(pointAtProgress(pathRef.current, state.current));
      }

      if (ratio < 1) {
        frameId.current = requestAnimationFrame(runFrame);
      } else {
        // Arrived: fold the running value back into one lap so it never grows.
        state.current = wrapProgress(state.to);
        state.from = state.current;
        state.to = state.current;
        frameId.current = null;
      }
    },
    [pathRef],
  );

  // React to each new GPS-based destination.
  useEffect(() => {
    const state = motion.current;
    const pathElement = pathRef.current;

    if (!sample || !pathElement) {
      state.lastSampleAt = null;
      setPosition(null);
      return;
    }

    const now = performance.now();
    const isFirstSample = state.lastSampleAt === null;

    if (isFirstSample || prefersReducedMotion()) {
      // Nothing to glide from yet: place the marker straight on the spot.
      state.current = sample.progress;
      state.from = sample.progress;
      state.to = sample.progress;
      state.lastSampleAt = now;
      setPosition(pointAtProgress(pathElement, sample.progress));
      return;
    }

    // Glide for as long as the readings are actually spaced apart.
    state.glideMs = clamp(now - (state.lastSampleAt ?? now), MIN_GLIDE_MS, MAX_GLIDE_MS);
    state.lastSampleAt = now;
    state.from = state.current;
    state.to = resolveNextProgress(state.current, sample.progress);
    state.startedAt = now;

    if (frameId.current === null) {
      frameId.current = requestAnimationFrame(runFrame);
    }
  }, [sample, pathRef, runFrame]);

  // Stop the animation loop when the component goes away.
  useEffect(() => {
    return () => {
      if (frameId.current !== null) {
        cancelAnimationFrame(frameId.current);
        frameId.current = null;
      }
    };
  }, []);

  return position;
}
