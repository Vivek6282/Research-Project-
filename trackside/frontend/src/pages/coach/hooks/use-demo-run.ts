/**
 * Trackside Coach — talks to the demo control endpoints: availability, live status, start and stop.
 * The Play and Stop buttons exist only when the build switch (VITE_ENABLE_DEMO_TOOLS) is on AND the
 * server says demo tools are on and not in production.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";

export type DemoAvailability = "checking" | "available" | "off" | "production";
export type DemoState = "idle" | "running" | "finished" | "stopped" | "failed";

export interface DemoRunFacts {
  session_id: string;
  driver_id: string;
  driver_name: string;
  track_id: string;
  track_name: string;
  laps: number;
  pace: string;
  pace_applied: boolean;
  built_in: boolean;
  limits?: Record<string, number>;
  limits_custom?: boolean;
}

export interface DemoStatus {
  running: boolean;
  state: DemoState;
  laps: number | null;
  current_lap: number | null;
  bridge_connected: boolean | null;
  port_hint: string | null;
  last_lines: string[];
  error: string | null;
  limits?: Record<string, number> | null;
  limits_custom?: boolean | null;
  run: DemoRunFacts | null;
}

export interface DemoStartBody {
  track_id: string;
  driver_id: string;
  laps: number;
  pace: string;
}

const POLL_MS = 2000;

/** True when this build was made with the demo switch on. */
export function demoSwitchIsOn(): boolean {
  return import.meta.env.VITE_ENABLE_DEMO_TOOLS === "true";
}

/** Holds the demo status and the start/stop actions for the Maps & Demo tab. */
export function useDemoRun(enabled: boolean) {
  const [availability, setAvailability] = useState<DemoAvailability>(enabled ? "checking" : "off");
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const alive = useRef(true);

  /** Read the status once; a 404 means switched off on the server, a 403 means production. */
  const refresh = useCallback(async () => {
    if (!enabled) return;
    try {
      const data = await api.get<DemoStatus>("/api/demo/simulator/status/");
      if (!alive.current) return;
      setAvailability("available");
      setStatus(data);
    } catch (e) {
      if (!alive.current) return;
      const message = e instanceof Error ? e.message : "";
      setAvailability(/production/i.test(message) ? "production" : "off");
      setStatus(null);
    }
  }, [enabled]);

  useEffect(() => {
    alive.current = true;
    if (!enabled) return undefined;
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    return () => {
      alive.current = false;
      clearInterval(timer);
    };
  }, [enabled, refresh]);

  /** Start a run; returns true on success, otherwise keeps the server's message in actionError. */
  const start = useCallback(
    async (body: DemoStartBody) => {
      setActionError(null);
      try {
        await api.post("/api/demo/simulator/start/", body);
        await refresh();
        return true;
      } catch (e) {
        setActionError(e instanceof Error ? e.message : "Could not start the demo.");
        return false;
      }
    },
    [refresh],
  );

  /** Stop the run (safe to press twice). */
  const stop = useCallback(async () => {
    setActionError(null);
    try {
      await api.post("/api/demo/simulator/stop/");
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Could not stop the demo.");
    }
    await refresh();
  }, [refresh]);

  return { availability, status, actionError, start, stop, isRunning: Boolean(status?.running) };
}
