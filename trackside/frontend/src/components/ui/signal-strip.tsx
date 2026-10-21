/**
 * Trackside — Signal Strip Component & Stage Evaluator
 *
 * 5-segment LED strip mirroring the physical glove hardware.
 * Fixed base colors (left to right): [Green, Green, Amber, Amber, Red]
 *
 * Stage behavior (driven by single source of truth getTrajectoryStage):
 * - Nominal (lateral-g < 82% threshold) → 2 segments lit (Green, Green), label "Nominal" (#33D17E)
 * - Monitoring (82% ≤ lateral-g < 100% threshold) → 4 segments lit (Green, Green, Amber, Amber), label "Monitoring" (#F2A93B)
 * - Intervene (lateral-g ≥ 100% threshold) → 5 segments lit (Green, Green, Amber, Amber, Red), label "Intervene" (#E5473C)
 */

export type TrajectoryStage = "no_data" | "nominal" | "monitoring" | "intervene";

export interface StageDetails {
  stage: TrajectoryStage;
  label: "NO DATA" | "Nominal" | "Monitoring" | "Intervene";
  color: string;
  litCount: number;
}

/**
 * Derives trajectory stage details from either a lateral G reading or stage identifier.
 * Returns no_data (0 lit segments, label NO DATA, color #7C8898) when input is null, undefined, or "no_data".
 */
export function getTrajectoryStage(
  input?: number | TrajectoryStage | "green" | "amber" | "red" | null,
  threshold: number = 1.15,
): StageDetails {
  if (input === null || input === undefined || input === "no_data") {
    return { stage: "no_data", label: "NO DATA", color: "#7C8898", litCount: 0 };
  }

  if (typeof input === "number") {
    const safeThreshold = threshold > 0 ? threshold : 1.15;
    const ratio = input / safeThreshold;

    if (ratio >= 1.0) {
      return { stage: "intervene", label: "Intervene", color: "#E5473C", litCount: 5 };
    }
    if (ratio >= 0.82) {
      return { stage: "monitoring", label: "Monitoring", color: "#F2A93B", litCount: 4 };
    }
    return { stage: "nominal", label: "Nominal", color: "#33D17E", litCount: 2 };
  }

  const normStage =
    input === "green" ? "nominal" : input === "amber" ? "monitoring" : input === "red" ? "intervene" : input;
  if (normStage === "intervene") {
    return { stage: "intervene", label: "Intervene", color: "#E5473C", litCount: 5 };
  }
  if (normStage === "monitoring") {
    return { stage: "monitoring", label: "Monitoring", color: "#F2A93B", litCount: 4 };
  }
  if (normStage === "nominal") {
    return { stage: "nominal", label: "Nominal", color: "#33D17E", litCount: 2 };
  }
  return { stage: "no_data", label: "NO DATA", color: "#7C8898", litCount: 0 };
}

const SEGMENT_COLORS = ["#33D17E", "#33D17E", "#F2A93B", "#F2A93B", "#E5473C"] as const;
const OFF_COLOR = "#232B35";

interface SignalStripProps {
  currentG?: number | null;
  threshold?: number;
  stage?: TrajectoryStage | "green" | "amber" | "red" | null;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
  testId?: string;
}

/**
 * 5-segment LED signal strip component that visualizes real-time lateral G-force stages.
 */
export function SignalStrip({
  currentG,
  threshold = 1.15,
  stage,
  size = "md",
  showLabel = true,
  className = "",
  testId,
}: SignalStripProps) {
  let details: StageDetails;

  if (typeof currentG === "number") {
    details = getTrajectoryStage(currentG, threshold);
  } else if (stage) {
    details = getTrajectoryStage(stage, threshold);
  } else {
    details = getTrajectoryStage("no_data", threshold);
  }

  const h = size === "sm" ? 8 : size === "lg" ? 14 : 10;
  const w = h * 1.6;

  const baseTestId = testId || "signal-strip";

  return (
    <div
      data-testid={baseTestId}
      className={`inline-flex items-center gap-2 font-mono ${className}`}
    >
      {/* 5 Fixed Segment LEDs */}
      <div
        data-testid={`${baseTestId}-segments`}
        className="flex items-center gap-1"
      >
        {SEGMENT_COLORS.map((baseColor, i) => {
          const isLit = i < details.litCount;
          return (
            <div
              key={i}
              data-testid={`${baseTestId}-segment-${i}`}
              data-lit={isLit ? "true" : "false"}
              style={{
                width: w,
                height: h,
                borderRadius: 2,
                background: isLit ? baseColor : OFF_COLOR,
                boxShadow: isLit ? `0 0 8px ${baseColor}99` : "none",
                transition: "all 150ms ease",
              }}
            />
          );
        })}
      </div>

      {/* Synchronized Status Label */}
      {showLabel && (
        <span
          data-testid={`${baseTestId}-stage-label`}
          className="text-xs font-bold uppercase tracking-wider transition-colors duration-150"
          style={{ color: details.color }}
        >
          {details.label}
        </span>
      )}
    </div>
  );
}
