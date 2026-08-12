/**
 * Trackside — Reusable Confirm Dialog Component
 *
 * Pit-Wall styled confirmation modal for destructive or critical actions:
 * - Dark panel (#12181F), border (#232B35), matching Settings modal backdrop
 * - Custom title, message, button labels, and variant colors (danger, warning, primary)
 * - Dismissible via clicking backdrop or pressing Escape key
 */

import { useEffect } from "react";
import { X, AlertTriangle } from "lucide-react";

export interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "warning" | "primary";
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onCancel();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const btnBgClass =
    variant === "danger"
      ? "bg-[#E5473C] hover:bg-[#E5473C]/90 text-[#FFFFFF]"
      : variant === "warning"
      ? "bg-[#F2A93B] hover:bg-[#F2A93B]/90 text-[#06121B]"
      : "bg-[#3FA6E0] hover:bg-[#3FA6E0]/90 text-[#06121B]";

  const iconColor =
    variant === "danger" ? "#E5473C" : variant === "warning" ? "#F2A93B" : "#3FA6E0";

  return (
    <div
      onClick={onCancel}
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-sm select-none p-4"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl overflow-hidden font-mono text-[#E7EDF3] animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26]">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} style={{ color: iconColor }} />
            <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
              {title}
            </span>
          </div>
          <button
            onClick={onCancel}
            className="text-[#7C8898] hover:text-[#E7EDF3] p-1 rounded hover:bg-[#232B35] transition-colors cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Message Body */}
        <div className="p-5 space-y-4">
          <p className="text-xs text-[#C5D1DE] leading-relaxed font-mono">{message}</p>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 rounded text-xs font-mono font-semibold uppercase tracking-wider cursor-pointer bg-[#1A222D] hover:bg-[#232B35] text-[#7C8898] border border-[#232B35] transition-colors"
            >
              {cancelText}
            </button>
            <button
              onClick={onConfirm}
              className={`px-4 py-2 rounded text-xs font-mono font-bold uppercase tracking-wider cursor-pointer transition-colors ${btnBgClass}`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
