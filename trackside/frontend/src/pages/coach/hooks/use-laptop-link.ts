/**
 * Trackside Coach — Laptop link hook.
 * Starts a live session for a chosen driver so a laptop's simulator (driving the glove through the
 * bridge) can post its readings to this server, and shows where the link is (waiting, receiving...).
 * The one-time token is kept only in memory: it is gone after a reload.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";
import { singleFlight } from "../../../lib/single-flight";

export const LINK_POLL_MS = 3000;

export interface LinkStart {
  session_id: string;
  driver_id: string;
  driver_name: string;
  backend_url: string;
  device_token: string;
  zones: Record<string, string>;
}

export interface LinkStatus {
  state: "idle" | "waiting" | "receiving" | "quiet";
  driver_id?: string;
  driver_name?: string;
  readings?: number;
  last_reading_seconds_ago?: number | null;
}

/** The lines to paste into trackside/demo/.env on the laptop; tokenText replaces the token (to hide it on screen). */
export function envLines(link: LinkStart, tokenText?: string): string {
  return [
    `BACKEND_URL=${link.backend_url}`,
    `SESSION_ID=${link.session_id}`,
    `DEVICE_TOKEN=${tokenText ?? link.device_token}`,
    `DEMO_ZONES=${JSON.stringify(link.zones)}`,
  ].join("\n");
}

export function useLaptopLink() {
  const [link, setLink] = useState<LinkStart | null>(null);
  const [status, setStatus] = useState<LinkStatus>({ state: "idle" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Ask where the link is (also once on load, to show a link started earlier)
  const refresh = useCallback(async () => {
    try {
      const answer = await api.get<LinkStatus>("/api/laptop-link/status/");
      if (answer && answer.state) setStatus(answer);
    } catch {
      /* the next poll tries again */
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(singleFlight(refresh), LINK_POLL_MS);   // a slow answer is waited for, not stacked on
    return () => clearInterval(timer);
  }, [refresh]);

  // Start a link for this driver and keep the one-time token
  const start = useCallback(async (driverId: string) => {
    setBusy(true);
    setError(null);
    try {
      setLink(await api.post<LinkStart>("/api/laptop-link/start/", { driver_id: driverId }));
      await refresh();
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the link.");
      return false;
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  // End the link (closes the session and drops the token)
  const stop = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/laptop-link/stop/");
      setLink(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not end the link.");
    } finally {
      setBusy(false);
    }
  }, [refresh]);

  return { link, status, error, busy, start, stop };
}
