import fs from "fs";
import path from "path";

const INPUT_DIR = "./logs/raw";
const OUTPUT_FOUNDER = "./logs/founder";
const OUTPUT_PUBLIC = "./logs/public";

function extractSection(content: string, section: string) {
  const regex = new RegExp(`## ${section}([\\s\\S]*?)(\\n## |$)`, "i");
  const match = content.match(regex);
  return match ? match[1].trim() : "";
}

function extractNarrative(content: string) {
  const split = content.split("Narrative Log");
  return split.length > 1 ? split[1].trim() : "";
}

function extractKeySentences(text: string) {
  const sentences = text.split("\n").flatMap(line =>
    line.split(". ").map(s => s.trim())
  );

  return sentences.filter(s =>
    s.length > 80 &&
    (
      s.includes("system") ||
      s.includes("no longer") ||
      s.includes("now") ||
      s.includes("stopped") ||
      s.includes("shift")
    )
  );
}

function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function processFile(filePath: string) {
  const content = fs.readFileSync(filePath, "utf-8");

  const important = extractSection(content, "Important outcome");
  const closing = extractSection(content, "Closing thought");
  const narrative = extractNarrative(content);

  // Founder log output
  const founder = [important, narrative, closing]
    .filter(Boolean)
    .join("\n\n");

  // Public posts
  const publicPosts = [
    ...extractKeySentences(important),
    ...extractKeySentences(narrative)
  ];

  const fileName = path.basename(filePath);

  fs.writeFileSync(
    path.join(OUTPUT_FOUNDER, fileName),
    founder
  );

  fs.writeFileSync(
    path.join(OUTPUT_PUBLIC, fileName),
    publicPosts.join("\n\n---\n\n")
  );
}

function main() {
  ensureDir(INPUT_DIR);
  ensureDir(OUTPUT_FOUNDER);
  ensureDir(OUTPUT_PUBLIC);

  const files = fs.readdirSync(INPUT_DIR);

  files.forEach(file => {
    if (file.endsWith(".md")) {
      processFile(path.join(INPUT_DIR, file));
    }
  });

  console.log("Logs processed.");
}

main();
