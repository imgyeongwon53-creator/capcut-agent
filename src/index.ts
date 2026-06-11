#!/usr/bin/env node
import { generateMotionGraphicWithSections } from "./agent/motionAgent";
import * as fs from "fs";
import * as path from "path";

async function main() {
  const prompt = process.argv[2];

  if (!prompt) {
    console.error("사용법: npm run generate \"<프롬프트>\"");
    console.error('예시: npm run generate "2024년 매출 성장 분석 영상"');
    process.exit(1);
  }

  const durationSeconds = process.argv[3] ? parseInt(process.argv[3]) : 8;

  console.log(`\n🎬 모션 그래픽 생성 중: "${prompt}"`);
  console.log(`⏱  목표 길이: ${durationSeconds}초\n`);

  try {
    const config = await generateMotionGraphicWithSections({ prompt, durationSeconds });

    const outputPath = path.join(process.cwd(), "src", "generated-config.json");
    fs.writeFileSync(outputPath, JSON.stringify(config, null, 2), "utf-8");

    console.log("✅ 설정 생성 완료!\n");
    console.log("📋 생성된 설정:");
    console.log(`   제목: ${config.title}`);
    if (config.subtitle) console.log(`   부제: ${config.subtitle}`);
    console.log(`   로고: ${config.logoText}`);
    console.log(`   기본 색상: ${config.primaryColor}`);
    console.log(`   보조 색상: ${config.secondaryColor}`);
    console.log(`   배경 색상: ${config.backgroundColor}`);
    console.log(`   길이: ${config.durationInFrames}프레임 (${Math.round(config.durationInFrames / 30)}초)`);
    if (config.dataPoints?.length) {
      console.log(`   데이터 포인트: ${config.dataPoints.length}개`);
      config.dataPoints.forEach((d) => console.log(`     - ${d.label}: ${d.value}`));
    }

    console.log(`\n📁 설정 저장: ${outputPath}`);
    console.log("\n▶️  미리보기 실행:");
    console.log("   npm run preview");
    console.log("\n🎞️  영상 렌더링:");
    console.log(`   npm run render`);
  } catch (err) {
    console.error("❌ 오류:", err);
    process.exit(1);
  }
}

main();
