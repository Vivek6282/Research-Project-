/**
 * Trackside Maps — "Add map" wizard: upload a session export, review the outline and
 * corners, name the corners, set their limits, and save.
 */

import { Upload, X } from "lucide-react";
import { useImportWizard } from "../hooks/use-import-wizard";
import { CornerTable } from "./corner-table";
import { OutlineSvg } from "./outline-svg";

interface AddMapWizardProps {
  onClose: () => void;
  onSaved: () => void;
}

const buttonClass =
  "text-xs font-mono px-3 py-2 min-h-[36px] rounded-[2px] cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

/** The two-step modal: pick a file, then review and save. */
export function AddMapWizard({ onClose, onSaved }: AddMapWizardProps) {
  const wizard = useImportWizard(onSaved);
  const { preview } = wizard;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-3 sm:p-4">
      <div
        data-testid="add-map-wizard"
        className="w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl text-[#E7EDF3]"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26] sticky top-0 z-10">
          <span className="text-xs font-bold uppercase tracking-wider">
            Add map — {preview ? "step 2 of 2: review" : "step 1 of 2: upload"}
          </span>
          <button aria-label="Close" onClick={onClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer">
            <X size={16} />
          </button>
        </div>

        <div className="p-4 flex flex-col gap-4">
          {wizard.error && (
            <p data-testid="wizard-error" role="alert" className="text-xs text-[#E5473C] border border-[#E5473C]/40 rounded p-2">
              {wizard.error}
            </p>
          )}

          {!preview && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-[#7C8898] leading-relaxed">
                Export a recorded lap session from RaceChrono (CSV v3) or a Racelogic .vbo file. The track shape comes
                from the recorded GPS path; the file is checked and nothing is saved until the last step.
              </p>
              <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
                Session file (.csv or .vbo, max 5 MB)
                <input
                  data-testid="map-file-input"
                  type="file"
                  accept=".csv,.vbo"
                  onChange={(e) => wizard.pickFile(e.target.files?.[0] ?? null)}
                  className="text-xs text-[#E7EDF3]"
                />
              </label>
              <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898] max-w-[240px]">
                Corner radius (m): stretches tighter than this count as corners
                <input
                  data-testid="map-radius-input"
                  inputMode="decimal"
                  value={wizard.radius}
                  onChange={(e) => wizard.setRadius(e.target.value)}
                  className="bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs text-[#E7EDF3]"
                />
              </label>
              <div>
                <button
                  data-testid="map-preview-btn"
                  disabled={!wizard.file || wizard.busy}
                  onClick={wizard.runPreview}
                  className={`${buttonClass} bg-[#3FA6E0] text-[#06121B] font-bold inline-flex items-center gap-2`}
                >
                  <Upload size={14} />
                  {wizard.busy ? "Reading file…" : "Preview map"}
                </button>
              </div>
            </div>
          )}

          {preview && (
            <>
              <p className="text-xs font-mono text-[#7C8898]" data-testid="wizard-summary">
                {preview.rows_used.toLocaleString()} GPS rows used, {preview.rows_rejected.toLocaleString()} rejected ·
                lap length {preview.outline_length_m.toFixed(0)} m · {preview.corners.length} corners at radius{" "}
                {preview.corner_radius_m} m
              </p>
              <OutlineSvg outline={preview.outline} corners={preview.corners} />
              <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
                Map name
                <input
                  data-testid="map-name-input"
                  value={wizard.mapName}
                  maxLength={150}
                  onChange={(e) => wizard.setMapName(e.target.value)}
                  className="bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs text-[#E7EDF3]"
                />
              </label>
              {preview.corners.length === 0 ? (
                <p className="text-xs text-[#F2A93B]" data-testid="wizard-no-corners">
                  No corners were found at this radius. Go back, raise the radius, and preview again.
                </p>
              ) : (
                <CornerTable
                  corners={preview.corners}
                  choices={wizard.choices}
                  range={preview.limit_range_g}
                  onChange={wizard.changeChoice}
                />
              )}
              {wizard.blocker && (
                <p data-testid="wizard-blocker" className="text-[11px] text-[#7C8898]">
                  Cannot save yet: {wizard.blocker}
                </p>
              )}
              <div className="flex gap-2 justify-end">
                <button onClick={wizard.backToUpload} className={`${buttonClass} border border-[#232B35] text-[#7C8898]`}>
                  Back
                </button>
                <button
                  data-testid="map-save-btn"
                  disabled={Boolean(wizard.blocker) || wizard.busy}
                  onClick={wizard.save}
                  className={`${buttonClass} bg-[#3FA6E0] text-[#06121B] font-bold`}
                >
                  {wizard.busy ? "Saving…" : "Save map"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
