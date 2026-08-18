/**
 * Trackside — Preferences & Settings Context
 *
 * Provides application-wide user display preferences synced with the backend server API:
 * - Font Size: small, medium, large, xlarge
 * - Tutorial Completed: per-user persistence across sessions/devices
 * - Replay Tutorial action & Settings Modal open/close state
 */

import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "../lib/api";

export type FontSizePreset = "small" | "medium" | "large" | "xlarge";

interface UserPreferences {
  font_size: FontSizePreset;
  tutorial_completed: boolean;
}

interface PreferencesContextType {
  fontSize: FontSizePreset;
  tutorialCompleted: boolean;
  isSettingsOpen: boolean;
  openSettings: () => void;
  closeSettings: () => void;
  updatePreferences: (newPrefs: Partial<UserPreferences>) => Promise<void>;
  replayTutorial: () => Promise<void>;
}

const PreferencesContext = createContext<PreferencesContextType | undefined>(undefined);

export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [fontSize, setFontSize] = useState<FontSizePreset>("medium");
  const [tutorialCompleted, setTutorialCompleted] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

  // Apply font size preset to root element across the whole application
  const applyFontSizeScale = (preset: FontSizePreset) => {
    const scaleMap: Record<FontSizePreset, string> = {
      small: "14px",
      medium: "16px",
      large: "18px",
      xlarge: "20px",
    };
    document.documentElement.style.fontSize = scaleMap[preset] || "16px";
  };

  // Load preferences from backend API on mount
  useEffect(() => {
    async function loadPreferences() {
      try {
        const data = await api.get<UserPreferences>("/api/preferences/me/");
        if (data) {
          if (data.font_size) {
            setFontSize(data.font_size);
            applyFontSizeScale(data.font_size);
          }
          if (typeof data.tutorial_completed === "boolean") {
            setTutorialCompleted(data.tutorial_completed);
          }
        }
      } catch (err) {
        console.warn("Could not load backend user preferences, using defaults:", err);
      }
    }
    loadPreferences();
  }, []);

  const openSettings = () => setIsSettingsOpen(true);
  const closeSettings = () => setIsSettingsOpen(false);

  const updatePreferences = async (newPrefs: Partial<UserPreferences>) => {
    // Update local state immediately for instant feedback
    if (newPrefs.font_size) {
      setFontSize(newPrefs.font_size);
      applyFontSizeScale(newPrefs.font_size);
    }
    if (typeof newPrefs.tutorial_completed === "boolean") {
      setTutorialCompleted(newPrefs.tutorial_completed);
    }

    // Persist to backend server API
    try {
      await api.patch<UserPreferences>("/api/preferences/me/", newPrefs);
    } catch (err) {
      console.warn("Failed saving user preferences to backend:", err);
    }
  };

  const replayTutorial = async () => {
    setTutorialCompleted(false);
    setIsSettingsOpen(false);
    try {
      await api.patch<UserPreferences>("/api/preferences/me/", { tutorial_completed: false });
    } catch (err) {
      console.warn("Failed resetting tutorial completed state on backend:", err);
    }
  };

  return (
    <PreferencesContext.Provider
      value={{
        fontSize,
        tutorialCompleted,
        isSettingsOpen,
        openSettings,
        closeSettings,
        updatePreferences,
        replayTutorial,
      }}
    >
      {children}
    </PreferencesContext.Provider>
  );
}


export function usePreferences() {
  const context = useContext(PreferencesContext);
  if (!context) {
    throw new Error("usePreferences must be used within a PreferencesProvider");
  }
  return context;
}
