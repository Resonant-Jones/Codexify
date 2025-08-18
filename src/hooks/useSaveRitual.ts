import { Notes, Agent } from "../dcw-services/gc";
export async function getPins(): Promise<string[]> {
  try {
    const me = await Agent.whoami();
    return me?.pins || [];
  } catch (err) {
    console.error("[useSaveRitual] Failed to get pins:", err);
    throw err;
  }
}

export async function setPins(pins: string[]) {
  try {
    await Agent.updateProfile({ pins });
  } catch (err) {
    console.error("[useSaveRitual] Failed to set pins:", err);
    throw err;
  }
}

export async function savePrimary({
  projectSlug,
  markdown,
  threadId,
  turnIndex,
  autoFormat = false
}: {
  projectSlug: string;
  markdown: string;
  threadId?: string;
  turnIndex?: number;
  autoFormat?: boolean;
}) {
  const idempotencyKey = `${projectSlug}-${threadId || "noThread"}-${Date.now()}`;
  let content = markdown;
  try {
    await Notes.log({
      command: 'save',
      meta: {
        dcw: true,
        project: projectSlug,
        threadId,
        turnIndex,
        target: 'notes/daily',
        remember: true,
        idempotencyKey
      },
      payload: { markdown }
    });
  } catch (err) {
    console.error("[useSaveRitual] Failed to log note:", err);
    throw err;
  }

  if (autoFormat) {
    try {
      const out = await Notes.codexify({
        source: 'chat',
        input: { content: markdown },
        options: { format: 'markdown' }
      });
      content = out.content || markdown;
    } catch (err) {
      console.warn("[useSaveRitual] Codexify formatting failed, using raw markdown:", err);
    }
  }

  // Use local date string in YYYY-MM-DD format
  const today = new Date().toLocaleDateString('en-CA');

  try {
    const res = await Notes.summarize({
      title: `DCW Capture — ${today}`,
      content,
      tags: ['dcw', 'capture'],
      meta: { project: projectSlug, appendPolicy: 'daily', idempotencyKey }
    });
    return { noteId: res.id, path: res.path, content };
  } catch (err) {
    console.error("[useSaveRitual] Failed to summarize note:", err);
    throw err;
  }
}
