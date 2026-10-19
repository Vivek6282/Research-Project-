/**
 * Trackside Coach Dashboard — Shared Types and Interfaces.
 */

export interface DriverProfile {
  pos: number;
  kart: string;
  name: string;
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
  customThreshold: number;
  inPit?: boolean;
}

export interface SessionNote {
  id: string;
  timestamp: string;
  driverName: string;
  kart: string;
  zone: string;
  lap: string;
  text: string;
}

export interface HistoricalSession {
  id: string;
  rawId?: string;
  driver: string;
  kart: string;
  date: string;
  duration: string;
  mode: string;
  laps: number | string;
  bestLap: string;
  maxG: string;
  alerts: number;
}

export interface TrackZone {
  id: string;
  label: string;
  corner_type?: string;
  threshold_g?: number;
  min_threshold_g?: number;
}

export interface RosterStatusItem {
  current_g: number;
  active_threshold: number;
  stage: string;
}
