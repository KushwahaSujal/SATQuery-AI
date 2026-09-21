"use client";

import React, { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatView } from "@/components/analysis/ChatView";
import { useAnalysisStore } from "@/stores/useAnalysisStore";

function AnalysisContent() {
  const searchParams = useSearchParams();

  const carriedQuery = searchParams.get("q") ?? undefined;

  useEffect(() => {
    // This page used to call resetAnalysis() unconditionally on mount, which wiped
    // `rasters` and `video`. That is why uploading on the home page and landing here
    // left an empty workspace and the same file had to be picked a second time -- the
    // upload did reach the backend, the store just got cleared on arrival.
    // Only start clean when nothing was handed over.
    const store = useAnalysisStore.getState();
    if (!store.hasCarriedOverWork()) {
      store.resetAnalysis();
    }
  }, []);

  return (
    <div className="h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-2)] font-sans overflow-hidden select-none antialiased">
      <TopBar showBrand={true} />

      <div className="min-h-0 flex-1 flex overflow-hidden">
        <Sidebar hideBrand={true} />
        <ChatView initialPrompt={carriedQuery} />
      </div>
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="h-screen w-full bg-[var(--canvas)]" />}>
      <AnalysisContent />
    </Suspense>
  );
}
