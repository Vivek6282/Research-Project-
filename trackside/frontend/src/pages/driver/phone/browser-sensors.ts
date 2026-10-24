/**
 * Trackside phone page — the browser's motion sensor, GPS and screen wake lock.
 * Motion and location need HTTPS (or localhost); iPhones also ask for motion permission after a tap.
 */

import type { Vec3 } from "../../../lib/phone-sensors/vector";

export interface MotionReading {
  t: number;
  accel: Vec3;
  rotation: Vec3;
}

export interface GpsFix {
  t: number;
  lat: number;
  lng: number;
  speedMs: number | null;
  accuracyM: number | null;
}

type MotionPermission = { requestPermission?: () => Promise<"granted" | "denied"> };

/** Ask for motion permission where the browser needs it (iOS); true when readings may start. */
export async function requestMotionPermission(): Promise<boolean> {
  const motion = (window as unknown as { DeviceMotionEvent?: MotionPermission }).DeviceMotionEvent;
  if (!motion) return false;
  if (typeof motion.requestPermission === "function") return (await motion.requestPermission()) === "granted";
  return true;
}

/** Start motion readings (acceleration with gravity, rotation in degrees per second); returns the stop function. */
export function listenToMotion(onReading: (reading: MotionReading) => void): () => void {
  const handler = (event: DeviceMotionEvent) => {
    const a = event.accelerationIncludingGravity;
    const r = event.rotationRate;
    if (!a || a.x === null || a.y === null || a.z === null) return;
    // rotationRate: beta is about x, gamma about y, alpha about z
    onReading({ t: performance.now(), accel: [a.x, a.y, a.z], rotation: [r?.beta ?? 0, r?.gamma ?? 0, r?.alpha ?? 0] });
  };
  window.addEventListener("devicemotion", handler);
  return () => window.removeEventListener("devicemotion", handler);
}

/** Start high-accuracy GPS; returns the stop function. */
export function watchGps(onFix: (fix: GpsFix) => void, onError: (message: string) => void): () => void {
  if (!("geolocation" in navigator)) {
    onError("This browser has no GPS access.");
    return () => undefined;
  }
  const id = navigator.geolocation.watchPosition(
    (position) => onFix({
      t: performance.now(), lat: position.coords.latitude, lng: position.coords.longitude,
      speedMs: position.coords.speed, accuracyM: position.coords.accuracy,
    }),
    (error) => onError(error.code === error.PERMISSION_DENIED ? "Location permission was refused." : "No GPS signal yet."),
    { enableHighAccuracy: true, maximumAge: 0, timeout: 15_000 },
  );
  return () => navigator.geolocation.clearWatch(id);
}

type WakeLockSentinel = { release: () => Promise<void> };

/** Keep the screen on while the run lasts (asked again when the page comes back); returns the release function. */
export function keepScreenOn(): () => void {
  const nav = navigator as Navigator & { wakeLock?: { request: (type: "screen") => Promise<WakeLockSentinel> } };
  let sentinel: WakeLockSentinel | null = null;
  const request = () => nav.wakeLock?.request("screen").then((s) => (sentinel = s)).catch(() => undefined);
  const onVisible = () => document.visibilityState === "visible" && request();
  request();
  document.addEventListener("visibilitychange", onVisible);
  return () => {
    document.removeEventListener("visibilitychange", onVisible);
    sentinel?.release().catch(() => undefined);
  };
}
