interface ConfidenceRingProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  status?: "completed" | "processing" | "failed";
}

export function ConfidenceRing({ value, size = 44, strokeWidth = 3.5, status = "completed" }: ConfidenceRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashArray = `${(value / 100) * circumference}, ${circumference}`;
  const center = size / 2;

  const colorMap = {
    completed: "var(--green)",
    processing: "var(--warning)",
    failed: "var(--error)",
  };

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className={`${size > 40 ? "w-11 h-11" : "w-10 h-10"} transform -rotate-90`} viewBox={`0 0 ${size} ${size}`}>
        <path
          style={{ color: "var(--surface-3)" }}
          d={`M${center} ${strokeWidth / 2} a ${radius} ${radius} 0 0 1 0 ${radius * 2} a ${radius} ${radius} 0 0 1 0 -${radius * 2}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
        />
        <path
          style={{ color: colorMap[status] }}
          d={`M${center} ${strokeWidth / 2} a ${radius} ${radius} 0 0 1 0 ${radius * 2} a ${radius} ${radius} 0 0 1 0 -${radius * 2}`}
          fill="none"
          stroke="currentColor"
          strokeDasharray={dashArray}
          strokeLinecap="round"
          strokeWidth={strokeWidth}
        />
      </svg>
      <span className="absolute text-[11px] font-bold" style={{ color: "var(--heading)" }}>{value}%</span>
    </div>
  );
}
