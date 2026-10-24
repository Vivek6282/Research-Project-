/**
 * SYNTHETIC test data: what a phone mounted at an angle in a kart would measure. Not a real recording.
 * World axes: x right, y forward, z up. The phone is tilted 60° about its x axis and turned 30° about z.
 */

import type { Vec3 } from "../vector";

const tilt = (60 * Math.PI) / 180;
const turn = (30 * Math.PI) / 180;

/** World vector → the same vector in the phone's own axes (rotate by -turn about z, then -tilt about x). */
export function toPhone([x, y, z]: Vec3): Vec3 {
  const x1 = x * Math.cos(turn) + y * Math.sin(turn);
  const y1 = -x * Math.sin(turn) + y * Math.cos(turn);
  return [x1, y1 * Math.cos(tilt) + z * Math.sin(tilt), -y1 * Math.sin(tilt) + z * Math.cos(tilt)];
}

export const WORLD_UP: Vec3 = [0, 0, 1];
export const WORLD_FORWARD: Vec3 = [0, 1, 0];
export const WORLD_RIGHT: Vec3 = [1, 0, 0];

/** A small repeatable wobble (no randomness, so the tests never flake). */
export function wobble(i: number, size: number): Vec3 {
  return [Math.sin(i * 1.3) * size, Math.cos(i * 0.7) * size, Math.sin(i * 2.1) * size];
}
