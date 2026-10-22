/**
 * Trackside — Corner deltas hook.
 * Reads GET /api/sessions/<id>/corner-deltas/ for one session. It reloads when the
 * session or the lap number changes, and every 5 seconds while the session is live.
 */

import { useEffect, useState } from "react";
import { api } from "./api";

export const CORNER_DELTAS_REFRESH_MS = 5000;

export interface CornerDeltaLap {
  lap_number: number;
  time_s: number;
  delta_s: number | null;
  completed: boolean;
}

export interface CornerDelta {
  zone_id: string;
  label: string;
  best_s: number | null;
  last_lap_s: number | null;
  last_lap_delta_s: number | null;
  laps: CornerDeltaLap[];
}

/** Corner times of a session; corners stays empty until the first answer arrives. */
export function useCornerDeltas(sessionId: string | null, lapNumber: number | null, isLive: boolean) {
  const [corners, setCorners] = useState<CornerDelta[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setCorners([]);
    setFailed(false);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    const load = () => {
      api
        .get<{ corners: CornerDelta[] }>(`/api/sessions/${sessionId}/corner-deltas/`)
        .then((res) => {
          if (cancelled) return;
          setCorners(Array.isArray(res.corners) ? res.corners : []);
          setFailed(false);
        })
        .catch(() => {
          if (!cancelled) setFailed(true);
        });
    };
    load();
    const timer = isLive ? setInterval(load, CORNER_DELTAS_REFRESH_MS) : null;
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
  }, [sessionId, lapNumber, isLive]);

  return { corners, failed };
}

/** Seconds as "1.234 s", or a dash when there is no value. */
export function formatSeconds(value: number | null): string {
  return value === null || value === undefined ? "—" : `${value.toFixed(3)} s`;
}

/** A delta as "+0.120" or "-0.050", or a dash when there is no value. */
export function formatDelta(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(3)}`;
}
