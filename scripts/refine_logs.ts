import fs from "fs";
import path from "path";

const BASE_URL = "http://localhost:8888";
const API_KEY = process.env.CODEXIFY_API_KEY || "";

const RAW_DIR = "logs/public";
const OUT_DIR = "logs/refined";

function ensureDir(dir: string) {
  fs.mkdirSync(dir, { recursive: true });
}

async function createThread() {
  const res = await fetch(`${BASE_URL}/chat/threads`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({ title: "log-refinement" }),
  });

  const data = await res.json();
  return data.thread_id;
}

async function sendMessage(threadId: number, content: string) {
  await fetch(`${BASE_URL}/chat/${threadId}/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({
      role: "user",
      content,
    }),
  });
}

async function triggerCompletion(threadId: number) {
  await fetch(`${BASE_URL}/chat/${threadId}/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({}),
  });
}

async function waitForCompletion(threadId: number): Promise<string> {
  for (let i = 0; i < 60; i++) {
    await new Promise((r) => setTimeout(r, 2000));

    const res = await fetch(`${BASE_URL}/chat/${threadId}/messages`, {
      headers: { "X-API-Key": API_KEY },
    });

    const data = await res.json();

    const assistant = [...data.messages]
      .reverse()
      .find((m: any) => m.role === "assistant");

    if (assistant) return assistant.content;
  }

  throw new Error("Timeout waiting for completion");
}

async function refineFile(file: string) {
  const inputPath = path.join(RAW_DIR, file);
  const outputPath = path.join(OUT_DIR, file);

  const raw = fs.readFileSync(inputPath, "utf-8");

  const prompt = `Refine the following text for clarity.

Rules:
- Preserve original meaning
- Do not add new claims
- Compress where possible
- Improve readability

---

${raw}`;

  const threadId = await createThread();
  await sendMessage(threadId, prompt);
  await triggerCompletion(threadId);

  const refined = await waitForCompletion(threadId);

  fs.writeFileSync(outputPath, refined);
  console.log(`Refined: ${file}`);
}

async function main() {
  ensureDir(OUT_DIR);

  const files = fs.readdirSync(RAW_DIR).filter(f => f.endsWith(".md"));

  for (const file of files) {
    await refineFile(file);
  }

  console.log("All logs refined.");
}

main();
