import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";

interface LogoAnimationProps {
  text: string;
  primaryColor?: string;
  secondaryColor?: string;
  size?: number;
  startFrame?: number;
}

export const LogoAnimation: React.FC<LogoAnimationProps> = ({
  text,
  primaryColor = "#6366f1",
  secondaryColor = "#ec4899",
  size = 120,
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - startFrame;

  const scale = spring({
    frame: localFrame,
    fps,
    config: { damping: 10, stiffness: 150, mass: 0.8 },
  });

  const rotation = interpolate(localFrame, [0, fps * 2], [0, 360], {
    extrapolateRight: "clamp",
  });

  const opacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ opacity, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      <div
        style={{
          width: size,
          height: size,
          borderRadius: "30%",
          background: `linear-gradient(135deg, ${primaryColor}, ${secondaryColor})`,
          transform: `scale(${scale}) rotate(${rotation}deg)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 40px ${primaryColor}80`,
        }}
      >
        <span style={{ fontSize: size * 0.4, color: "#fff", fontWeight: "bold" }}>
          {text.charAt(0).toUpperCase()}
        </span>
      </div>
      <div
        style={{
          fontSize: size * 0.3,
          fontWeight: "900",
          background: `linear-gradient(135deg, ${primaryColor}, ${secondaryColor})`,
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          transform: `scale(${scale})`,
          letterSpacing: "0.05em",
        }}
      >
        {text}
      </div>
    </div>
  );
};
