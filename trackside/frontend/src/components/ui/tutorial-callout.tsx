/**
 * Trackside — Per-Role Dismissible Tutorial System
 *
 * Renders a sequence of numbered callout steps explaining key dashboard panels.
 * Content is customized per role (Coach, Driver, Admin).
 * Remembers dismissal on the backend via user_preferences API (tutorial_completed: true).
 */

import { useState } from "react";
import { ChevronRight, ChevronLeft, CheckCircle, Sparkles } from "lucide-react";
import { usePreferences } from "../../context/PreferencesContext";

interface StepContent {
  title: string;
  badge: string;
  description: string;
}

const COACH_STEPS: StepContent[] = [
  {
    title: "LIVE TRAJECTORY & 5-SEGMENT SIGNAL STRIP",
    badge: "1 OF 4",
    description: "Streams kart telemetry at 20Hz (actual vs target speed curves) paired with a live 5-segment LED signal strip displaying Nominal, Monitoring, or Intervene status.",
  },
  {
    title: "TIMING TOWER & DRIVER ROSTER",
    badge: "2 OF 4",
    description: "Real-time 5-driver classification tower showing live status (ACTIVE / PITS), lap times, gaps, sector deltas, and active kart selection.",
  },
  {
    title: "CUSTOM ZONE THRESHOLD CONTROL",
    badge: "3 OF 4",
    description: "Calibrate per-driver lateral G-force safety thresholds (e.g. Turn 4 Hairpin max 1.15g) validated server-side to enforce safety envelopes.",
  },
  {
    title: "SESSION NOTES RECORDER",
    badge: "4 OF 4",
    description: "Record coach observations for specific laps and track zones, saved directly to the backend database.",
  },
];

const DRIVER_STEPS: StepContent[] = [
  {
    title: "SESSION MODE SELECTION",
    badge: "1 OF 3",
    description: "Select your driving session mode: Performance mode (1.15g standard threshold) or Safety mode (1.00g conservative threshold).",
  },
  {
    title: "5-SEGMENT LED SIGNAL STRIP MIRROR",
    badge: "2 OF 3",
    description: "Mirrors your physical race glove LEDs: Green (Nominal), Amber (Monitoring), and Red (Intervene stage).",
  },
  {
    title: "ZONE RISK HEATMAP & G-FORCE GAUGE",
    badge: "3 OF 3",
    description: "Real-time G-force gauge and track corner risk heatmaps highlighting safety zone entry.",
  },
];

const ADMIN_STEPS: StepContent[] = [
  {
    title: "IOT HARDWARE DEVICE GRID",
    badge: "1 OF 3",
    description: "Monitor registered Glove Units, Kart Sensor Units, and Biometric Straps connectivity, driver assignment, and API key tokens.",
  },
  {
    title: "SYSTEM USER MANAGEMENT",
    badge: "2 OF 3",
    description: "Create new user accounts, assign roles (Admin, Coach, Driver), and manage account active status.",
  },
  {
    title: "ACADEMY SYSTEM STATISTICS",
    badge: "3 OF 3",
    description: "High-level overview of active driving sessions, total registered nodes, and platform uptime.",
  },
];

export function TutorialCallout({ role }: { role: "coach" | "driver" | "admin" }) {
  const { tutorialCompleted, updatePreferences } = usePreferences();
  const [currentStep, setCurrentStep] = useState<number>(0);

  if (tutorialCompleted) return null;

  const steps = role === "coach" ? COACH_STEPS : role === "driver" ? DRIVER_STEPS : ADMIN_STEPS;
  const step = steps[currentStep] || steps[0];
  const isFirst = currentStep === 0;
  const isLast = currentStep === steps.length - 1;

  const handleFinish = async () => {
    await updatePreferences({ tutorial_completed: true });
  };

  const handleNext = () => {
    if (isLast) {
      handleFinish();
    } else {
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    if (!isFirst) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  return (
    <div className="bg-[#12181F] border-b border-[#3FA6E0]/40 px-4 py-2.5 font-mono select-none animate-in fade-in duration-200">
      <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        {/* Left: Step Badge, Role Tag & Description */}
        <div className="flex items-center gap-3 flex-1">
          <span className="bg-[#3FA6E0] text-[#0A0E13] font-extrabold text-[10px] px-2 py-0.5 rounded-[2px] uppercase flex items-center gap-1 shrink-0">
            <Sparkles size={11} />
            {step.badge}
          </span>

          <span className="text-[#3FA6E0] font-bold text-[11px] uppercase tracking-wider shrink-0">
            {step.title}:
          </span>

          <span className="text-[#E7EDF3] text-[11px] leading-relaxed">
            {step.description}
          </span>
        </div>

        {/* Right: Step Controls (BACK / NEXT / SKIP) */}
        <div className="flex items-center gap-2 shrink-0 self-end md:self-auto">
          {!isFirst && (
            <button
              onClick={handleBack}
              className="flex items-center gap-1 px-2.5 py-1 rounded-[2px] bg-[#161D26] border border-[#232B35] text-[#7C8898] hover:text-[#E7EDF3] hover:border-[#3A4553] cursor-pointer text-[11px] font-bold transition-all"
            >
              <ChevronLeft size={13} />
              <span>BACK</span>
            </button>
          )}

          <button
            onClick={handleNext}
            className="flex items-center gap-1 px-3 py-1 rounded-[2px] bg-[#3FA6E0] text-[#0A0E13] hover:bg-[#3FA6E0]/90 cursor-pointer text-[11px] font-bold transition-all"
          >
            <span>{isLast ? "FINISH" : "NEXT"}</span>
            {isLast ? <CheckCircle size={13} /> : <ChevronRight size={13} />}
          </button>

          <button
            onClick={handleFinish}
            className="text-[11px] text-[#7C8898] hover:text-[#E5473C] px-2 py-1 cursor-pointer transition-colors"
          >
            Skip all
          </button>
        </div>
      </div>
    </div>
  );
}
