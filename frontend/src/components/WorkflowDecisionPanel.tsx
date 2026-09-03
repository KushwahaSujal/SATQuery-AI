"use client";

import React from "react";
import { GitFork, Cpu, CheckCircle, HelpCircle } from "lucide-react";

interface WorkflowDecisionPanelProps {
  workflowId?: string;
  task?: string;
  reason?: string;
  selectedModels: string[];
}

export const WorkflowDecisionPanel: React.FC<WorkflowDecisionPanelProps> = ({
  workflowId,
  task,
  reason,
  selectedModels,
}) => {
  if (!workflowId || !task) return null;

  return (
    <div className="bg-gradient-to-r from-blue-950/40 via-slate-900 to-slate-900 border border-blue-500/30 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 rounded-md bg-blue-500/20 text-blue-400">
            <GitFork className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Agent Workflow Decision
          </h3>
        </div>
        <span className="text-xs font-mono uppercase px-2.5 py-1 rounded-full font-bold bg-blue-500/20 text-blue-300 border border-blue-500/40">
          {task.replace(/_/g, " ")}
        </span>
      </div>

      <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800 text-xs mb-3">
        <div className="text-slate-400 font-semibold mb-1">Observable Selection Reason:</div>
        <p className="text-slate-200 leading-relaxed font-sans">{reason}</p>
      </div>

      <div className="flex items-center space-x-2 text-xs">
        <span className="text-slate-400 font-semibold">Planned Models:</span>
        <div className="flex flex-wrap gap-1.5">
          {selectedModels.map((m, idx) => (
            <span
              key={idx}
              className="px-2 py-0.5 rounded font-mono font-bold bg-slate-800 text-cyan-300 border border-slate-700"
            >
              {m}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
