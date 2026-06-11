import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

interface TextAnimationProps {
  text: string;
  fontSize?: number;
  color?: string;
  fontFamily?: string;
  animationType?: "fadeIn" | "slideUp" | "typewriter" | "bounce";
  startFrame?: number;
}

export const TextAnimation: React.FC<TextAnimationProps> = ({
  text,
  fontSize = 72,
  color = "#ffffff",
  fontFamily = "sans-serif",
  animationType = "slideUp",
  startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const localFrame = frame - startFrame;

  const opacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const slideY = animationType === "slideUp"
    ? interpolate(localFrame, [0, 25], [60, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  const scale = animationType === "bounce"
    ? spring({ frame: localFrame, fps, config: { damping: 8, stiffness: 200 } })
    : 1;

  const visibleText = animationType === "typewriter"
    ? text.slice(0, Math.floor(interpolate(localFrame, [0, fps * 2], [0, text.length], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })))
    : text;

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${slideY}px) scale(${scale})`,
        fontSize,
        color,
        fontFamily,
        fontWeight: "bold",
        textAlign: "center",
        textShadow: "0 2px 20px rgba(0,0,0,0.5)",
      }}
    >
      {visibleText}
    </div>
  );
};
