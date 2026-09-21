"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { usePathname } from "next/navigation";

/**
 * Open/closed state for the mobile navigation drawer.
 *
 * Pages render <TopBar /> and <Sidebar /> as siblings, so the hamburger and the drawer
 * it controls live in different subtrees. A context is the only way for them to share
 * state without every page having to thread a prop pair through.
 */
interface MobileNavContextValue {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

const MobileNavContext = createContext<MobileNavContextValue>({
  isOpen: false,
  open: () => {},
  close: () => {},
  toggle: () => {},
});

export const useMobileNav = (): MobileNavContextValue => useContext(MobileNavContext);

export function MobileNavProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((v) => !v), []);

  // Navigating is the most common way to finish with the drawer.
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // Escape closes it, and the page behind must not scroll while it is over the content.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen]);

  const value = useMemo(() => ({ isOpen, open, close, toggle }), [isOpen, open, close, toggle]);

  return <MobileNavContext.Provider value={value}>{children}</MobileNavContext.Provider>;
}
