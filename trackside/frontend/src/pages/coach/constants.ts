/**
 * Trackside Coach Dashboard — Constants & Seed Fallback Data.
 */

import { DriverProfile, HistoricalSession } from "./types";

export const DEFAULT_SPRINT_FLOOR = 1.0;
export const DEFAULT_SPRINT_CEILING = 1.5;

export const INITIAL_DRIVERS: DriverProfile[] = [
  { pos: 1, kart: "12", name: "Lucas Vance", lapTime: "1:24.312", session: "Race Sim 3", gap: "---", baseSpeed: 88, baseHr: 154, baseSpo2: 98, baseBreathing: 24, stressIndex: 0.62, hydration: 90, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_CEILING },
  { pos: 2, kart: "7", name: "Lena Hartmann", lapTime: "1:24.688", session: "Qualifying 2", gap: "+0.376", baseSpeed: 84, baseHr: 162, baseSpo2: 97, baseBreathing: 26, stressIndex: 0.74, hydration: 85, status: "ELEVATED STRESS", statusColor: "#F2A93B", alerts: 2, customThreshold: 1.10 },
  { pos: 3, kart: "3", name: "Kai Nakamura", lapTime: "1:25.902", session: "Practice 1", gap: "+1.590", baseSpeed: 80, baseHr: 148, baseSpo2: 99, baseBreathing: 21, stressIndex: 0.45, hydration: 92, status: "OPTIMAL", statusColor: "#33D17E", alerts: 1, customThreshold: 1.05 },
  { pos: 4, kart: "18", name: "Marcus Brody", lapTime: "1:26.114", session: "Race Sim 3", gap: "+1.802", baseSpeed: 78, baseHr: 171, baseSpo2: 96, baseBreathing: 28, stressIndex: 0.81, hydration: 78, status: "HIGH FATIGUE", statusColor: "#E5473C", alerts: 4, customThreshold: DEFAULT_SPRINT_CEILING, inPit: true },
  { pos: 5, kart: "5", name: "Ethan Cole", lapTime: "1:26.517", session: "Practice 2", gap: "+2.205", baseSpeed: 76, baseHr: 158, baseSpo2: 97, baseBreathing: 23, stressIndex: 0.58, hydration: 88, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_FLOOR },
];

export const INITIAL_HISTORICAL_SESSIONS: HistoricalSession[] = [
  { id: "SESS-1092", driver: "Marco Ferretti", kart: "#12", date: "2026-08-08", duration: "42 min", mode: "Performance", laps: 28, bestLap: "1:23.104", maxG: "1.42g", alerts: 3 },
  { id: "SESS-1091", driver: "Lena Hartmann", kart: "#07", date: "2026-08-08", duration: "38 min", mode: "Performance", laps: 24, bestLap: "1:24.688", maxG: "1.38g", alerts: 5 },
  { id: "SESS-1090", driver: "Kai Nakamura", kart: "#03", date: "2026-08-07", duration: "45 min", mode: "Safety", laps: 30, bestLap: "1:25.902", maxG: "1.18g", alerts: 1 },
  { id: "SESS-1089", driver: "Ethan Cole", kart: "#05", date: "2026-08-07", duration: "30 min", mode: "Performance", laps: 18, bestLap: "1:26.517", maxG: "1.52g", alerts: 8 },
];
