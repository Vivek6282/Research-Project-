/**
 * Trackside — Track Survey & Heading-Change Zone Auto-Detection Modal
 *
 * Plotted survey line viewer with candidate corner zone boundary overlays.
 * Allows Admin/Coach to upload survey laps, review auto-detected corner zones,
 * adjust boundaries & G-thresholds, and confirm saving real Zone records.
 */

import { useState } from "react";
import { X, Navigation, CheckCircle, Sparkles } from "lucide-react";

interface CandidateZone {
  order_number: number;
  suggested_label: string;
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
  max_g_threshold: number;
}

interface TrackSurveyModalProps {
  isOpen: boolean;
  trackId: string;
  trackName: string;
  onClose: () => void;
  onZonesConfirmed: () => void;
}

export function TrackSurveyModal({
  isOpen,
  trackName,
  onClose,
}: TrackSurveyModalProps) {
  const [candidateZones] = useState<CandidateZone[]>([]);

  if (!isOpen) return null;

  /**
   * Survey analysis is disabled in Phase 1 (requires kart GPS hardware).
   */
  const handleRunSurveyAnalysis = () => {
    // Disabled in Phase 1 — needs the kart GPS unit. Sends no network request.
  };

  /**
   * Zone confirmation is disabled in Phase 1.
   */
  const handleConfirmAndSave = () => {
    // Disabled in Phase 1 — needs the kart GPS unit. Sends no network request.
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm select-none p-3 sm:p-4 font-mono text-[#E7EDF3]">
      <div className="w-full max-w-3xl max-h-[90vh] flex flex-col bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-[#232B35] bg-[#161D26] flex-shrink-0">
          <div className="flex items-center gap-2">
            <Navigation size={16} className="text-[#3FA6E0] flex-shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3] truncate">
              SURVEY & ZONE AUTO-DETECTION — {trackName}
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-[#7C8898] hover:text-[#E7EDF3] p-1.5 rounded hover:bg-[#232B35] transition-colors cursor-pointer min-h-[36px] min-w-[36px] flex items-center justify-center flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-3 sm:p-5 overflow-y-auto space-y-4 sm:space-y-5 flex-1">
          {/* Phase 2 Notice Banner */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3 bg-[#161D26] border border-[#E8C547]/40 rounded-[2px]">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles size={14} className="text-[#E8C547]" />
                <span className="text-xs font-bold text-[#E8C547]">
                  GPS HEADING-CHANGE DETECTOR (PHASE 2)
                </span>
              </div>
              <p className="text-[11px] text-[#7C8898] mt-0.5">
                Phase 2 — needs the kart GPS unit. Automated multi-lap GPS survey processing and corner zone boundary detection are scheduled for Phase 2 hardware integration.
              </p>
            </div>
            <button
              disabled
              onClick={handleRunSurveyAnalysis}
              data-testid="survey-run-button"
              className="px-3 py-1.5 rounded-[2px] bg-[#232B35] text-[#7C8898] border border-[#3A4553] text-xs font-bold cursor-not-allowed opacity-60 shrink-0"
            >
              Phase 2 — needs the kart GPS unit
            </button>
          </div>

          {/* Survey Line Visualizer Placeholder */}
          <div className="h-44 bg-[#0A0E13] border border-[#232B35] rounded-[2px] p-4 flex flex-col justify-center items-center text-center">
            <p className="text-xs text-[#7C8898]">
              No survey data recorded yet.
            </p>
            <span className="text-[10px] text-[#4B5563] mt-1">
              Phase 2 — needs the kart GPS unit
            </span>
          </div>

          {/* Candidate Zones List */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#7C8898] uppercase tracking-wider">
                | CANDIDATE CORNER ZONES ({candidateZones.length})
              </span>
              <span className="text-[10px] text-[#7C8898]">PHASE 2 FEATURE</span>
            </div>

            <div className="p-4 text-center text-xs text-[#7C8898] border border-dashed border-[#232B35] rounded-[2px]">
              No candidate zones detected. Survey feature is Phase 2.
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-[#232B35] bg-[#161D26] flex items-center justify-between">
          <span className="text-[10px] text-[#7C8898]">
            Phase 2 — needs the kart GPS unit
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-[2px] bg-[#161D26] border border-[#232B35] text-[#7C8898] hover:text-[#E7EDF3] text-xs font-bold cursor-pointer"
            >
              CANCEL
            </button>
            <button
              disabled
              onClick={handleConfirmAndSave}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-[2px] bg-[#232B35] text-[#7C8898] font-bold text-xs cursor-not-allowed opacity-60"
            >
              <CheckCircle size={14} />
              <span>Phase 2 — needs the kart GPS unit</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
