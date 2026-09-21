"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore } from "react";

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
/** The palette DEFAULT_MODE resolves to, kept separate so it can be compared freely. */
const DEFAULT_RESOLVED: "light" | "dark" = "dark";

function isThemeMode(value: unknown): value is ThemeMode {
  return value === "light" || value === "dark" || value === "system";
}

/*
 * The stored mode is read through useSyncExternalStore rather than copied into state by
 * an effect. Reading it in an effect meant a synchronous setState on mount (a cascading
 * render, and a lint error), and it also made every caller of the old bare `useTheme`
 * hook hold its own independent copy of the mode -- TopBar and the provider only
 * appeared to agree because both wrote classes onto documentElement.
 */
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((l) => l());
}

function subscribeToStoredTheme(onChange: () => void) {
  listeners.add(onChange);
  // `storage` gives cross-tab sync for free.
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

function getStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(themeStorageKey);
    return isThemeMode(stored) ? stored : DEFAULT_MODE;
  } catch {
    // Private windows and blocked site data both throw here.
    return DEFAULT_MODE;
  }
}

/** The server cannot know the viewer's stored choice, so it renders the default. */
function getServerTheme(): ThemeMode {
  return DEFAULT_MODE;
}

function storeTheme(mode: ThemeMode) {
  try {
    localStorage.setItem(themeStorageKey, mode);
  } catch {
    // Persisting the choice is a convenience, not a requirement.
  }
  notify();
}

/* The OS preference is also an external store, so "system" needs no effect either. */
function subscribeToOSPreference(onChange: () => void) {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", onChange);
  return () => mq.removeEventListener("change", onChange);
}

function getOSPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function getServerOSPrefersDark(): boolean {
  return DEFAULT_RESOLVED === "dark";
}

interface ThemeContextValue {
  mode: ThemeMode;
  /** The palette actually applied, with "system" already resolved. */
  resolved: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  mode: DEFAULT_MODE,
  resolved: DEFAULT_RESOLVED,
  setMode: () => {},
});

export const useTheme = (): ThemeContextValue => useContext(ThemeContext);

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const mode = useSyncExternalStore(subscribeToStoredTheme, getStoredTheme, getServerTheme);
  const osPrefersDark = useSyncExternalStore(
    subscribeToOSPreference,
    getOSPrefersDark,
    getServerOSPrefersDark,
  );

  const resolved: "light" | "dark" = mode === "system" ? (osPrefersDark ? "dark" : "light") : mode;

  // Applying a class to documentElement is a genuine side effect on a node outside the
  // React tree, so this one stays an effect -- but it sets no state.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", resolved === "dark");
    root.classList.toggle("light", resolved === "light");
  }, [resolved]);

  const setMode = useCallback((next: ThemeMode) => {
    storeTheme(next);
  }, []);

  const value = useMemo<ThemeContextValue>(() => ({ mode, resolved, setMode }), [mode, resolved, setMode]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
