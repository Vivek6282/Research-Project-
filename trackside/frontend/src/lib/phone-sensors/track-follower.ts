/**
 * Trackside phone sensors — a smooth position on the track between GPS fixes.
 *
 * Phones give about one GPS fix per second. Between fixes the position moves along the track outline by
 * speed × time; each new fix snaps it back to the nearest outline point. Far from the outline (pit lane)
 * the raw GPS position is used. Positions sent from here are on the outline, which is also where the
 * server looks for corners.
 */

export interface LatLng {
  lat: number;
  lng: number;
}

const METERS_PER_DEG_LAT = 111_320;
export const OFF_TRACK_M = 30;
/** Never run ahead of the last fix by more than this (seconds), in case fixes stop. */
export const MAX_EXTRAPOLATE_S = 3;
const NEARBY_POINTS = 60;

export class TrackFollower {
  private readonly xy: [number, number][];
  private readonly along: number[];
  private readonly length: number;
  private readonly originLat: number;
  private readonly originLng: number;
  private readonly metersPerDegLng: number;
  private lastIndex: number | null = null;
  private fix: { s: number | null; raw: LatLng; speedMs: number; atMs: number } | null = null;

  /** Prepare the outline (at least 3 points) in local metres with the distance along it. */
  constructor(outline: LatLng[]) {
    this.originLat = outline.reduce((a, p) => a + p.lat, 0) / outline.length;
    this.originLng = outline.reduce((a, p) => a + p.lng, 0) / outline.length;
    this.metersPerDegLng = METERS_PER_DEG_LAT * Math.cos((this.originLat * Math.PI) / 180);
    this.xy = outline.map((p) => this.toXY(p));
    this.along = [0];
    for (let i = 1; i <= this.xy.length; i += 1) {
      const [a, b] = [this.xy[i - 1], this.xy[i % this.xy.length]];
      this.along.push(this.along[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1]));
    }
    this.length = this.along[this.xy.length];
  }

  /** Lat/lng to local metres. */
  private toXY(p: LatLng): [number, number] {
    return [(p.lng - this.originLng) * this.metersPerDegLng, (p.lat - this.originLat) * METERS_PER_DEG_LAT];
  }

  /** Local metres to lat/lng. */
  private toLatLng([x, y]: [number, number]): LatLng {
    return { lat: this.originLat + y / METERS_PER_DEG_LAT, lng: this.originLng + x / this.metersPerDegLng };
  }

  /** Squared distance from outline point i to (x, y). */
  private gap(i: number, x: number, y: number): number {
    return (this.xy[i][0] - x) ** 2 + (this.xy[i][1] - y) ** 2;
  }

  /** Nearest outline point: near the last one first, else the whole outline. */
  private nearest(x: number, y: number): [number, number] {
    const count = this.xy.length;
    const pick = (indexes: number[]) => indexes.reduce((best, i) => (this.gap(i, x, y) < this.gap(best, x, y) ? i : best));
    if (this.lastIndex !== null) {
      const near = Array.from({ length: 2 * NEARBY_POINTS + 1 }, (_, k) => (this.lastIndex! + k - NEARBY_POINTS + count) % count);
      const best = pick(near);
      if (Math.sqrt(this.gap(best, x, y)) <= OFF_TRACK_M / 2) return [best, Math.sqrt(this.gap(best, x, y))];
    }
    const best = pick(Array.from({ length: count }, (_, i) => i));
    return [best, Math.sqrt(this.gap(best, x, y))];
  }

  /** Take a new GPS fix with its speed (m/s) and time (ms). */
  onFix(position: LatLng, speedMs: number, atMs: number): void {
    const [x, y] = this.toXY(position);
    const [index, distance] = this.nearest(x, y);
    const onTrack = distance <= OFF_TRACK_M;
    if (onTrack) this.lastIndex = index;
    this.fix = { s: onTrack ? this.along[index] : null, raw: position, speedMs: Math.max(0, speedMs), atMs };
  }

  /** The position to report at time atMs, or null before the first fix. */
  positionAt(atMs: number): LatLng | null {
    if (!this.fix) return null;
    if (this.fix.s === null) return this.fix.raw;
    const seconds = Math.min(Math.max(0, (atMs - this.fix.atMs) / 1000), MAX_EXTRAPOLATE_S);
    const s = (this.fix.s + this.fix.speedMs * seconds) % this.length;
    let i = this.along.findIndex((value) => value > s) - 1;
    if (i < 0) i = this.xy.length - 1;
    const segment = this.along[i + 1] - this.along[i] || 1;
    const t = (s - this.along[i]) / segment;
    const [a, b] = [this.xy[i], this.xy[(i + 1) % this.xy.length]];
    return this.toLatLng([a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]);
  }
}
