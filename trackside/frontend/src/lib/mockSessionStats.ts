/**
 * Trackside — Mock Session Stats Isolation
 *
 * Provides isolated placeholder values for session metrics (kart, duration, laps, best_lap, max_g)
 * when real Telemetry/Alert aggregation fields are not yet available on the backend Session model.
 *
 * TODO(real-data): compute from Telemetry/Alert aggregation, see fix prompt for SessionSerializer.
 * Once SessionSerializer supplies real values for kart, duration, laps, best_lap, and max_g,
 * this helper module can be deleted and replaced with direct API fields.
 */

export interface MockSessionStats {
  kart: string;
  duration: string;
  laps: number;
  bestLap: string;
  maxG: string;
  kartIsSimulated: boolean;
  durationIsSimulated: boolean;
  bestLapIsSimulated: boolean;
  maxGIsSimulated: boolean;
}

export function getMockSessionStats(session: any): MockSessionStats {
  const hasRealKart = typeof session?.kart === "string" && session.kart.length > 0;
  const hasRealDuration = typeof session?.duration === "string" && session.duration.length > 0;
  const hasRealLaps = typeof session?.laps === "number";
  const hasRealBestLap = typeof session?.best_lap === "string" && session.best_lap.length > 0;
  const hasRealMaxG = typeof session?.max_g === "string" && session.max_g.length > 0;

  return {
    kart: hasRealKart ? session.kart : `#${(session?.id ? session.id.charCodeAt(0) % 20 : 12) + 1}`,
    duration: hasRealDuration ? session.duration : (session?.ended_at ? "38 min" : "Active / 42 min"),
    laps: hasRealLaps ? session.laps : 24,
    bestLap: hasRealBestLap ? session.best_lap : "1:23.104",
    maxG: hasRealMaxG ? session.max_g : "1.42g",
    kartIsSimulated: !hasRealKart,
    durationIsSimulated: !hasRealDuration,
    bestLapIsSimulated: !hasRealBestLap,
    maxGIsSimulated: !hasRealMaxG,
  };
}
