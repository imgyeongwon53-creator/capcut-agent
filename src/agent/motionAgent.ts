import Anthropic from "@anthropic-ai/sdk";
import { MotionGraphicProps } from "../compositions/MotionGraphic";

const client = new Anthropic();

interface GenerateMotionGraphicInput {
  prompt: string;
  durationSeconds?: number;
}

interface MotionGraphicConfig extends MotionGraphicProps {
  durationInFrames: number;
  fps: number;
}

const SYSTEM_PROMPT = `You are a motion graphic designer AI. Given a user prompt, generate a JSON configuration for a motion graphic video.

You must return a valid JSON object with these fields:
- title: string (main title text)
- subtitle: string (optional subtitle)
- logoText: string (1-4 character logo/brand text)
- primaryColor: string (hex color like "#6366f1")
- secondaryColor: string (hex color like "#ec4899")
- backgroundColor: string (hex color like "#0f0f1a")
- showAudioVisualizer: boolean
- dataPoints: array of {label: string, value: number} (2-6 items, values 0-100)
- durationInFrames: number (90-300, at 30fps)
- fps: number (always 30)

Design principles:
- Choose colors that match the mood/theme of the prompt
- Data points should represent relevant metrics for the topic
- Duration should match content complexity
- Make it visually compelling and professional

Return ONLY the JSON object, no markdown or explanation.`;

export async function generateMotionGraphicConfig(
  input: GenerateMotionGraphicInput
): Promise<MotionGraphicConfig> {
  const durationFrames = input.durationSeconds
    ? input.durationSeconds * 30
    : 240;

  const response = await client.messages.create({
    model: "claude-opus-4-8",
    max_tokens: 1024,
    thinking: { type: "adaptive" },
    system: SYSTEM_PROMPT,
    messages: [
      {
        role: "user",
        content: `Create a motion graphic for: "${input.prompt}"\nTarget duration: ${durationFrames} frames (${Math.round(durationFrames / 30)}s)`,
      },
    ],
  });

  let jsonText = "";
  for (const block of response.content) {
    if (block.type === "text") {
      jsonText = block.text.trim();
      break;
    }
  }

  // Strip markdown code blocks if present
  jsonText = jsonText.replace(/^```json\s*/i, "").replace(/\s*```$/, "");

  const config = JSON.parse(jsonText) as MotionGraphicConfig;
  return config;
}

export async function generateMotionGraphicWithSections(
  input: GenerateMotionGraphicInput
): Promise<MotionGraphicConfig> {
  const config = await generateMotionGraphicConfig(input);

  // Build default section layout based on duration
  const fps = 30;
  const total = config.durationInFrames;

  config.sections = [
    { type: "logo" as const, startFrame: 0, durationFrames: Math.round(total * 0.22) },
    { type: "title" as const, startFrame: Math.round(total * 0.18), durationFrames: Math.round(total * 0.35) },
    { type: "data" as const, startFrame: Math.round(total * 0.45), durationFrames: Math.round(total * 0.38) },
    { type: "outro" as const, startFrame: Math.round(total * 0.78), durationFrames: Math.round(total * 0.22) },
  ];

  return config;
}
