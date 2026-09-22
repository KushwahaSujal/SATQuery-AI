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
  const pathname = usePathname();
  // The route the drawer was opened on is stored alongside the flag, so "close on
  // navigate" is derived during render instead of being a setState inside an effect
  // (which triggers a cascading render).
  const [state, setState] = useState<{ open: boolean; route: string }>({ open: false, route: pathname });

  const isOpen = state.open && state.route === pathname;

  const open = useCallback(() => setState({ open: true, route: pathname }), [pathname]);
  const close = useCallback(() => setState({ open: false, route: pathname }), [pathname]);
  const toggle = useCallback(
    () => setState((prev) => ({ open: !(prev.open && prev.route === pathname), route: pathname })),
    [pathname],
  );

  // Escape closes it, and the page behind must not scroll while it is over the content.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    window.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, close]);

  const value = useMemo(() => ({ isOpen, open, close, toggle }), [isOpen, open, close, toggle]);

  return <MobileNavContext.Provider value={value}>{children}</MobileNavContext.Provider>;
}
