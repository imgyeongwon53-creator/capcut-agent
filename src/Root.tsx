import React from "react";
import { Composition } from "remotion";
import { MotionGraphic, MotionGraphicProps } from "./compositions/MotionGraphic";

// Load AI-generated config if it exists, otherwise use defaults
let generatedConfig: Partial<MotionGraphicProps & { durationInFrames: number }> = {};
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  generatedConfig = require("./generated-config.json");
} catch {
  // No generated config yet — use defaults
}

const defaultProps: MotionGraphicProps = {
  title: generatedConfig.title ?? "Motion Graphics",
  subtitle: generatedConfig.subtitle ?? "Powered by AI",
  logoText: generatedConfig.logoText ?? "MG",
  primaryColor: generatedConfig.primaryColor ?? "#6366f1",
  secondaryColor: generatedConfig.secondaryColor ?? "#ec4899",
  backgroundColor: generatedConfig.backgroundColor ?? "#0f0f1a",
  showAudioVisualizer: generatedConfig.showAudioVisualizer ?? true,
  dataPoints: generatedConfig.dataPoints ?? [
    { label: "Revenue", value: 85 },
    { label: "Growth", value: 62 },
    { label: "Users", value: 91 },
    { label: "Retention", value: 74 },
  ],
  sections: generatedConfig.sections,
};

const durationInFrames = generatedConfig.durationInFrames ?? 240;

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MotionGraphic"
      component={MotionGraphic}
      durationInFrames={durationInFrames}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={defaultProps}
    />
  );
};
