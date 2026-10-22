/**
 * Trackside — Settings no longer holds any demo controls (H2).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../../../context/PreferencesContext", () => ({
  usePreferences: () => ({ fontSize: "medium", isSettingsOpen: true, closeSettings: vi.fn(), updatePreferences: vi.fn(), replayTutorial: vi.fn() }),
}));

import { SettingsModal } from "../settings-modal";

describe("Settings modal", () => {
  it("has text size and tutorial settings but no Demo Tools section, even with the demo switch on", () => {
    vi.stubEnv("VITE_ENABLE_DEMO_TOOLS", "true");
    render(<SettingsModal />);
    expect(screen.getByTestId("settings-font-size-m")).toBeTruthy();
    expect(screen.getByTestId("settings-replay-tutorial-btn")).toBeTruthy();
    expect(screen.queryByTestId("settings-open-demo-visualizer-btn")).toBeNull();
    expect(document.body.textContent).not.toContain("DEMO TOOLS");
    expect(document.body.textContent).not.toContain("Visualizer");
    vi.unstubAllEnvs();
  });
});
