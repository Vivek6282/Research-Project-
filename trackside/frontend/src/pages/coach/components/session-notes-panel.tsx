/**
 * Trackside Coach Dashboard — Session Notes Panel Component.
 * Lets the coach select or create track zones, type notes tied to laps, and view the note timeline.
 */

import { DriverProfile, TrackZone, SessionNote } from "../types";

interface SessionNotesPanelProps {
  selectedDriver: DriverProfile;
  selectedZoneId: string;
  zones: TrackZone[];
  handleZoneSelectChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  newNoteText: string;
  setNewNoteText: (val: string) => void;
  handleAddNote: () => void;
  noteError: string | null;
  isCreatingZone: boolean;
  setIsCreatingZone: (val: boolean) => void;
  setSelectedZoneId: (val: string) => void;
  newZoneName: string;
  setNewZoneName: (val: string) => void;
  newCornerType: string;
  setNewCornerType: (val: string) => void;
  handleCreateZone: () => void;
  isSavingZone: boolean;
  notes: SessionNote[];
}

export function SessionNotesPanel({
  selectedDriver,
  selectedZoneId,
  zones,
  handleZoneSelectChange,
  newNoteText,
  setNewNoteText,
  handleAddNote,
  noteError,
  isCreatingZone,
  setIsCreatingZone,
  setSelectedZoneId,
  newZoneName,
  setNewZoneName,
  newCornerType,
  setNewCornerType,
  handleCreateZone,
  isSavingZone,
  notes,
}: SessionNotesPanelProps) {
  return (
    <div
      data-testid="coach-panel-session-notes"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
    >
      <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2">
        <div className="flex items-center gap-2">
          <span className="text-[#3FA6E0] font-bold">|</span>
          <span className="text-xs font-bold text-[#E7EDF3]">
            SESSION NOTES (TIED TO LAP / ZONE)
          </span>
        </div>
        <span className="text-[10px] text-[#7C8898]">
          ACTIVE: {selectedDriver.name} (#{selectedDriver.kart})
        </span>
      </div>

      <div className="space-y-2 mb-3">
        <div className="flex flex-col sm:flex-row gap-2">
          <select
            data-testid="coach-zone-select"
            value={selectedZoneId}
            onChange={handleZoneSelectChange}
            className="bg-[#161D26] border border-[#232B35] text-[#E7EDF3] text-xs px-3 py-2 min-h-[44px] rounded-[2px] outline-none cursor-pointer"
          >
            {zones.length === 0 ? (
              <option value="">General (no zone)</option>
            ) : (
              <>
                <option value="">General (no zone)</option>
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.label} {z.corner_type ? `(${z.corner_type})` : ""}
                  </option>
                ))}
              </>
            )}
            <option value="__new__">+ New Zone...</option>
          </select>

          <input
            data-testid="coach-note-input"
            type="text"
            placeholder="Record coach observation for this lap/zone..."
            value={newNoteText}
            onChange={(e) => setNewNoteText(e.target.value)}
            className="flex-1 bg-[#161D26] border border-[#232B35] text-[#E7EDF3] text-xs px-3 py-2 min-h-[44px] rounded-[2px] outline-none focus:border-[#3FA6E0]"
          />

          <button
            data-testid="coach-save-note-btn"
            onClick={handleAddNote}
            className="bg-[#3FA6E0] text-[#0A0E13] font-bold text-xs px-5 py-2 min-h-[44px] rounded-[2px] hover:bg-[#3FA6E0]/90 cursor-pointer flex items-center justify-center"
          >
            SAVE NOTE
          </button>
        </div>

        {noteError && (
          <div
            data-testid="coach-note-error"
            className="p-2 rounded text-xs font-mono bg-[#E5473C]/15 border border-[#E5473C]/40 text-[#E5473C]"
          >
            {noteError}
          </div>
        )}

        {/* Extensible New Zone Creation Form */}
        {isCreatingZone && (
          <div
            data-testid="coach-new-zone-form"
            className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 p-2.5 bg-[#161D26] border border-[#3FA6E0]/50 rounded-[2px] text-xs animate-fade-in"
          >
            <span className="text-[#3FA6E0] font-bold">NEW ZONE:</span>
            <input
              data-testid="coach-new-zone-name-input"
              type="text"
              placeholder="Zone Name (e.g. Turn 7 Kink)"
              value={newZoneName}
              onChange={(e) => setNewZoneName(e.target.value)}
              className="bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] text-xs px-3 py-2 min-h-[40px] rounded-[2px] flex-1 outline-none focus:border-[#3FA6E0]"
            />
            <select
              data-testid="coach-new-zone-corner-select"
              value={newCornerType}
              onChange={(e) => setNewCornerType(e.target.value)}
              className="bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] text-xs px-3 py-2 min-h-[40px] rounded-[2px] outline-none cursor-pointer"
            >
              <option value="hairpin">Hairpin</option>
              <option value="sweeper">Sweeper</option>
              <option value="chicane">Chicane</option>
              <option value="straight">Straight</option>
              <option value="other">Other</option>
            </select>
            <button
              data-testid="coach-new-zone-add-btn"
              type="button"
              onClick={handleCreateZone}
              disabled={isSavingZone}
              className="bg-[#33D17E] text-[#0A0E13] font-bold px-4 py-2 min-h-[40px] rounded-[2px] cursor-pointer hover:bg-[#33D17E]/90 flex items-center justify-center"
            >
              {isSavingZone ? "SAVING..." : "ADD ZONE"}
            </button>
            <button
              data-testid="coach-new-zone-cancel-btn"
              type="button"
              onClick={() => {
                setIsCreatingZone(false);
                setSelectedZoneId(zones[0]?.id || "");
              }}
              className="text-[#7C8898] hover:text-[#E7EDF3] px-3 py-2 min-h-[40px] cursor-pointer"
            >
              CANCEL
            </button>
          </div>
        )}
      </div>

      {/* Session Notes Feed */}
      <div data-testid="coach-notes-list" className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
        {notes.map((n) => (
          <div
            key={n.id}
            data-testid="coach-note-item"
            className="bg-[#161D26] border border-[#232B35] p-2 rounded-[2px] flex items-center justify-between text-xs"
          >
            <div>
              <span className="text-[#3FA6E0] font-bold mr-2">[{n.timestamp}]</span>
              <span className="text-[#E7EDF3] font-semibold">
                {n.driverName} ({n.zone}):
              </span>
              <span className="text-[#7C8898] ml-1.5">{n.text}</span>
            </div>
            <span className="text-[10px] text-[#7C8898] bg-[#0A0E13] px-1.5 py-0.5 rounded">
              {n.lap}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
