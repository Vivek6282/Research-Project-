/**
 * Trackside phone page — React side of a phone run: find the session, start and stop the sensors,
 * tick every 100 ms, send every second, and refresh what the page shows.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { keepScreenOn, listenToMotion, requestMotionPermission, watchGps } from "./browser-sensors";
import { findRealTimeSession, loadOutline, saveCalibration, sendReadings, type PhoneSession } from "./phone-api";
import { PhoneRun, type RunSnapshot } from "./phone-run";

const TICK_MS = 100;
const SEND_MS = 1000;
const SHOW_MS = 250;

/** The page's state: the session, the run's snapshot, and the start/stop/calibrate actions. */
export function usePhoneUnit() {
  const [session, setSession] = useState<PhoneSession | null>(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [snapshot, setSnapshot] = useState<RunSnapshot | null>(null);
  const [pageHidden, setPageHidden] = useState(false);
  const runRef = useRef<PhoneRun | null>(null);
  const stopRef = useRef<(() => void) | null>(null);

  /** Look for the driver's running real-time session. */
  const checkSession = useCallback(async () => {
    setChecking(true);
    setError(null);
    try {
      setSession(await findRealTimeSession());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load your sessions.");
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
    const onVisibility = () => setPageHidden(document.visibilityState === "hidden");
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      stopRef.current?.();
    };
  }, [checkSession]);

  /** Ask for permissions, start sensors and timers, and begin at the "hold still" step. */
  const start = useCallback(async () => {
    if (!session || runRef.current) return;
    setError(null);
    if (!(await requestMotionPermission())) {
      setError("Motion sensor permission was refused, or this browser has no motion sensor.");
      return;
    }
    const outline = await loadOutline(session.track).catch(() => null);
    const run = new PhoneRun(outline, {
      send: (batch) => sendReadings(session.id, batch),
      saveCalibration: (body) => saveCalibration(session.id, body),
      wallClock: () => new Date(),
    });
    runRef.current = run;
    const stopMotion = listenToMotion((reading) => run.onMotion(reading));
    const stopGps = watchGps((fix) => run.onFix(fix), (message) => setError(message));
    const releaseScreen = keepScreenOn();
    const ticker = window.setInterval(() => run.tick(performance.now()), TICK_MS);
    const sender = window.setInterval(() => run.queue.flush(performance.now()), SEND_MS);
    const shower = window.setInterval(() => setSnapshot(run.snapshot()), SHOW_MS);
    stopRef.current = () => {
      [ticker, sender, shower].forEach((id) => window.clearInterval(id));
      stopMotion();
      stopGps();
      releaseScreen();
      run.queue.flush(performance.now() + 60_000);   // one last try for what is still queued
      setSnapshot(run.snapshot());
      stopRef.current = null;
    };
    setRunning(true);
    setSnapshot(run.snapshot());
  }, [session]);

  /** Stop sensors and timers; the run stays on screen so the recording can still be saved. */
  const stop = useCallback(() => {
    stopRef.current?.();
    setRunning(false);
  }, []);

  /** Start (or retry) the "hold still" calibration. */
  const calibrateStill = useCallback(() => runRef.current?.beginStill(performance.now()), []);

  /** Skip the "drive straight" step. */
  const skipForward = useCallback(() => runRef.current?.skipForward(), []);

  /** Download the raw sensor recording of this run as a JSON file. */
  const saveRecording = useCallback(() => {
    const run = runRef.current;
    if (!run) return;
    const blob = new Blob([run.recording.toJson(run.calibration(), session?.track_name ?? "")], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `trackside-phone-recording-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
  }, [session]);

  return { session, checking, error, running, snapshot, pageHidden, checkSession, start, stop, calibrateStill, skipForward, saveRecording };
}
