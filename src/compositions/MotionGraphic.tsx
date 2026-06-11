import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig, interpolate, useCurrentFrame } from "remotion";
import { TextAnimation } from "../components/TextAnimation";
import { LogoAnimation } from "../components/LogoAnimation";
import { DataVisualization } from "../components/DataVisualization";
import { AudioVisualizer } from "../components/AudioVisualizer";

export interface MotionGraphicProps {
  title?: string;
  subtitle?: string;
  logoText?: string;
  primaryColor?: string;
  secondaryColor?: string;
  backgroundColor?: string;
  dataPoints?: Array<{ label: string; value: number; color?: string }>;
  showAudioVisualizer?: boolean;
  sections?: Array<{
    type: "title" | "logo" | "data" | "outro";
    startFrame: number;
    durationFrames: number;
  }>;
}

export const MotionGraphic: React.FC<MotionGraphicProps> = ({
  title,
  subtitle = "",
  logoText = "MG",
  primaryColor = "#6366f1",
  secondaryColor = "#ec4899",
  backgroundColor = "#0f0f1a",
  dataPoints = [],
  showAudioVisualizer = true,
  sections,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Default section layout if not provided
  const defaultSections = [
    { type: "logo" as const, startFrame: 0, durationFrames: 60 },
    { type: "title" as const, startFrame: 50, durationFrames: 90 },
    { type: "data" as const, startFrame: 120, durationFrames: 100 },
    { type: "outro" as const, startFrame: 200, durationFrames: 40 },
  ];
  const activeSections = sections ?? defaultSections;

  // Fade out at end
  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const particleCount = 20;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(ellipse at center, ${primaryColor}22 0%, ${backgroundColor} 70%)`,
        opacity: fadeOut,
      }}
    >
      {/* Background particles */}
      {Array.from({ length: particleCount }, (_, i) => {
        const x = ((i * 137.5) % 100);
        const y = ((i * 97.3) % 100);
        const size = 2 + (i % 4);
        const speed = 0.3 + (i % 5) * 0.1;
        const offset = (i * 17) % 100;
        const opacity = 0.2 + (Math.sin(frame * speed * 0.05 + offset) + 1) * 0.15;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${(y + frame * speed * 0.02 + offset) % 100}%`,
              width: size,
              height: size,
              borderRadius: "50%",
              background: i % 2 === 0 ? primaryColor : secondaryColor,
              opacity,
            }}
          />
        );
      })}

      {/* Logo section */}
      {activeSections.filter((s) => s.type === "logo").map((s, i) => (
        <Sequence key={i} from={s.startFrame} durationInFrames={s.durationFrames + 60}>
          <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
            <LogoAnimation
              text={logoText}
              primaryColor={primaryColor}
              secondaryColor={secondaryColor}
              startFrame={0}
            />
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* Title section */}
      {activeSections.filter((s) => s.type === "title").map((s, i) => (
        <Sequence key={i} from={s.startFrame} durationInFrames={s.durationFrames + 60}>
          <AbsoluteFill
            style={{
              alignItems: "center",
              justifyContent: "center",
              flexDirection: "column",
              gap: 24,
              padding: "0 80px",
            }}
          >
            <TextAnimation
              text={title ?? ""}
              fontSize={80}
              color="#ffffff"
              animationType="slideUp"
              startFrame={0}
            />
            {subtitle && (
              <TextAnimation
                text={subtitle}
                fontSize={40}
                color={primaryColor}
                animationType="fadeIn"
                startFrame={20}
              />
            )}
          </AbsoluteFill>
        </Sequence>
      ))}

      {/* Data section */}
      {dataPoints.length > 0 &&
        activeSections.filter((s) => s.type === "data").map((s, i) => (
          <Sequence key={i} from={s.startFrame} durationInFrames={s.durationFrames + 60}>
            <AbsoluteFill
              style={{ alignItems: "center", justifyContent: "center", padding: "0 80px" }}
            >
              <DataVisualization data={dataPoints} title="Data" startFrame={0} />
            </AbsoluteFill>
          </Sequence>
        ))}

      {/* Audio visualizer */}
      {showAudioVisualizer && (
        <AbsoluteFill style={{ justifyContent: "flex-end", padding: "0 60px 40px" }}>
          <AudioVisualizer
            color={primaryColor}
            secondaryColor={secondaryColor}
            startFrame={0}
          />
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
