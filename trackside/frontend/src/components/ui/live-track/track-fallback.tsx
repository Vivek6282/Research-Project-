/**
 * Trackside Live Track View — Fallback States Component.
 * Renders graceful messages and placeholders when track data is absent,
 * loading, errored, or unsurveyed.
 */

interface TrackFallbackProps {
  type: "no-track" | "loading" | "error" | "unsurveyed";
}

export function TrackFallback({ type }: TrackFallbackProps) {
  return (
    <div
      data-testid="coach-panel-live-track-view"
      className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3 sm:p-4 font-mono"
    >
      <div className="flex items-center gap-2 mb-3 border-b border-[#232B35]/60 pb-2">
        <span className="text-[#3FA6E0] font-bold">|</span>
        <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
          LIVE TRACK VIEW
        </span>
      </div>

      <div
        data-testid="live-track-fallback"
        className="flex items-center justify-center h-[180px] text-xs font-mono"
      >
        {type === "no-track" && (
          <span className="text-[#7C8898]">No active track selected.</span>
        )}

        {type === "loading" && (
          <span className="text-[#7C8898] animate-pulse">Loading track shape…</span>
        )}

        {type === "error" && (
          <span className="text-[#E5473C]">Failed to load track data.</span>
        )}

        {type === "unsurveyed" && (
          <div className="flex flex-col items-center justify-center gap-3">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="#232B35"
                strokeWidth="2"
                strokeDasharray="4 3"
              />
              <circle
                cx="20"
                cy="20"
                r="8"
                stroke="#232B35"
                strokeWidth="1.5"
                strokeDasharray="3 2"
              />
              <circle cx="20" cy="8" r="3" fill="#3A4553" />
            </svg>
            <p className="text-[#7C8898] text-xs text-center leading-relaxed max-w-[320px]">
              Live Track View unavailable — this track hasn't been surveyed yet.
            </p>
            <button
              disabled
              data-testid="track-survey-button"
              className="text-[10px] bg-[#161D26] text-[#7C8898] border border-[#232B35] px-2.5 py-1 rounded-[2px] uppercase tracking-wider cursor-not-allowed opacity-75"
            >
              Phase 2 — needs the kart GPS unit
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
