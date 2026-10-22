/**
 * Trackside Coach Dashboard — Shared Types and Interfaces.
 */

export interface DriverProfile {
  id: string;
  pos: number;
  kart: string;
  name: string;
  driverCode?: string | null;
  lapTime: string;
  session: string;
  gap: string;
  baseSpeed: number;
  baseHr: number;
  baseSpo2: number;
  baseBreathing: number;
  stressIndex: number;
  hydration: number;
  status: string;
  statusColor: string;
  alerts: number;
  customThreshold?: number | null;
  inPit?: boolean;
}

export interface SessionNote {
  id: string;
  timestamp: string;
  driverName: string;
  zone: string;
  lap: string;
  text: string;
}

export interface HistoricalSession {
  id: string;
  rawId?: string;
  driver: string;
  driverCode?: string | null;
  kart: string;
  date: string;
  duration: string;
  mode: string;
  laps: number | string;
  bestLap: string;
  maxG: string;
  alerts: number;
  isDemo?: boolean;
}

export interface TrackZone {
  id: string;
  label: string;
  corner_type?: string;
  threshold_g?: number;
  min_threshold_g?: number;
}

export interface RosterStatusItem {
  current_g: number | null;
  active_threshold: number | null;
  stage: string;
  live?: boolean;
  session_state?: string;
}
