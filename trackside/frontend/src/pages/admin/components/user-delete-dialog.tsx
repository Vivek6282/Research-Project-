/**
 * Trackside Admin Dashboard — Permanent Delete Dialog.
 * Shows what a delete would remove (from the server's delete-preview), blocks the cases the
 * server refuses, and only enables "Delete permanently" once the driver ID (or username) is typed exactly.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "../../../lib/api";
import { UserRecord } from "../types";

interface DeletePreview {
  name: string;
  role: string;
  username: string | null;
  driver_code: string | null;
  can_delete: boolean;
  blocked_reason: string | null;
  counts: Record<string, number>;
}

interface UserDeleteDialogProps {
  user: UserRecord;
  onClose: () => void;
  onDeleted: (user: UserRecord) => void;
  onDeactivateInstead: (user: UserRecord) => void;
}

// What each count means, in the order shown (zero counts are hidden)
const COUNT_LABELS: [string, string][] = [
  ["sessions", "sessions"],
  ["telemetry_readings", "telemetry readings"],
  ["alerts", "alerts"],
  ["biometric_readings", "biometric readings"],
  ["session_notes_on_their_sessions", "coach notes on their sessions"],
  ["thresholds_set_for_them", "corner limits set for them"],
  ["devices_to_unassign", "devices will be unassigned (kept)"],
];

const FOCUSABLE = "button:not([disabled]), input:not([disabled])";

/** The text that must be typed to confirm: the driver ID for a driver, otherwise the username. */
function confirmTextOf(preview: DeletePreview): string {
  return (preview.role === "driver" && preview.driver_code) || preview.username || "";
}

export function UserDeleteDialog({ user, onClose, onDeleted, onDeactivateInstead }: UserDeleteDialogProps) {
  const [preview, setPreview] = useState<DeletePreview | null>(null);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  // Ask the server what a delete would remove
  useEffect(() => {
    let cancelled = false;
    api
      .get<DeletePreview>(`/api/auth/users/${user.id}/delete-preview/`)
      .then((res) => !cancelled && setPreview(res))
      .catch((e: Error) => !cancelled && setError(e.message || "Could not load the delete preview."));
    return () => {
      cancelled = true;
    };
  }, [user.id]);

  // Escape closes; Tab stays inside the dialog
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab" || !boxRef.current) return;
      const items = Array.from(boxRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Put the cursor in the dialog when it opens or when the preview arrives
  useEffect(() => {
    boxRef.current?.querySelector<HTMLElement>(FOCUSABLE)?.focus();
  }, [preview]);

  const expected = preview ? confirmTextOf(preview) : "";
  const canConfirm = !!preview?.can_delete && !!expected && typed === expected && !busy;
  const isActive = user.is_active !== false && user.status !== "Inactive";
  const notesWritten = preview?.counts.notes_written_by_them ?? 0;

  // Send the delete with the typed confirmation
  async function confirmDelete() {
    setBusy(true);
    setError("");
    try {
      await api.delete(`/api/auth/users/${user.id}/`, { confirm: typed });
      onDeleted(user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete this user.");
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-sm p-3 sm:p-4">
      <div
        ref={boxRef}
        role="dialog"
        aria-modal="true"
        data-testid="admin-delete-dialog"
        className="w-full max-w-md max-h-[90vh] overflow-y-auto bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl font-mono text-[#E7EDF3] p-4 space-y-3"
      >
        <div className="text-xs font-bold uppercase tracking-wider text-[#E5473C]">
          Delete {user.name} ({user.driver_code || user.username || "-"}) permanently?
        </div>

        {!preview && !error && <div className="text-xs text-[#7C8898]">Checking what would be removed...</div>}

        {preview && !preview.can_delete && (
          <div data-testid="admin-delete-blocked" className="text-xs p-2 rounded border border-[#F2A93B]/40 bg-[#F2A93B]/10 text-[#F2A93B]">
            {preview.blocked_reason}
          </div>
        )}

        {preview && preview.can_delete && (
          <>
            <ul data-testid="admin-delete-counts" className="text-xs text-[#7C8898] list-disc pl-5 space-y-0.5">
              {COUNT_LABELS.filter(([key]) => (preview.counts[key] ?? 0) > 0).map(([key, label]) => (
                <li key={key}>{preview.counts[key]} {label}</li>
              ))}
            </ul>
            {preview.role === "coach" && notesWritten > 0 && (
              <p className="text-xs text-[#F2A93B]">Notes written by this coach ({notesWritten}) will also be deleted.</p>
            )}
            <label className="block text-[10px] text-[#7C8898]">
              Type {expected} to confirm
              <input
                data-testid="admin-delete-confirm-input"
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                autoComplete="off"
                className="mt-1 w-full px-3 py-2 rounded text-xs bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] outline-none focus:border-[#E5473C]"
              />
            </label>
          </>
        )}

        {error && <div data-testid="admin-delete-error" role="alert" className="text-xs text-[#E5473C]">{error}</div>}

        <div className="flex flex-wrap gap-2 pt-1">
          {preview?.can_delete && (
            <button
              data-testid="admin-delete-confirm-btn"
              disabled={!canConfirm}
              onClick={confirmDelete}
              className={`px-3 py-2 min-h-[40px] rounded text-xs font-bold bg-[#E5473C] text-white ${canConfirm ? "cursor-pointer" : "opacity-40 cursor-not-allowed"}`}
            >
              Delete permanently
            </button>
          )}
          {isActive && (
            <button
              data-testid="admin-delete-deactivate-instead-btn"
              onClick={() => onDeactivateInstead(user)}
              className="px-3 py-2 min-h-[40px] rounded text-xs border border-[#F2A93B66] text-[#F2A93B] cursor-pointer"
            >
              Deactivate instead
            </button>
          )}
          <button
            data-testid="admin-delete-cancel-btn"
            onClick={onClose}
            className="px-3 py-2 min-h-[40px] rounded text-xs border border-[#232B35] text-[#7C8898] cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
