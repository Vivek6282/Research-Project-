/**
 * Trackside Maps — corner marker editor dialog (Coach and Admin).
 *
 * Mark the turning points where drivers face the highest g: each saved marker becomes an alert
 * corner (a Zone) that the alert rule and the glove use. Archived maps open view-only.
 */

import { useState } from "react";
import { Trash2, X } from "lucide-react";
import { ConfirmDialog } from "../../../components/ui/confirm-dialog";
import { useCornerEditor } from "../hooks/use-corner-editor";
import type { MapTrack } from "../types";
import { CornerEditorCanvas } from "./corner-editor-canvas";
import { CornerMarkerTable } from "./corner-marker-table";
import { LimitHistoryDialog } from "./limit-history-dialog";

interface CornerEditorDialogProps {
  map: MapTrack;
  onClose: () => void;
  /** Called after a save so the map list can reload; the text is shown on the list */
  onChanged: (message?: string) => void;
}

const buttonClass =
  "text-xs font-mono px-3 py-2 min-h-[36px] rounded-[2px] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed";

/** The dialog. */
export function CornerEditorDialog({ map, onClose, onChanged }: CornerEditorDialogProps) {
  const editor = useCornerEditor(map.id);
  const { payload } = editor;
  const [confirmClose, setConfirmClose] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);
  const [historyOf, setHistoryOf] = useState<{ id: string; label: string } | null>(null);
  const canEdit = Boolean(payload?.editable);

  /** Close, asking first when there are unsaved edits. */
  function requestClose() {
    if (editor.isDirty) setConfirmClose(true);
    else onClose();
  }

  /** Save, then tell the list to reload. */
  async function handleSave() {
    if (await editor.save()) onChanged();
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-2 sm:p-4">
      <div data-testid="corner-editor-dialog" className="w-full max-w-6xl max-h-[94vh] overflow-y-auto bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl text-[#E7EDF3]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26] sticky top-0 z-10">
          <span className="text-xs font-bold uppercase tracking-wider truncate">
            {canEdit ? "Edit corners" : "Corners"} — {map.name}
          </span>
          <button aria-label="Close" onClick={requestClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer"><X size={16} /></button>
        </div>

        <div className="p-3 sm:p-4 flex flex-col gap-3">
          {editor.isLoading && <p className="text-xs font-mono text-[#7C8898] animate-pulse">Loading corners…</p>}
          {editor.error && <p role="alert" data-testid="editor-error" className="text-xs text-[#E5473C] border border-[#E5473C]/40 rounded p-2">{editor.error}</p>}
          {payload && (
            <>
              <p className="text-[11px] font-mono text-[#7C8898] leading-relaxed" data-testid="editor-help">
                {canEdit
                  ? "Where g is highest: the tightest point of each bend. Click the outline to add a corner, drag a number along the line to move it, or click a green + to accept a suggestion. Each corner is an alert zone the glove uses."
                  : "This map is archived, so its corners are view-only. Restore it to edit them."}
              </p>
              <div className="grid grid-cols-1 lg:grid-cols-[3fr_2fr] gap-3">
                <CornerEditorCanvas
                  payload={payload} markers={editor.markers} selectedKey={editor.selectedKey} editable={canEdit}
                  onSelect={editor.setSelectedKey} onAddAt={(i) => editor.addMarker(i)}
                  onAcceptSuggestion={(s) => editor.addMarker(s.center_index, s)}
                  onMove={(key, i) => editor.updateMarker(key, { centerIndex: i })}
                />
                <CornerMarkerTable
                  payload={payload} markers={editor.markers} selectedKey={editor.selectedKey} editable={canEdit}
                  problems={editor.checks.byKey} onSelect={editor.setSelectedKey}
                  onChange={editor.updateMarker} onRemove={editor.removeMarker}
                  onHistory={(m) => m.id && setHistoryOf({ id: m.id, label: m.label })}
                />
              </div>
              {canEdit && (
                <p className="text-[10px] font-mono text-[#7C8898]">
                  Limit {payload.limit_range_g.min}–{payload.limit_range_g.max} g · zone length {payload.zone_length_m.min}–{payload.zone_length_m.max} m (default {payload.zone_length_m.default} m).
                  Removing a corner that already has telemetry or alerts hides it and keeps its history.
                </p>
              )}
              {editor.checks.first && canEdit && <p data-testid="editor-blocker" className="text-[11px] text-[#7C8898]">Cannot save yet: {editor.checks.first}</p>}
              {editor.savedNote && <p data-testid="editor-saved" className="text-xs text-[#33D17E]">{editor.savedNote}</p>}

              <div className="flex gap-2 justify-end">
                {canEdit && editor.markers.length > 0 && (
                  <button data-testid="editor-delete-all-btn" onClick={() => setConfirmClear(true)} title="Removes every corner when you press Save corners"
                    className={`${buttonClass} mr-auto inline-flex items-center gap-1.5 border border-[#E5473C]/60 text-[#E5473C]`}>
                    <Trash2 size={14} /> Delete all corners
                  </button>
                )}
                <button onClick={requestClose} className={`${buttonClass} border border-[#232B35] text-[#7C8898]`}>Close</button>
                {canEdit && (
                  <button data-testid="editor-save-btn" disabled={Boolean(editor.checks.first) || editor.isSaving || !editor.isDirty}
                    onClick={handleSave} className={`${buttonClass} bg-[#3FA6E0] text-[#06121B] font-bold`}>
                    {editor.isSaving ? "Saving…" : "Save corners"}
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
      {historyOf && <LimitHistoryDialog trackId={map.id} zoneId={historyOf.id} label={historyOf.label} onClose={() => setHistoryOf(null)} />}
      <ConfirmDialog isOpen={confirmClear} title="Delete all corners?"
        message={`All ${editor.markers.length} corners on this map will be removed when you press Save corners. Corners that already have telemetry or alerts are hidden and keep their history. Until you save, you can still close without saving.`}
        confirmText="Delete all" variant="danger" onCancel={() => setConfirmClear(false)} onConfirm={() => { setConfirmClear(false); editor.removeAllMarkers(); }} />
      <ConfirmDialog isOpen={confirmClose} title="Discard your changes?" message="You have corner changes that are not saved."
        confirmText="Discard" variant="warning" onCancel={() => setConfirmClose(false)} onConfirm={() => { setConfirmClose(false); onClose(); }} />
    </div>
  );
}
