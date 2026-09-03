"use client";

import React from "react";
import { Satellite, Cpu, Activity, ShieldCheck } from "lucide-react";

interface HeaderProps {
  device?: string;
  isHealthy: boolean;
}

export const Header: React.FC<HeaderProps> = ({ device = "Auto", isHealthy }) => {
  return (
    <header className="border-b border-surfaceBorder bg-surface/80 backdrop-blur-md px-6 py-4 sticky top-0 z-50 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-gradient-to-tr from-blue-600 to-cyan-500 rounded-lg shadow-lg shadow-blue-500/20 text-white">
          <Satellite className="w-6 h-6" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight text-white">SATQUERY AI</h1>
            <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-blue-500/20 text-blue-400 border border-blue-500/30">
              v1.0.0
            </span>
          </div>
          <p className="text-xs text-slate-400 font-medium">Agentic Remote-Sensing Intelligence</p>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-900/80 border border-slate-800 text-xs font-mono text-slate-300">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>Device: <span className="text-cyan-300 font-bold uppercase">{device}</span></span>
        </div>

        <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-md bg-slate-900/80 border border-slate-800 text-xs font-mono">
          <Activity className={`w-3.5 h-3.5 ${isHealthy ? "text-emerald-400 animate-pulse" : "text-rose-400"}`} />
          <span className={isHealthy ? "text-emerald-400 font-medium" : "text-rose-400 font-medium"}>
            {isHealthy ? "BACKEND ONLINE" : "OFFLINE"}
          </span>
        </div>
      </div>
    </header>
  );
};
