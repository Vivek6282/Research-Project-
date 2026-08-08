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

export type TrajectoryStage = "nominal" | "monitoring" | "intervene";

export interface StageDetails {
  stage: TrajectoryStage;
  label: "Nominal" | "Monitoring" | "Intervene";
  color: string;
  litCount: number;
}

/**
  * Single source of truth helper to derive stage, lit count, label, and color
  */
export function getTrajectoryStage(currentG: number, threshold: number = 1.15): StageDetails {
  const safeThreshold = threshold > 0 ? threshold : 1.15;
  const ratio = currentG / safeThreshold;

  if (ratio >= 1.0) {
    return { stage: "intervene", label: "Intervene", color: "#E5473C", litCount: 5 };
  }
  if (ratio >= 0.82) {
    return { stage: "monitoring", label: "Monitoring", color: "#F2A93B", litCount: 4 };
  }
  return { stage: "nominal", label: "Nominal", color: "#33D17E", litCount: 2 };
}

const SEGMENT_COLORS = ["#33D17E", "#33D17E", "#F2A93B", "#F2A93B", "#E5473C"] as const;
const OFF_COLOR = "#232B35";

interface SignalStripProps {
  currentG?: number;
  threshold?: number;
  stage?: TrajectoryStage | "green" | "amber" | "red";
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function SignalStrip({
  currentG,
  threshold = 1.15,
  stage,
  size = "md",
  showLabel = true,
  className = "",
}: SignalStripProps) {
  let details: StageDetails;

  if (typeof currentG === "number") {
    details = getTrajectoryStage(currentG, threshold);
  } else {
    const normStage = (stage === "green" ? "nominal" : stage === "amber" ? "monitoring" : stage === "red" ? "intervene" : stage) || "nominal";
    if (normStage === "intervene") {
      details = { stage: "intervene", label: "Intervene", color: "#E5473C", litCount: 5 };
    } else if (normStage === "monitoring") {
      details = { stage: "monitoring", label: "Monitoring", color: "#F2A93B", litCount: 4 };
    } else {
      details = { stage: "nominal", label: "Nominal", color: "#33D17E", litCount: 2 };
    }
  }

  const h = size === "sm" ? 8 : size === "lg" ? 14 : 10;
  const w = h * 1.6;

  return (
    <div className={`inline-flex items-center gap-2 font-mono ${className}`}>
      {/* 5 Fixed Segment LEDs */}
      <div className="flex items-center gap-1">
        {SEGMENT_COLORS.map((baseColor, i) => {
          const isLit = i < details.litCount;
          return (
            <div
              key={i}
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
          className="text-xs font-bold uppercase tracking-wider transition-colors duration-150"
          style={{ color: details.color }}
        >
          {details.label}
        </span>
      )}
    </div>
  );
}
