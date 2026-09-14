"use client";

import { BarChart } from "@mui/x-charts/BarChart";

interface MetricsChartProps {
  confidence: number;
  regions: number;
  pixelsChanged: number;
  areaM2: number;
}

export function MetricsChart({
  confidence,
  regions,
  pixelsChanged,
  areaM2,
}: MetricsChartProps) {
  const data = [
    { label: "Confidence", value: confidence * 100, color: "var(--accent)" },
    { label: "Regions", value: Math.min(regions, 100), color: "var(--cyan)" },
    { label: "Pixels (k)", value: Math.min(pixelsChanged / 1000, 100), color: "var(--green)" },
    { label: "Area (m²)", value: Math.min(areaM2 / 1000, 100), color: "var(--purple)" },
  ];

  return (
    <div className="w-full h-[180px]">
      <BarChart
        xAxis={[{
          scaleType: "band",
          data: data.map(d => d.label),
          tickLabelStyle: {
            fill: "var(--t3)",
            fontSize: 10,
            fontFamily: "var(--font-geist-mono)",
          },
        }]}
        yAxis={[{
          tickLabelStyle: {
            fill: "var(--t4)",
            fontSize: 9,
            fontFamily: "var(--font-geist-mono)",
          },
        }]}
        series={[{
          data: data.map(d => d.value),
          color: "var(--accent)",
        }]}
        height={180}
        margin={{ top: 20, bottom: 30, left: 40, right: 20 }}
        slotProps={{
          bar: {
            rx: 4,
            ry: 4,
          },
        }}
        theme="dark"
      />
    </div>
  );
}
