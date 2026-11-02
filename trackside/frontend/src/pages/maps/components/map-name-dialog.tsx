/**
 * Trackside Maps — one small form dialog for "Edit details" (name and kart class) and "Duplicate" (name only).
 * The caller's onSubmit throws an Error to show its message under the form.
 */

import { useState } from "react";
import { X } from "lucide-react";

export const KART_CLASSES = [
  { value: "rental", label: "Rental karts (limits 0.3–0.8 g)" },
  { value: "sprint", label: "Sprint karts (limits 0.3–1.5 g)" },
] as const;

interface MapNameDialogProps {
  title: string;
  initialName: string;
  /** Pass the current class to show the kart class choice; leave out to ask for a name only */
  initialKartClass?: string;
  submitText: string;
  onSubmit: (values: { name: string; kartClass: string }) => Promise<void>;
  onClose: () => void;
}

/** The dialog; closes itself through onClose after a successful submit (the caller decides). */
export function MapNameDialog({ title, initialName, initialKartClass, submitText, onSubmit, onClose }: MapNameDialogProps) {
  const [name, setName] = useState(initialName);
  const [kartClass, setKartClass] = useState(initialKartClass ?? "sprint");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const blank = !name.trim();

  /** Send the values; keep the dialog open with the server's message when it is refused. */
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (blank) return;
    setIsBusy(true);
    setError(null);
    try {
      await onSubmit({ name: name.trim(), kartClass });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setIsBusy(false);
    }
  }

  const fieldClass = "bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-2 text-xs text-[#E7EDF3] focus:border-[#3FA6E0] outline-none";
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-sm p-3" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()} data-testid="map-name-dialog" aria-label={title}
        className="w-full max-w-md bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl font-mono text-[#E7EDF3]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26]">
          <span className="text-xs font-bold uppercase tracking-wider">{title}</span>
          <button type="button" aria-label="Close" onClick={onClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer"><X size={16} /></button>
        </div>
        <div className="p-4 flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-[11px] text-[#7C8898]">
            Map name
            <input data-testid="map-name-input" value={name} maxLength={150} autoFocus onChange={(e) => setName(e.target.value)}
              aria-invalid={blank} className={fieldClass} />
          </label>
          {initialKartClass !== undefined && (
            <label className="flex flex-col gap-1 text-[11px] text-[#7C8898]">
              Kart class
              <select data-testid="map-kart-class" value={kartClass} onChange={(e) => setKartClass(e.target.value)} className={fieldClass}>
                {KART_CLASSES.map((k) => <option key={k.value} value={k.value}>{k.label}</option>)}
              </select>
            </label>
          )}
          {error && <p role="alert" data-testid="map-name-error" className="text-xs text-[#E5473C]">{error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onClose} className="text-xs px-3 py-2 min-h-[36px] rounded-[2px] border border-[#232B35] text-[#7C8898] cursor-pointer">Cancel</button>
            <button type="submit" data-testid="map-name-submit" disabled={isBusy || blank}
              className="text-xs font-bold px-3 py-2 min-h-[36px] rounded-[2px] bg-[#3FA6E0] text-[#06121B] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
              {isBusy ? "Saving…" : submitText}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
