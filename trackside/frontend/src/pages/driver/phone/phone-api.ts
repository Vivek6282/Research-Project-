/**
 * Trackside phone page — the server calls: find the driver's real-time session, its track outline,
 * save the calibration, and turn an upload answer into what the queue should do.
 */

import { api, ApiError } from "../../../lib/api";
import type { LatLng } from "../../../lib/phone-sensors/track-follower";
import type { QueuedReading, SendResult } from "../../../lib/phone-sensors/upload-queue";
import type { Vec3 } from "../../../lib/phone-sensors/vector";

export interface PhoneSession {
  id: string;
  track: string;
  track_name: string | null;
  started_at: string;
  ended_at: string | null;
  data_source?: string;
}

/** The driver's newest running real-time session, or null. */
export async function findRealTimeSession(): Promise<PhoneSession | null> {
  const body = await api.get<PhoneSession[] | { results?: PhoneSession[] }>("/api/sessions/");
  const sessions = Array.isArray(body) ? body : body.results ?? [];
  const open = sessions.filter((s) => s.data_source === "real_time" && !s.ended_at);
  open.sort((a, b) => b.started_at.localeCompare(a.started_at));
  return open[0] ?? null;
}

/** The track's GPS outline, or null for a map without one. */
export async function loadOutline(trackId: string): Promise<LatLng[] | null> {
  const body = await api.get<{ reference_line: LatLng[] | null; is_schematic: boolean }>(`/api/tracks/${trackId}/reference-line/`);
  if (body.is_schematic || !Array.isArray(body.reference_line) || body.reference_line.length < 3) return null;
  return body.reference_line;
}

/** Save the calibration directions and any warnings for the session. */
export async function saveCalibration(sessionId: string, body: { gravity?: Vec3; forward?: Vec3; flags?: string[] }) {
  await api.put(`/api/sessions/${sessionId}/phone-calibration/`, body);
}

/** What an upload's answer means for the queue: sent, try later, drop the batch, or stop sending. */
export function sendResultFromError(error: unknown): SendResult {
  if (error instanceof ApiError) {
    if (error.status === 400) return { kind: "reject" };
    if (error.status === 403 || error.status === 409 || error.status === 404) return { kind: "stop", message: error.message };
  }
  return { kind: "retry" };
}

/** Send one batch of readings. */
export async function sendReadings(sessionId: string, batch: QueuedReading[]): Promise<SendResult> {
  try {
    await api.post(`/api/sessions/${sessionId}/telemetry/`, batch);
    return { kind: "ok" };
  } catch (error) {
    return sendResultFromError(error);
  }
}
