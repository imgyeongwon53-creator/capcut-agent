import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

interface DataVisualizationProps {
  data: DataPoint[];
  title?: string;
  startFrame?: number;
  maxValue?: number;
}

const DEFAULT_COLORS = ["#6366f1", "#ec4899", "#10b981", "#f59e0b", "#3b82f6"];

export const DataVisualization: React.FC<DataVisualizationProps> = ({
  data,
  title,
  startFrame = 0,
  maxValue,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - startFrame;
  const max = maxValue ?? Math.max(...data.map((d) => d.value));

  const progress = interpolate(localFrame, [0, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleOpacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ width: "100%", padding: "0 40px" }}>
      {title && (
        <div
          style={{
            fontSize: 36,
            fontWeight: "bold",
            color: "#fff",
            marginBottom: 32,
            opacity: titleOpacity,
            textAlign: "center",
          }}
        >
          {title}
        </div>
      )}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {data.map((item, i) => {
          const barProgress = interpolate(
            localFrame,
            [i * 8, i * 8 + 40],
            [0, item.value / max],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          ) * progress;

          const color = item.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length];
          const labelOpacity = interpolate(localFrame, [i * 8, i * 8 + 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          return (
            <div key={i} style={{ opacity: labelOpacity }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ color: "#e2e8f0", fontSize: 20 }}>{item.label}</span>
                <span style={{ color, fontSize: 20, fontWeight: "bold" }}>
                  {Math.round(item.value * barProgress / (item.value / max))}
                </span>
              </div>
              <div style={{ background: "rgba(255,255,255,0.1)", borderRadius: 8, height: 24 }}>
                <div
                  style={{
                    width: `${barProgress * 100}%`,
                    height: "100%",
                    background: `linear-gradient(90deg, ${color}80, ${color})`,
                    borderRadius: 8,
                    boxShadow: `0 0 12px ${color}60`,
                    transition: "width 0.1s",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
