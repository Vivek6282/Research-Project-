/**
 * Trackside — Mini Telemetry Chart Component
 *
 * Smooth Recharts AreaChart with gradient fills for speed, G-force,
 * heart rate, and SpO2.
 */

import {
  AreaChart,
  Area,
  YAxis,
  XAxis,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  t: number;
  v: number;
}

interface MiniChartProps {
  data: DataPoint[];
  color: string;
  height?: number;
  id?: string;
}

export function MiniChart({ data, color, height = 54, id = "chart-grad" }: MiniChartProps) {
  const gradientId = `grad-${id}-${color.replace("#", "")}`;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.35} />
            <stop offset="95%" stopColor={color} stopOpacity={0.0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="v"
          stroke={color}
          strokeWidth={2}
          fillOpacity={1}
          fill={`url(#${gradientId})`}
          isAnimationActive={false}
        />
        <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
        <XAxis hide dataKey="t" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
