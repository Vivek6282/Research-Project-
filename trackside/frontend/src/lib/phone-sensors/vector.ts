/**
 * Trackside phone sensors — tiny 3-D vector helpers (phone axes: x right, y up the screen, z out of the screen).
 */

export type Vec3 = [number, number, number];

/** a · b */
export function dot(a: Vec3, b: Vec3): number {
  return a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
}

/** a × b */
export function cross(a: Vec3, b: Vec3): Vec3 {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}

/** Length of a. */
export function norm(a: Vec3): number {
  return Math.sqrt(dot(a, a));
}

/** a scaled by k. */
export function scale(a: Vec3, k: number): Vec3 {
  return [a[0] * k, a[1] * k, a[2] * k];
}

/** a − b */
export function sub(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

/** a with length 1 (a zero vector stays zero). */
export function normalize(a: Vec3): Vec3 {
  const length = norm(a);
  return length > 0 ? scale(a, 1 / length) : [0, 0, 0];
}

/** The angle between a and b in degrees. */
export function angleDeg(a: Vec3, b: Vec3): number {
  const cosine = dot(normalize(a), normalize(b));
  return (Math.acos(Math.max(-1, Math.min(1, cosine))) * 180) / Math.PI;
}

/** Average of several vectors (zero when there are none). */
export function mean(vectors: Vec3[]): Vec3 {
  if (!vectors.length) return [0, 0, 0];
  const total = vectors.reduce<Vec3>((sum, v) => [sum[0] + v[0], sum[1] + v[1], sum[2] + v[2]], [0, 0, 0]);
  return scale(total, 1 / vectors.length);
}
