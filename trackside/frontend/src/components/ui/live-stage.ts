/**
 * Trackside — Live stage for the Coach screen.
 * Turns the live g and the limit in force into stage details by calling getTrajectoryStage
 * (the only place that holds the stage rule). On a straight there is no limit, so it is nominal.
 */

import { getTrajectoryStage, StageDetails } from "./signal-strip";

/** Stage details for the latest reading; no reading gives NO DATA, a straight gives nominal. */
export function liveStage(currentG: number | null, threshold: number | null, isStraight: boolean): StageDetails {
  if (currentG === null) return getTrajectoryStage("no_data");
  if (isStraight) return getTrajectoryStage("nominal");
  return getTrajectoryStage(currentG, threshold ?? undefined);
}
