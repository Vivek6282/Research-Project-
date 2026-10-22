/**
 * Trackside Coach — Bridge chip (in the sub-navigation bar).
 * Shows whether the glove bridge is connected through this browser and offers Connect bridge.
 */

import { useBridge } from "../../../lib/use-bridge";

export function BridgeChip() {
  const { supported, status, message, connect, disconnect } = useBridge();
  if (!supported) {
    return (
      <span data-testid="bridge-chip" title="Web Serial needs Chrome or Edge" className="text-[10px] text-[#7C8898] border border-[#232B35] px-2 py-0.5 rounded-[2px]">
        GLOVE BRIDGE: use Chrome or Edge
      </span>
    );
  }
  const color = status === "connected" ? "#33D17E" : status === "error" ? "#E5473C" : "#7C8898";
  return (
    <span data-testid="bridge-chip" className="flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-[2px] border" style={{ color, borderColor: `${color}55` }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      {status === "connected" ? "GLOVE BRIDGE CONNECTED" : status === "connecting" ? "CHECKING BOARD…" : "GLOVE BRIDGE: NOT CONNECTED"}
      {status === "connected" ? (
        <button data-testid="bridge-disconnect-btn" onClick={disconnect} className="underline font-normal cursor-pointer">Disconnect</button>
      ) : status !== "connecting" ? (
        <button data-testid="bridge-connect-btn" onClick={connect} className="underline cursor-pointer">Connect bridge</button>
      ) : null}
      {message && status !== "connected" && <span data-testid="bridge-message" className="font-normal text-[#F2A93B]">{message}</span>}
    </span>
  );
}
