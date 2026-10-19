/**
 * Trackside Admin Dashboard — Device Diagnostic Panel.
 * Manages device status display, self-test diagnostics command trigger,
 * polling for diagnostic outcomes, and manual hardware verification.
 */

import { useState, useEffect } from "react";
import { Wifi, WifiOff } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { Chip } from "../../../components/ui/chip";
import { api } from "../../../lib/api";
import { DeviceRecord } from "../types";

interface DeviceDiagnosticPanelProps {
  device: DeviceRecord;
}

export function DeviceDiagnosticPanel({ device }: DeviceDiagnosticPanelProps) {
  const [pollingId, setPollingId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [manualConfirm, setManualConfirm] = useState({
    led: null as boolean | null,
    buzzer: null as boolean | null,
  });

  useEffect(() => {
    let interval: any;
    if (pollingId) {
      interval = setInterval(async () => {
        try {
          const res: any = await api.get(`/api/devices/${device.id}/commands/`);
          const cmds = Array.isArray(res) ? res : res?.results || [];
          const cmd = cmds.find((c: any) => c.id === pollingId);
          if (cmd && cmd.status !== "pending") {
            setResult(cmd);
            setPollingId(null);
          }
        } catch (e) {
          console.error(e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [pollingId, device.id]);

  const handleRunDiagnostic = async () => {
    setResult(null);
    setManualConfirm({ led: null, buzzer: null });
    try {
      const res: any = await api.post(`/api/devices/${device.id}/commands/`, {
        command_type: "self_test",
      });
      setPollingId(res.id);
    } catch (e) {
      alert("Failed to start diagnostic.");
    }
  };

  const getIcon = (type: string) => {
    if (type === "glove" || type === "kart_unit") return <Wifi size={16} />;
    return <WifiOff size={16} />;
  };

  const isOnline = device.status === "connected";

  return (
    <Panel
      title={device.device_type.replace("_", " ").toUpperCase()}
      icon={getIcon(device.device_type).type}
      testId={`admin-device-panel-${device.id}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isOnline ? "bg-[#33D17E] animate-pulse" : "bg-[#E5473C]"
            }`}
          />
          <span
            className={`text-xs font-mono font-bold ${
              isOnline ? "text-[#E7EDF3]" : "text-[#E5473C]"
            }`}
          >
            {isOnline ? "ONLINE" : "OFFLINE"}
          </span>
        </div>
        <Chip color={isOnline ? "#33D17E" : "#E5473C"}>
          {device.status.toUpperCase()}
        </Chip>
      </div>

      <div className="border-t border-[#232B35] pt-3">
        <button
          data-testid="admin-run-diagnostic-btn"
          onClick={handleRunDiagnostic}
          disabled={!!pollingId || !isOnline}
          className={`w-full py-1.5 rounded text-[11px] font-bold font-mono transition-colors ${
            pollingId
              ? "bg-[#3FA6E0]/20 text-[#3FA6E0] cursor-not-allowed"
              : !isOnline
              ? "bg-[#232B35] text-[#7C8898] cursor-not-allowed"
              : "bg-[#3FA6E0] text-[#0A0E13] hover:bg-[#3FA6E0]/90 cursor-pointer"
          }`}
        >
          {pollingId ? (
            <span data-testid="admin-diagnostic-waiting">WAITING FOR DEVICE...</span>
          ) : (
            "RUN DIAGNOSTIC"
          )}
        </button>

        {result && (
          <div
            data-testid="admin-diagnostic-result"
            className="mt-3 bg-[#0A0E13] border border-[#232B35] rounded p-2 text-[10px] font-mono"
          >
            <div className="font-bold mb-1 text-[#3FA6E0]">
              DIAGNOSTIC RESULT: {result.status.toUpperCase()}
            </div>
            <ul className="space-y-1 mb-2 text-[#7C8898]">
              <li className="flex justify-between">
                Boot Check:{" "}
                <span className={result.result?.boot ? "text-[#33D17E]" : "text-[#E5473C]"}>
                  {result.result?.boot ? "✓ PASS" : "✗ FAIL"}
                </span>
              </li>
              <li className="flex justify-between">
                ESP-NOW Init:{" "}
                <span className={result.result?.esp_now_init ? "text-[#33D17E]" : "text-[#E5473C]"}>
                  {result.result?.esp_now_init ? "✓ PASS" : "✗ FAIL"}
                </span>
              </li>
              <li className="flex justify-between">
                Ping Latency:{" "}
                <span className="text-[#E7EDF3]">
                  {result.result?.ping_latency_ms ? `${result.result.ping_latency_ms}ms` : "N/A"}
                </span>
              </li>
            </ul>

            <div className="border-t border-[#232B35] pt-2 space-y-2">
              <div className="text-[9px] font-bold text-[#E7EDF3]">MANUAL VERIFICATION</div>
              <div className="flex justify-between items-center">
                <span>All 3 LEDs flashed?</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, led: true }))}
                    className={`px-1.5 py-0.5 rounded ${
                      manualConfirm.led === true
                        ? "bg-[#33D17E] text-[#0A0E13]"
                        : "bg-[#232B35] text-[#E7EDF3]"
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, led: false }))}
                    className={`px-1.5 py-0.5 rounded ${
                      manualConfirm.led === false
                        ? "bg-[#E5473C] text-[#0A0E13]"
                        : "bg-[#232B35] text-[#E7EDF3]"
                    }`}
                  >
                    No
                  </button>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span>Buzzer pulsed?</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, buzzer: true }))}
                    className={`px-1.5 py-0.5 rounded ${
                      manualConfirm.buzzer === true
                        ? "bg-[#33D17E] text-[#0A0E13]"
                        : "bg-[#232B35] text-[#E7EDF3]"
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, buzzer: false }))}
                    className={`px-1.5 py-0.5 rounded ${
                      manualConfirm.buzzer === false
                        ? "bg-[#E5473C] text-[#0A0E13]"
                        : "bg-[#232B35] text-[#E7EDF3]"
                    }`}
                  >
                    No
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
