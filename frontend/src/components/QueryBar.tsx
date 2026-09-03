"use client";

import React from "react";
import { Search, Loader2, Sparkles } from "lucide-react";

interface QueryBarProps {
  query: string;
  isAnalyzing: boolean;
  canAnalyze: boolean;
  onChange: (q: string) => void;
  onSubmit: () => void;
}

const EXAMPLE_QUERIES = [
  "Describe the land-cover and major infrastructure visible in this image.",
  "Highlight the water body and solar panels.",
  "What changed between these two acquisition dates? Has the built-up area increased?",
  "Use the optical and SAR images together to identify built-up and water-covered regions.",
];

export const QueryBar: React.FC<QueryBarProps> = ({
  query,
  isAnalyzing,
  canAnalyze,
  onChange,
  onSubmit,
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && canAnalyze && !isAnalyzing) {
      onSubmit();
    }
  };

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-3">
      <div className="flex items-center space-x-2">
        <Sparkles className="w-4 h-4 text-amber-400" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">Natural-Language Query</h2>
      </div>

      <div className="flex space-x-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, request grounding, or analyze bi-temporal/cross-modal changes..."
            className="w-full bg-slate-900/90 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        <button
          onClick={onSubmit}
          disabled={!canAnalyze || isAnalyzing}
          className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-bold text-sm transition-all duration-200 ${
            canAnalyze && !isAnalyzing
              ? "bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-lg shadow-blue-500/25 cursor-pointer"
              : "bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed"
          }`}
        >
          {isAnalyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <Search className="w-4 h-4" />
              <span>Execute</span>
            </>
          )}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <span className="text-[11px] font-semibold text-slate-500 mr-1">Examples:</span>
        {EXAMPLE_QUERIES.map((ex, idx) => (
          <button
            key={idx}
            onClick={() => onChange(ex)}
            className="text-[11px] px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
          >
            {ex.length > 55 ? `${ex.substring(0, 55)}...` : ex}
          </button>
        ))}
      </div>
    </div>
  );
};
