/**
 * Trackside Coach — real-time (phone) sessions: list the running ones, start one, finish one (Phase 2.1).
 * The server checks the driver, the map (it needs a GPS outline) and who may do it.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";
import type { MapTrack } from "../../maps/types";

export interface RealTimeSession {
  id: string;
  driver: string;
  driver_name: string | null;
  track_name: string | null;
  started_at: string;
  ended_at: string | null;
  data_source?: string;
  sensor_flags?: string[];
}

type ListBody<T> = T[] | { results?: T[] };
const rows = <T,>(body: ListBody<T>): T[] => (Array.isArray(body) ? body : body.results ?? []);
const REFRESH_MS = 10_000;

/** Running real-time sessions and the GPS maps one can be started on. */
export function useRealTimeSessions() {
  const [sessions, setSessions] = useState<RealTimeSession[]>([]);
  const [maps, setMaps] = useState<MapTrack[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  /** Reload the running real-time sessions. */
  const refresh = useCallback(async () => {
    try {
      const body = await api.get<ListBody<RealTimeSession>>("/api/sessions/");
      setSessions(rows(body).filter((s) => s.data_source === "real_time" && !s.ended_at));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load the sessions.");
    }
  }, []);

  useEffect(() => {
    refresh();
    api.get<ListBody<MapTrack>>("/api/tracks/")
      .then((body) => setMaps(rows(body).filter((m) => !m.is_builtin && !m.is_archived && (m.reference_line?.length ?? 0) >= 50)))
      .catch(() => setMaps([]));
    const timer = window.setInterval(refresh, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  /** Start a real-time session for the driver on the map; true when it worked. */
  const start = useCallback(async (driverId: string, trackId: string) => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/sessions/", { driver: driverId, track: trackId, started_at: new Date().toISOString(), data_source: "real_time" });
      await refresh();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the session.");
      return false;
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  /** Finish a running session. */
  const finish = useCallback(async (sessionId: string) => {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/api/sessions/${sessionId}/finish/`);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not finish the session.");
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  return { sessions, maps, error, busy, start, finish };
}
