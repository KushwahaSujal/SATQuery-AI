"use client";

import React, { useState } from "react";
import { ListTree, CheckCircle2, AlertCircle, Clock, ChevronDown, ChevronRight } from "lucide-react";

export interface ExecutionStepItem {
  timestamp: string;
  step: string;
  status: string;
  duration_ms?: number | null;
  details?: string | null;
}

interface TracePanelProps {
  trace: ExecutionStepItem[];
}

export const TracePanel: React.FC<TracePanelProps> = ({ trace }) => {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);

  if (!trace || trace.length === 0) return null;

  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-3">
      <div className="flex items-center space-x-2">
        <ListTree className="w-4 h-4 text-cyan-400" />
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
          Observable Execution Trace
        </h2>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {trace.map((step, idx) => {
          const isExpanded = expandedIdx === idx;
          const timeFormatted = step.timestamp.split("T")[-1]?.replace("Z", "") || step.timestamp;

          return (
            <div
              key={idx}
              className="bg-slate-900/70 border border-slate-800 rounded-lg p-2.5 text-xs font-mono transition-colors hover:bg-slate-900"
            >
              <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpandedIdx(isExpanded ? null : idx)}
              >
                <div className="flex items-center space-x-2">
                  {step.status === "success" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                  )}
                  <span className="font-semibold text-slate-200">{step.step}</span>
                </div>

                <div className="flex items-center space-x-2 text-slate-400">
                  {step.duration_ms !== null && step.duration_ms !== undefined && (
                    <span className="text-[10px] text-cyan-400 bg-cyan-950/40 px-1.5 py-0.5 rounded border border-cyan-800/50">
                      {step.duration_ms.toFixed(1)}ms
                    </span>
                  )}
                  <span className="text-[10px] text-slate-500">{timeFormatted}</span>
                  {step.details && (
                    isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
                  )}
                </div>
              </div>

              {isExpanded && step.details && (
                <div className="mt-2 pt-2 border-t border-slate-800 text-slate-400 text-[11px] font-sans">
                  {step.details}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
