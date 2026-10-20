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
import { DeviceRecord, UserRecord } from "../types";

interface DeviceDiagnosticPanelProps {
  device: DeviceRecord;
  activeDrivers?: UserRecord[];
  onDeviceUpdated?: (notice?: string) => Promise<void> | void;
}

export function DeviceDiagnosticPanel({
  device,
  activeDrivers = [],
  onDeviceUpdated,
}: DeviceDiagnosticPanelProps) {
  const [pollingId, setPollingId] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [manualConfirm, setManualConfirm] = useState({
    led: null as boolean | null,
    buzzer: null as boolean | null,
  });
  const [selectedDriverId, setSelectedDriverId] = useState<string>(
    device.assigned_to || ""
  );
  const [reassignNotice, setReassignNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedDriverId(device.assigned_to || "");
  }, [device.assigned_to]);

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

  const handleSaveAssignment = async () => {
    setIsSaving(true);
    setSaveError(null);
    setReassignNotice(null);
    try {
      const res: any = await api.patch(`/api/devices/${device.id}/`, {
        assigned_to: selectedDriverId || null,
      });
      if (res.reassignment_notice) {
        setReassignNotice(res.reassignment_notice);
      }
      if (onDeviceUpdated) {
        await onDeviceUpdated(res.reassignment_notice);
      }
    } catch (err: any) {
      setSaveError(err.message || "Failed to update device assignment.");
    } finally {
      setIsSaving(false);
    }
  };

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

  const isOnline = !!device.is_online;
  const statusText = (() => {
    if (isOnline) return "Online";
    if (!device.last_seen_at) return "Never seen";
    const diffSec = Math.max(0, Math.floor((Date.now() - new Date(device.last_seen_at).getTime()) / 1000));
    if (diffSec < 60) return "Offline — last seen just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `Offline — last seen ${diffMin} min ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `Offline — last seen ${diffHours} hr ago`;
    return `Offline — last seen ${Math.floor(diffHours / 24)} d ago`;
  })();

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
              isOnline
                ? "bg-[#33D17E] animate-pulse"
                : device.last_seen_at
                ? "bg-[#E5473C]"
                : "bg-[#7C8898]"
            }`}
          />
          <span
            data-testid={`admin-device-status-text-${device.id}`}
            className={`text-xs font-mono font-bold ${
              isOnline ? "text-[#33D17E]" : device.last_seen_at ? "text-[#E5473C]" : "text-[#7C8898]"
            }`}
          >
            {statusText}
          </span>
        </div>
        <Chip color={isOnline ? "#33D17E" : device.last_seen_at ? "#E5473C" : "#7C8898"}>
          {isOnline ? "ONLINE" : "OFFLINE"}
        </Chip>
      </div>

      {/* Driver Assignment Section */}
      <div className="border-t border-[#232B35] pt-2 pb-2">
        <div className="flex items-center justify-between text-xs font-mono mb-1">
          <span className="text-[#7C8898]">Driver:</span>
          <span
            data-testid={`admin-device-assigned-driver-${device.id}`}
            className="font-bold text-[#E7EDF3]"
          >
            {device.assigned_to_name || "Unassigned"}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs font-mono mb-2">
          <span className="text-[#7C8898]">Last Seen:</span>
          <span
            data-testid={`admin-device-last-seen-${device.id}`}
            className="text-[#E7EDF3]"
          >
            {device.last_seen_at
              ? new Date(device.last_seen_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })
              : "Never"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <select
            data-testid={`admin-device-assign-select-${device.id}`}
            value={selectedDriverId}
            onChange={(e) => setSelectedDriverId(e.target.value)}
            disabled={isSaving}
            className="flex-1 bg-[#141A21] border border-[#232B35] rounded px-2 py-1 text-xs font-mono text-[#E7EDF3] focus:outline-none focus:border-[#3FA6E0]"
          >
            <option value="">Unassigned</option>
            {activeDrivers.map((driver) => (
              <option key={driver.id} value={driver.id}>
                {driver.name}
              </option>
            ))}
          </select>
          <button
            data-testid={`admin-device-assign-save-btn-${device.id}`}
            onClick={handleSaveAssignment}
            disabled={isSaving || selectedDriverId === (device.assigned_to || "")}
            className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition-colors ${
              isSaving || selectedDriverId === (device.assigned_to || "")
                ? "bg-[#232B35] text-[#7C8898] cursor-not-allowed"
                : "bg-[#3FA6E0] text-[#0A0E13] hover:bg-[#3FA6E0]/90 cursor-pointer"
            }`}
          >
            {isSaving ? "..." : "Save"}
          </button>
        </div>
        {reassignNotice && (
          <div
            data-testid={`admin-device-notice-${device.id}`}
            className="mt-2 text-[11px] font-mono text-[#E5A93C] bg-[#E5A93C]/10 border border-[#E5A93C]/30 rounded p-1.5"
          >
            {reassignNotice}
          </div>
        )}
        {saveError && (
          <div
            data-testid={`admin-device-error-${device.id}`}
            className="mt-2 text-[11px] font-mono text-[#E5473C] bg-[#E5473C]/10 border border-[#E5473C]/30 rounded p-1.5"
          >
            {saveError}
          </div>
        )}
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
                Boot Check: <span className={result.result?.boot ? "text-[#33D17E]" : "text-[#E5473C]"}>{result.result?.boot ? "✓ PASS" : "✗ FAIL"}</span>
              </li>
              <li className="flex justify-between">
                ESP-NOW Init: <span className={result.result?.esp_now_init ? "text-[#33D17E]" : "text-[#E5473C]"}>{result.result?.esp_now_init ? "✓ PASS" : "✗ FAIL"}</span>
              </li>
              <li className="flex justify-between">
                Ping Latency: <span className="text-[#E7EDF3]">{result.result?.ping_latency_ms ? `${result.result.ping_latency_ms}ms` : "N/A"}</span>
              </li>
            </ul>

            <div className="border-t border-[#232B35] pt-2 space-y-2">
              <div className="text-[9px] font-bold text-[#E7EDF3]">MANUAL VERIFICATION</div>
              <div className="flex justify-between items-center">
                <span>All 3 LEDs flashed?</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, led: true }))}
                    className={`px-1.5 py-0.5 rounded ${manualConfirm.led === true ? "bg-[#33D17E] text-[#0A0E13]" : "bg-[#232B35] text-[#E7EDF3]"}`}
                  >Yes</button>
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, led: false }))}
                    className={`px-1.5 py-0.5 rounded ${manualConfirm.led === false ? "bg-[#E5473C] text-[#0A0E13]" : "bg-[#232B35] text-[#E7EDF3]"}`}
                  >No</button>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span>Buzzer pulsed?</span>
                <div className="flex gap-1">
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, buzzer: true }))}
                    className={`px-1.5 py-0.5 rounded ${manualConfirm.buzzer === true ? "bg-[#33D17E] text-[#0A0E13]" : "bg-[#232B35] text-[#E7EDF3]"}`}
                  >Yes</button>
                  <button
                    onClick={() => setManualConfirm((p) => ({ ...p, buzzer: false }))}
                    className={`px-1.5 py-0.5 rounded ${manualConfirm.buzzer === false ? "bg-[#E5473C] text-[#0A0E13]" : "bg-[#232B35] text-[#E7EDF3]"}`}
                  >No</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
