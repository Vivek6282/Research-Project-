/**
 * Trackside — Bridge over Web Serial: banner check, the g,STAGE line and the reset sequence
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { BANNER_WINDOW_MS, SerialPortLike, classifyBanner, formatBridgeLine, openBridge } from "../bridge-serial";

/** A fake port: the test pushes board output with emit(); everything written is collected in written. */
function fakePort() {
  let controller!: ReadableStreamDefaultController<Uint8Array>;
  const readable = new ReadableStream<Uint8Array>({ start: (c) => (controller = c) });
  const written: string[] = [];
  const signals: object[] = [];
  const log: string[] = [];
  const port: SerialPortLike = {
    open: async () => void log.push("open"),
    close: async () => void log.push("close"),
    setSignals: async (s) => void signals.push(s),
    readable,
    writable: new WritableStream<Uint8Array>({ write: (chunk) => void written.push(new TextDecoder().decode(chunk)) }),
  };
  return { port, written, signals, log, emit: (text: string) => controller.enqueue(new TextEncoder().encode(text)) };
}

describe("banner and line format", () => {
  it("tells the bridge from the glove and ignores other lines", () => {
    expect(classifyBanner("=== TRACKSIDE BRIDGE ===")).toBe("bridge");
    expect(classifyBanner("=== TRACKSIDE GLOVE (LED only) ===")).toBe("glove");
    expect(classifyBanner("=== TRACKSIDE GLOVE (USB direct) ready ===")).toBe("glove");
    expect(classifyBanner("Bridge ready. Waiting for numbers from the laptop...")).toBeNull();
  });

  it("formats one reading as g,STAGE and refuses unusable values", () => {
    expect(formatBridgeLine(1.28, "intervene")).toBe("1.28,INTERVENE\n");
    expect(formatBridgeLine(0.5, "nominal")).toBe("0.5,NOMINAL\n");
    expect(formatBridgeLine(0.9, "monitoring")).toBe("0.9,MONITORING\n");
    expect(formatBridgeLine("1.2", "nominal")).toBeNull();
    expect(formatBridgeLine(NaN, "nominal")).toBeNull();
    expect(formatBridgeLine(1.0, "red")).toBeNull();
    expect(formatBridgeLine(1.0, undefined)).toBeNull();
  });
});

describe("openBridge", () => {
  afterEach(() => vi.useRealTimers());

  it("resets the board the standard way, accepts the bridge and writes only the lines it is given", async () => {
    const fake = fakePort();
    const pending = openBridge(fake.port, async () => undefined);
    await new Promise((resolve) => setTimeout(resolve, 0));
    fake.emit("ets Jun  8 2016\n=== TRACKSIDE BRIDGE ===\n");
    const connection = await pending;
    expect(connection.verdict).toBe("bridge");
    expect(fake.signals).toEqual([{ dataTerminalReady: false, requestToSend: true }, { requestToSend: false }]);
    await connection.send("1.28,INTERVENE\n");
    await connection.send("0.3,NOMINAL\n");
    expect(fake.written).toEqual(["1.28,INTERVENE\n", "0.3,NOMINAL\n"]);
    await connection.close();
    expect(fake.log).toEqual(["open", "close"]);
  });

  it("refuses the glove: it is closed again at once and nothing is written", async () => {
    const fake = fakePort();
    const pending = openBridge(fake.port, async () => undefined);
    await new Promise((resolve) => setTimeout(resolve, 0));
    fake.emit("=== TRACKSIDE GLOVE (LED only) ===\n");
    const connection = await pending;
    expect(connection.verdict).toBe("glove");
    expect(fake.log).toContain("close");
    expect(fake.written).toEqual([]);
  });

  it("says unknown when no banner arrives within 3.5 seconds, and keeps the port open", async () => {
    vi.useFakeTimers();
    const fake = fakePort();
    const pending = openBridge(fake.port, async () => undefined);
    await vi.advanceTimersByTimeAsync(BANNER_WINDOW_MS + 50);
    const connection = await pending;
    expect(connection.verdict).toBe("unknown");
    expect(fake.log).toEqual(["open"]);
  });
});
