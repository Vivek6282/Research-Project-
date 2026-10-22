/**
 * Trackside — Smooth Marker Hook Tests
 *
 * Replaces requestAnimationFrame with a hand-driven clock so we can check the
 * marker glides between GPS readings instead of jumping.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSmoothMarker, ProgressSample } from "../live-track/use-smooth-marker";

/** Fake 100-unit straight path so progress 0.5 means x = 50. */
function makeStraightPath(): SVGPathElement {
  return {
    getTotalLength: () => 100,
    getPointAtLength: (length: number) => ({ x: length, y: 0 }),
  } as unknown as SVGPathElement;
}

let currentTime = 0;
let pendingFrame: ((time: number) => void) | null = null;

/** Move the fake clock forward and run the queued animation frame once. */
function advance(milliseconds: number) {
  currentTime += milliseconds;
  const frame = pendingFrame;
  pendingFrame = null;
  act(() => frame?.(currentTime));
}

describe("useSmoothMarker", () => {
  beforeEach(() => {
    currentTime = 0;
    pendingFrame = null;
    vi.spyOn(performance, "now").mockImplementation(() => currentTime);
    vi.stubGlobal("requestAnimationFrame", (callback: (time: number) => void) => {
      pendingFrame = callback;
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", () => {
      pendingFrame = null;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows nothing until a sample arrives", () => {
    const pathRef = { current: makeStraightPath() };
    const { result } = renderHook(() => useSmoothMarker(pathRef, null));
    expect(result.current).toBeNull();
  });

  it("places the marker straight away on the first sample", () => {
    const pathRef = { current: makeStraightPath() };
    const { result } = renderHook(() => useSmoothMarker(pathRef, { progress: 0.2 }));
    expect(result.current?.x).toBeCloseTo(20);
  });

  it("glides through in-between positions instead of jumping", () => {
    const pathRef = { current: makeStraightPath() };
    const { result, rerender } = renderHook(
      ({ sample }: { sample: ProgressSample }) => useSmoothMarker(pathRef, sample),
      { initialProps: { sample: { progress: 0.2 } } },
    );

    currentTime = 1000;
    rerender({ sample: { progress: 0.4 } });

    advance(500); // half way through the one-second glide
    expect(result.current?.x).toBeCloseTo(30, 0);

    advance(500); // glide finished
    expect(result.current?.x).toBeCloseTo(40, 0);
  });

  it("wraps seamlessly across the start/finish line", () => {
    const pathRef = { current: makeStraightPath() };
    const { result, rerender } = renderHook(
      ({ sample }: { sample: ProgressSample }) => useSmoothMarker(pathRef, sample),
      { initialProps: { sample: { progress: 0.98 } } },
    );

    currentTime = 1000;
    rerender({ sample: { progress: 0.02 } }); // short way round: +0.04 of a lap

    advance(250); // 0.98 + 0.01 = 0.99
    expect(result.current?.x).toBeCloseTo(99, 0);

    advance(500); // 0.98 + 0.03 = 1.01, which wraps to 0.01
    expect(result.current?.x).toBeCloseTo(1, 0);
  });

  it("stops requesting frames once it has arrived", () => {
    const pathRef = { current: makeStraightPath() };
    const { rerender } = renderHook(
      ({ sample }: { sample: ProgressSample }) => useSmoothMarker(pathRef, sample),
      { initialProps: { sample: { progress: 0.2 } } },
    );
    currentTime = 1000;
    rerender({ sample: { progress: 0.4 } });
    advance(1000);
    expect(pendingFrame).toBeNull();
  });
});
