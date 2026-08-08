/**
 * Trackside — Simulated Live Data Hook
 *
 * Generates random walk data that simulates real-time telemetry feeds.
 * Used across dashboards for speed, heart rate, SpO2, etc. until
 * real IoT hardware is connected.
 */

import { useState, useEffect, useRef } from "react";

interface DataPoint {
  t: number;
  v: number;
}

/**
 * Creates a series of data points that drift randomly within [min, max].
 * Updates at the given interval, keeping a sliding window of `points` items.
 */
export function useLiveSeries(
  min: number,
  max: number,
  points: number = 20,
  intervalMs: number = 1400
): DataPoint[] {
  const [data, setData] = useState<DataPoint[]>(() =>
    Array.from({ length: points }, (_, i) => ({
      t: i,
      v: Math.round((min + max) / 2),
    }))
  );
  const currentValue = useRef((min + max) / 2);

  useEffect(() => {
    const id = setInterval(() => {
      const drift = (Math.random() - 0.5) * (max - min) * 0.18;
      currentValue.current = Math.max(
        min,
        Math.min(max, currentValue.current + drift)
      );
      setData((prev) => [
        ...prev.slice(1),
        { t: prev[prev.length - 1].t + 1, v: Math.round(currentValue.current) },
      ]);
    }, intervalMs);

    return () => clearInterval(id);
  }, [min, max, intervalMs]);

  return data;
}
