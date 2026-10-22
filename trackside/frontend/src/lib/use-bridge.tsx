/**
 * Trackside — Bridge connection for the Coach pages.
 * One "Connect bridge" button: the browser asks which USB port, checks it really is the bridge, then forwards the
 * stage of every live reading to it, so the glove reacts to the run shown on screen. A port chosen before is
 * reconnected by itself when the page opens.
 */

import { createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  BridgeConnection, READING_EVENT, SILICON_LABS_VENDOR_ID, SerialPortLike,
  formatBridgeLine, isWebSerialSupported, openBridge,
} from "./bridge-serial";

export type BridgeStatus = "off" | "connecting" | "connected" | "error";

interface BridgeState {
  supported: boolean;
  status: BridgeStatus;
  message: string;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
}

const BridgeContext = createContext<BridgeState | null>(null);

export function BridgeProvider({ children }: { children: ReactNode }) {
  const supported = isWebSerialSupported();
  const [status, setStatus] = useState<BridgeStatus>("off");
  const [message, setMessage] = useState("");
  const connection = useRef<BridgeConnection | null>(null);

  // Open a port; keeps it only when it is the bridge (a glove is refused with a clear message)
  const tryPort = useCallback(async (port: SerialPortLike): Promise<boolean> => {
    setStatus("connecting");
    setMessage("Checking the board…");
    try {
      const opened = await openBridge(port);
      if (opened.verdict === "glove") {
        setStatus("error");
        setMessage("That is the glove, not the bridge. Press Connect bridge and choose the other board.");
        return false;
      }
      connection.current = opened;
      setStatus("connected");
      setMessage(opened.verdict === "bridge" ? "Bridge connected" : "Connected, but the board did not say it is the bridge");
      return true;
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Could not open the port. Close the Arduino Serial Monitor.");
      return false;
    }
  }, []);

  const connect = useCallback(async () => {
    if (!supported) return;
    try {
      const port = await (navigator as any).serial.requestPort({ filters: [{ usbVendorId: SILICON_LABS_VENDOR_ID }] });
      await tryPort(port);
    } catch {
      setStatus("off");
      setMessage("");
    }
  }, [supported, tryPort]);

  const disconnect = useCallback(async () => {
    await connection.current?.close();
    connection.current = null;
    setStatus("off");
    setMessage("");
  }, []);

  // Reconnect a port the browser already knows (the first one that turns out to be the bridge)
  useEffect(() => {
    if (!supported) return;
    let cancelled = false;
    (async () => {
      const ports: SerialPortLike[] = await (navigator as any).serial.getPorts();
      for (const port of ports) {
        if (cancelled || connection.current) return;
        if (await tryPort(port)) return;
      }
      if (!cancelled && !connection.current) {
        setStatus("off");
        setMessage("");
      }
    })().catch(() => undefined);
    const onUnplug = () => {
      connection.current = null;
      setStatus("off");
      setMessage("Bridge unplugged");
    };
    (navigator as any).serial.addEventListener("disconnect", onUnplug);
    return () => {
      cancelled = true;
      (navigator as any).serial.removeEventListener("disconnect", onUnplug);
    };
  }, [supported, tryPort]);

  // Forward the stage of every live reading to the bridge
  useEffect(() => {
    const onReading = (event: Event) => {
      const data = (event as CustomEvent).detail ?? {};
      const line = formatBridgeLine(data.lateral_g, data.stage);
      if (line && connection.current) {
        connection.current.send(line).catch(() => {
          setStatus("error");
          setMessage("Could not send to the bridge");
        });
      }
    };
    window.addEventListener(READING_EVENT, onReading);
    return () => window.removeEventListener(READING_EVENT, onReading);
  }, []);

  return (
    <BridgeContext.Provider value={{ supported, status, message, connect, disconnect }}>{children}</BridgeContext.Provider>
  );
}

/** The bridge connection (a "not available" stand-in outside the provider, for example in tests). */
export function useBridge(): BridgeState {
  return (
    useContext(BridgeContext) ?? {
      supported: false, status: "off", message: "", connect: async () => undefined, disconnect: async () => undefined,
    }
  );
}
