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

  const color = status === "failed" ? "text-rose-400" : status === "processing" ? "text-amber-400" : "text-emerald-400";
  const textColor = status === "failed" ? "text-amber-300" : status === "processing" ? "text-amber-300" : "text-white";

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className={`${size > 40 ? "w-11 h-11" : "w-10 h-10"} transform -rotate-90`} viewBox={`0 0 ${size} ${size}`}>
        <path
          className="text-[#10223b]"
          d={`M${center} ${strokeWidth / 2} a ${radius} ${radius} 0 0 1 0 ${radius * 2} a ${radius} ${radius} 0 0 1 0 -${radius * 2}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
        />
        <path
          className={color}
          d={`M${center} ${strokeWidth / 2} a ${radius} ${radius} 0 0 1 0 ${radius * 2} a ${radius} ${radius} 0 0 1 0 -${radius * 2}`}
          fill="none"
          stroke="currentColor"
          strokeDasharray={dashArray}
          strokeLinecap="round"
          strokeWidth={strokeWidth}
        />
      </svg>
      <span className={`absolute text-[11px] font-bold ${textColor}`}>{value}%</span>
    </div>
  );
}
