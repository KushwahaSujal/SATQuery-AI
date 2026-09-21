"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";

export const themeStorageKey = "satquery-theme";

/**
 * The app defaults to DARK rather than following prefers-color-scheme.
 *
 * The whole design language -- scan sweep, accent glow, the satellite HUD -- is built
 * for the dark palette, and demo laptops, projectors and headless screenshot runs all
 * commonly report a light preference. Defaulting to "system" meant those all got the
 * light palette by accident. A viewer can still pick light explicitly, and that choice
 * persists; "system" remains available but is no longer the default.
 */
const DEFAULT_MODE: ThemeMode = "dark";

function isThemeMode(value: unknown): value is ThemeMode {
  return value === "light" || value === "dark" || value === "system";
}

function readStoredTheme(): ThemeMode | null {
  try {
    const stored = localStorage.getItem(themeStorageKey);
    return isThemeMode(stored) ? stored : null;
  } catch {
    // Private windows and blocked site data both throw here.
    return null;
  }
}

function storeTheme(mode: ThemeMode) {
  try {
    localStorage.setItem(themeStorageKey, mode);
  } catch {
    // Persisting the choice is a convenience, not a requirement.
  }
}

/** Resolve "system" to a concrete palette. */
function resolveMode(mode: ThemeMode): "light" | "dark" {
  if (mode !== "system") return mode;
  if (typeof window === "undefined") return DEFAULT_MODE === "light" ? "light" : "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

interface ThemeContextValue {
  mode: ThemeMode;
  /** The palette actually applied, with "system" already resolved. */
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
}

/*
 * This is a context, not a bare hook. It used to be a plain hook holding its own
 * useState, so every caller (TopBar and the provider itself) had a SEPARATE copy of
 * the theme state and they only appeared to agree because each one's effect wrote
 * classes onto documentElement. Two consumers could disagree about the current mode
 * while both mutating the same DOM node.
 */
const ThemeContext = createContext<ThemeContextValue>({
  mode: DEFAULT_MODE,
  resolved: resolveMode(DEFAULT_MODE),
  setMode: () => {},
});

export const useTheme = (): ThemeContextValue => useContext(ThemeContext);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  // Keep the first client render identical to the server render; localStorage is
  // read only after hydration.
  const [mode, setModeState] = useState<ThemeMode>(DEFAULT_MODE);
  const [resolved, setResolved] = useState<"light" | "dark">(() => resolveMode(DEFAULT_MODE));

  useEffect(() => {
    const stored = readStoredTheme();
    if (stored) setModeState(stored);
  }, []);

  // Apply the palette, and keep following the OS only while mode is "system".
  useEffect(() => {
    const root = document.documentElement;
    const apply = () => {
      const next = resolveMode(mode);
      setResolved(next);
      root.classList.toggle("dark", next === "dark");
      root.classList.toggle("light", next === "light");
    };
    apply();

    if (mode !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, [mode]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    storeTheme(next);
  }, []);

  const value = useMemo<ThemeContextValue>(() => ({ mode, resolved, setMode }), [mode, resolved, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
