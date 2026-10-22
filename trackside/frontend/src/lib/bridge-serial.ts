/**
 * Trackside — Bridge over Web Serial (Chrome and Edge, HTTPS).
 * The Coach's browser opens the bridge board's USB port, checks its startup banner
 * ("TRACKSIDE BRIDGE" or "TRACKSIDE GLOVE") and then sends one "g,STAGE" line per live
 * reading, exactly the line the simulator sends from a laptop. Nothing else is ever written.
 */

export const BRIDGE_BAUD = 115200;
export const BANNER_WINDOW_MS = 3500;
export const RESET_PULSE_MS = 100;
export const SILICON_LABS_VENDOR_ID = 0x10c4; // the USB-serial chip on the ESP32 boards
export const READING_EVENT = "trackside:reading";

export type BridgeVerdict = "bridge" | "glove" | "unknown";

/** The part of a Web Serial port this code uses (so a fake port can stand in for tests). */
export interface SerialPortLike {
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
  setSignals(signals: { dataTerminalReady?: boolean; requestToSend?: boolean }): Promise<void>;
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
}

/** True when this browser has Web Serial (Chrome and Edge on desktop). */
export function isWebSerialSupported(): boolean {
  return typeof navigator !== "undefined" && "serial" in navigator;
}

/** What a startup banner line says: the bridge, the glove, or null for any other line. */
export function classifyBanner(line: string): "bridge" | "glove" | null {
  const text = line.toUpperCase();
  if (text.includes("TRACKSIDE BRIDGE")) return "bridge";
  if (text.includes("TRACKSIDE GLOVE")) return "glove";
  return null;
}

const STAGES = ["NOMINAL", "MONITORING", "INTERVENE"];

/** The line for one reading ("1.28,INTERVENE\n"), or null when the g value or the stage is not usable. */
export function formatBridgeLine(g: unknown, stage: unknown): string | null {
  const word = typeof stage === "string" ? stage.toUpperCase() : "";
  if (typeof g !== "number" || !Number.isFinite(g) || !STAGES.includes(word)) return null;
  return `${g},${word}\n`;
}

/** An open, verified bridge connection. */
export interface BridgeConnection {
  verdict: BridgeVerdict;
  send(line: string): Promise<void>;
  close(): Promise<void>;
}

/**
 * Open the port, reset the board the standard ESP32 way (dtr false, rts true, 0.1 s, rts false), read its
 * banner for up to 3.5 s and keep the port open for sending. A glove is closed again at once.
 */
export async function openBridge(
  port: SerialPortLike,
  sleep: (ms: number) => Promise<void> = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
): Promise<BridgeConnection> {
  await port.open({ baudRate: BRIDGE_BAUD });
  await port.setSignals({ dataTerminalReady: false, requestToSend: true });
  await sleep(RESET_PULSE_MS);
  await port.setSignals({ requestToSend: false });

  const reader = port.readable!.getReader();
  const writer = port.writable!.getWriter();
  const decoder = new TextDecoder();
  let buffer = "";

  // Keep reading so the board's output never fills the port; the first banner decides the verdict
  let settle: (verdict: BridgeVerdict) => void = () => {};
  const banner = new Promise<BridgeVerdict>((resolve) => (settle = resolve));
  const timer = setTimeout(() => settle("unknown"), BANNER_WINDOW_MS);
  const drained = (async () => {
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          const found = classifyBanner(line);
          if (found) settle(found);
        }
      }
    } catch {
      /* the port was closed or unplugged */
    }
    settle("unknown");
  })();

  const verdict = await banner;
  clearTimeout(timer);

  let queue: Promise<void> = Promise.resolve();
  const connection: BridgeConnection = {
    verdict,
    // Writes go out one after another, in order
    send(line: string) {
      queue = queue.then(() => writer.write(new TextEncoder().encode(line)));
      return queue;
    },
    async close() {
      try {
        await reader.cancel();
        await drained;
        reader.releaseLock();
        await writer.close();
      } catch {
        /* already closed */
      }
      try {
        await port.close();
      } catch {
        /* already closed */
      }
    },
  };
  if (verdict === "glove") await connection.close();
  return connection;
}
