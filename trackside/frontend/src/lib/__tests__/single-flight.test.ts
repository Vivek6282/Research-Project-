/**
 * Trackside — singleFlight: a slow poll is waited for, not stacked on.
 */

import { describe, it, expect } from "vitest";
import { singleFlight } from "../single-flight";

describe("singleFlight", () => {
  it("skips calls made while the last one is still running, then runs again", async () => {
    let calls = 0;
    let finish: () => void = () => undefined;
    const tick = singleFlight(() => { calls++; return new Promise<void>((resolve) => (finish = resolve)); });
    const first = tick();
    expect(await tick()).toBeUndefined();     // skipped: still running
    expect(await tick()).toBeUndefined();     // skipped again
    expect(calls).toBe(1);
    finish();
    await first;
    const second = tick();
    expect(calls).toBe(2);                    // free again
    finish();
    await second;
  });

  it("frees itself after a failure, so the next poll still happens", async () => {
    let calls = 0;
    const tick = singleFlight(async () => { calls++; if (calls === 1) throw new Error("server down"); return "ok"; });
    await expect(tick()).rejects.toThrow("server down");
    expect(await tick()).toBe("ok");
    expect(calls).toBe(2);
  });
});
