/**
 * Trackside Admin Dashboard — Device Panel.
 * Shows a device's online status and last seen time, and lets the admin assign it to a driver.
 * The remote self-test ("Run Diagnostic") is parked for Phase 2: the boards do not talk to the server yet.
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
  const [selectedDriverId, setSelectedDriverId] = useState<string>(
    device.assigned_to || ""
  );
  const [reassignNotice, setReassignNotice] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    setSelectedDriverId(device.assigned_to || "");
  }, [device.assigned_to]);

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

    </Panel>
  );
}
