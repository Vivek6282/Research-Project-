/**
 * Trackside Coach Dashboard — Live Readings Hook.
 * Keeps what the server adds to each live reading (limit in force, stage, corner),
 * the last 3 seconds of lateral g for the waveform, and the live alert log.
 * Everything starts empty and is cleared when the driver or the watched session changes.
 */

import { useCallback, useEffect, useState } from "react";

export const G_WINDOW_MS = 3000;
export const MAX_G_POINTS = 60;
export const MAX_ALERTS = 50;

export interface GSample {
  t: number;
  g: number;
}

export interface AlertLogEntry {
  id: string;
  zone_label: string | null;
  severity: "amber" | "red";
  g_value: number;
  threshold_applied: number;
  triggered_at: string;
}

type LiveStage = "nominal" | "monitoring" | "intervene";
const STAGES: LiveStage[] = ["nominal", "monitoring", "intervene"];

/** A finite number, or null. */
function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/** A non-empty text, or null. */
function textOrNull(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

export function useLiveReadings(resetKey: unknown) {
  const [currentLimit, setCurrentLimit] = useState<number | null>(null);
  const [currentStage, setCurrentStage] = useState<LiveStage | null>(null);
  const [currentZoneLabel, setCurrentZoneLabel] = useState<string | null>(null);
  const [currentCornerType, setCurrentCornerType] = useState<string | null>(null);
  const [isStraight, setIsStraight] = useState(false);
  const [gWindow, setGWindow] = useState<GSample[]>([]);
  const [alertLog, setAlertLog] = useState<AlertLogEntry[]>([]);

  // Start empty whenever the driver or the watched session changes
  useEffect(() => {
    setCurrentLimit(null);
    setCurrentStage(null);
    setCurrentZoneLabel(null);
    setCurrentCornerType(null);
    setIsStraight(false);
    setGWindow([]);
    setAlertLog([]);
  }, [resetKey]);

  // Take the live fields of one telemetry_reading message
  const applyReading = useCallback((data: any) => {
    setCurrentLimit(numberOrNull(data.threshold));
    setCurrentStage(STAGES.includes(data.stage) ? data.stage : null);
    setCurrentZoneLabel(textOrNull(data.zone_label));
    setCurrentCornerType(textOrNull(data.corner_type));
    setIsStraight(data.zone == null);
    const g = numberOrNull(data.lateral_g);
    if (g === null) return;
    const now = Date.now();
    setGWindow((prev) => [...prev, { t: now, g }].filter((s) => s.t >= now - G_WINDOW_MS).slice(-MAX_G_POINTS));
  }, []);

  // Add one alert_triggered message to the log (newest first, at most 50)
  const applyAlert = useCallback((data: any) => {
    const id = textOrNull(data.id);
    const g = numberOrNull(data.g_value);
    const limit = numberOrNull(data.threshold_applied);
    if (!id || g === null || limit === null || (data.severity !== "amber" && data.severity !== "red")) return;
    const entry: AlertLogEntry = {
      id, zone_label: textOrNull(data.zone_label), severity: data.severity,
      g_value: g, threshold_applied: limit, triggered_at: String(data.triggered_at ?? ""),
    };
    setAlertLog((prev) => [entry, ...prev.filter((a) => a.id !== id)].slice(0, MAX_ALERTS));
  }, []);

  // Empty the local list only (nothing is deleted on the server)
  const clearAlerts = useCallback(() => setAlertLog([]), []);

  return {
    currentLimit, currentStage, currentZoneLabel, currentCornerType, isStraight,
    gWindow, alertLog, applyReading, applyAlert, clearAlerts,
  };
}
