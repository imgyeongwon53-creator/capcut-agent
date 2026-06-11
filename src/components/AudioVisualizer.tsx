import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

interface AudioVisualizerProps {
  barCount?: number;
  color?: string;
  secondaryColor?: string;
  height?: number;
  startFrame?: number;
}

// Pseudo-random bar heights that simulate audio waveform
function pseudoRandom(frame: number, index: number): number {
  const seed = Math.sin(frame * 0.15 + index * 1.7) * Math.cos(frame * 0.08 + index * 0.9);
  return Math.abs(seed);
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
  barCount = 40,
  color = "#6366f1",
  secondaryColor = "#ec4899",
  height = 120,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - startFrame;

  const opacity = interpolate(localFrame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        display: "flex",
        alignItems: "center",
        gap: 4,
        height,
      }}
    >
      {Array.from({ length: barCount }, (_, i) => {
        const amplitude = pseudoRandom(localFrame, i);
        const barHeight = interpolate(amplitude, [0, 1], [8, height * 0.9]);
        const t = i / barCount;
        const r1 = parseInt(color.slice(1, 3), 16);
        const g1 = parseInt(color.slice(3, 5), 16);
        const b1 = parseInt(color.slice(5, 7), 16);
        const r2 = parseInt(secondaryColor.slice(1, 3), 16);
        const g2 = parseInt(secondaryColor.slice(3, 5), 16);
        const b2 = parseInt(secondaryColor.slice(5, 7), 16);
        const r = Math.round(r1 + (r2 - r1) * t);
        const g = Math.round(g1 + (g2 - g1) * t);
        const b = Math.round(b1 + (b2 - b1) * t);
        const barColor = `rgb(${r},${g},${b})`;

        return (
          <div
            key={i}
            style={{
              flex: 1,
              height: barHeight,
              background: barColor,
              borderRadius: 4,
              boxShadow: `0 0 8px ${barColor}80`,
            }}
          />
        );
      })}
    </div>
  );
};
