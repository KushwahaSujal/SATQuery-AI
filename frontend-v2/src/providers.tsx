"use client";

import { useState, useEffect } from "react";

export type ThemeMode = "light" | "dark" | "system";

export const themeStorageKey = "satquery-theme";

const getStoredTheme = (): ThemeMode => {
  if (typeof window === "undefined") return "system";
  const stored = localStorage.getItem(themeStorageKey);
  return (stored as ThemeMode) || "system";
};

const setStoredTheme = (theme: ThemeMode) => {
  if (typeof window !== "undefined") {
    localStorage.setItem(themeStorageKey, theme);
  }
};

export const useTheme = (): {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
} => {
  const [mode, setMode] = useState<ThemeMode>(getStoredTheme);

  useEffect(() => {
    const root = document.documentElement;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

    if (mode === "light") {
      root.classList.add("light");
      root.classList.remove("dark");
    } else if (mode === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      // system - honor OS preference
      if (prefersDark) {
        root.classList.add("dark");
        root.classList.remove("light");
      } else {
        root.classList.add("light");
        root.classList.remove("dark");
      }
    }
  }, [mode]);

  // Add smooth transition for mode changes
  useEffect(() => {
    const root = document.documentElement;
    root.style.transition = "background-color 0.3s ease, color 0.3s ease";
  }, [mode]);

  const setModeHandler = (newMode: ThemeMode) => {
    setMode(newMode);
    setStoredTheme(newMode);
  };

  return { mode, setMode: setModeHandler };
};

export const ThemeProvider = ({ children }: { children: React.ReactNode }) => {
  const { mode, setMode } = useTheme();

  // Determine icon based on mode
  const moonIcon = (
    <svg
      className="w-5 h-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path
        d="M20.354 15.354A9 9 0 018.455 2.404a9.003 9.003 0 011.404 1.818m-1.51 1.51l.707-.707A7.993 7.993 0 009 16c3.586 0 4.743-.917 6.363-2.73a8.001 8.001 0 01-1.404 1.408z"
      />
    </svg>
  );

  const sunIcon = (
    <svg
      className="w-5 h-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <circle cx="12" cy="12" r="5" />
      <path
        d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h-2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"
      />
    </svg>
  );

  const getIcon = () => {
    if (mode === "light") return sunIcon;
    if (mode === "dark") return moonIcon;
    if (typeof window === "undefined") return moonIcon;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    return prefersDark ? moonIcon : sunIcon;
  };

  return (
    <>
      <div
        style={{ display: "none" }}
        aria-hidden="true"
      >
        <button
          aria-label="Toggle theme"
          onClick={() => {
            // Cycle: light -> dark -> system -> light
            const modes: ThemeMode[] = ["light", "dark", "system"];
            const currentIndex = modes.indexOf(mode);
            const nextIndex = (currentIndex + 1) % modes.length;
            setMode(modes[nextIndex]);
          }}
          className="fixed top-4 right-4 z-50 p-2 rounded-full bg-[var(--surface)] border border-[var(--border)] hover:bg-[var(--surface-hover)] transition-colors"
        >
          {getIcon()}
        </button>
      </div>
      {children}
    </>
  );
};