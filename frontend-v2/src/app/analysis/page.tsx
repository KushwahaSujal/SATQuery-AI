"use client";

import React, { Suspense } from "react";
import { TopBar } from "@/components/layout/TopBar";
import { Sidebar } from "@/components/layout/Sidebar";
import { ChatView } from "@/components/analysis/ChatView";

function AnalysisContent() {
  return (
    <div className="h-screen w-full flex flex-col bg-[var(--canvas)] text-[var(--text-2)] font-sans overflow-hidden select-none antialiased">
      <TopBar showBrand={true} />

      <div className="min-h-0 flex-1 flex overflow-hidden">
        <Sidebar hideBrand={true} />
        <ChatView />
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
