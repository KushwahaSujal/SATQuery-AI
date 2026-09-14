"use client";

import { PieChart } from "@mui/x-charts/PieChart";

interface PieMetricsProps {
  confidence: number;
  regions: number;
  pixelsChanged: number;
}

export function PieMetrics({ confidence, regions, pixelsChanged }: PieMetricsProps) {
  const data = [
    { id: 0, value: confidence * 100, label: "Confidence", color: "var(--accent)" },
    { id: 1, value: Math.min(regions, 50), label: "Regions", color: "var(--cyan)" },
    { id: 2, value: Math.min(pixelsChanged / 100, 50), label: "Pixels", color: "var(--green)" },
  ];

  return (
    <div className="w-full h-[160px]">
      <PieChart
        series={[
          {
            data,
            innerRadius: 40,
            outerRadius: 70,
            paddingAngle: 2,
            cornerRadius: 4,
            highlightScope: { fade: "global", highlight: "item" },
            faded: { innerRadius: 35, additionalRadius: -5, color: "gray" },
          },
        ]}
        height={160}
        margin={{ top: 10, bottom: 10, left: 10, right: 10 }}
      />
    </div>
  );
}
