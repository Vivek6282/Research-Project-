/**
 * Unit Tests for Trackside Alert Decision Engine (Prompt 6, F2 & Prompt 6b, H5).
 * Executable via plain Node.js: `node --test tests/demo/test_alerts.test.mjs`
 * Requires Node.js >= 18.0.0 (built-in node:test and node:assert).
 */

import test from "node:test";
import assert from "node:assert";
import "../../public/demo/track_visualization_alerts.js";

const { shouldRecordAlert } = globalThis;

test("same crossing counted once across multiple readings", () => {
  const r1 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.25 };
  const r2 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.35 };
  const r3 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.28 };

  // First reading in crossing triggers alert
  assert.strictEqual(shouldRecordAlert(null, r1), true);

  // Subsequent readings in same crossing are suppressed
  assert.strictEqual(shouldRecordAlert(r1, r2), false);
  assert.strictEqual(shouldRecordAlert(r2, r3), false);
});

test("two different corners counted twice", () => {
  const corner1 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.25 };
  const corner2 = { stage: "INTERVENE", zone: "Sweeper", lap: 1, g_force: 1.60 };

  // First corner triggers alert
  assert.strictEqual(shouldRecordAlert(null, corner1), true);

  // Transition into different corner zone triggers second alert
  assert.strictEqual(shouldRecordAlert(corner1, corner2), true);
});

test("same corner on the next lap counted again", () => {
  const lap1Corner = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.25 };
  const lap2Corner = { stage: "INTERVENE", zone: "Hairpin", lap: 2, g_force: 1.30 };

  assert.strictEqual(shouldRecordAlert(null, lap1Corner), true);
  // Next lap on same corner triggers new alert
  assert.strictEqual(shouldRecordAlert(lap1Corner, lap2Corner), true);
});

test("a straight in between resets the alert state", () => {
  const corner1 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.25 };
  const straight = { stage: "NOMINAL", zone: "Straight", lap: 1, g_force: 0.20 };
  const corner2 = { stage: "INTERVENE", zone: "Hairpin", lap: 1, g_force: 1.22 };

  // First corner triggers alert
  assert.strictEqual(shouldRecordAlert(null, corner1), true);

  // Straight never triggers alert and resets state
  assert.strictEqual(shouldRecordAlert(corner1, straight), false);

  // Corner after straight triggers alert again
  assert.strictEqual(shouldRecordAlert(straight, corner2), true);
});

test("nominal and monitoring stages never trigger alerts", () => {
  const nominalReading = { stage: "NOMINAL", zone: "Hairpin", lap: 1, g_force: 0.85 };
  const monitoringReading = { stage: "MONITORING", zone: "Hairpin", lap: 1, g_force: 1.05 };

  assert.strictEqual(shouldRecordAlert(null, nominalReading), false);
  assert.strictEqual(shouldRecordAlert(nominalReading, monitoringReading), false);
});
