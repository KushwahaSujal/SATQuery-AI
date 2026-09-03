"use client";

import React from "react";
import { Cpu, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export interface ModelCapability {
  name: string;
  version?: string | null;
  task: string;
  supported_tasks: string[];
  supported_modalities: string[];
  input_count: number;
  input_relationship: string;
  checkpoint_path?: string | null;
  available: boolean;
  device: string;
}

interface ModelStatusPanelProps {
  models: ModelCapability[];
}

export const ModelStatusPanel: React.FC<ModelStatusPanelProps> = ({ models }) => {
  return (
    <div className="bg-surface rounded-xl border border-surfaceBorder p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200">
            Model Adapter Registry & Runtime Status
          </h2>
        </div>
        <span className="text-xs text-slate-400">Real Runtime Availability (No Synthetic Status)</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {models.map((m, idx) => (
          <div
            key={idx}
            className="bg-slate-900/80 border border-slate-800 rounded-lg p-3 text-xs space-y-2 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-bold text-white text-sm">{m.name}</span>
                {m.available ? (
                  <span className="flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>READY</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    <XCircle className="w-3 h-3 text-slate-500" />
                    <span>NOT CONFIGURED</span>
                  </span>
                )}
              </div>

              <div className="text-[11px] text-slate-400 font-mono">
                Task: <span className="text-slate-300 font-semibold">{m.task}</span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono flex justify-between">
              <span>Inputs: {m.input_count} ({m.input_relationship})</span>
              <span>Dev: {m.device}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
