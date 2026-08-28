import type { ImageContent, TextContent, Usage } from "@earendil-works/pi-ai";
import type { AgentMessage } from "../../types.ts";
import type { CustomEntry, SessionContext, SessionEntryCursorOptions, SessionMetadata, SessionStats, SessionStorage, SessionTreeEntry } from "../types.ts";
export type ContextEntryTransform = (entries: readonly SessionTreeEntry[]) => readonly SessionTreeEntry[];
export type CustomEntryContextMessageProjector = (entry: CustomEntry, index: number, entries: readonly SessionTreeEntry[]) => readonly AgentMessage[] | undefined;
export interface SessionContextBuildOptions {
    /** Additional entry transforms applied after the default compaction transform. */
    entryTransforms?: readonly ContextEntryTransform[];
    /** Optional custom-entry projectors. Custom entries are omitted from model context by default. */
    entryProjectors?: Readonly<Record<string, CustomEntryContextMessageProjector>>;
}
export declare function defaultContextEntryTransform(pathEntries: readonly SessionTreeEntry[]): SessionTreeEntry[];
export declare function buildContextEntries(pathEntries: readonly SessionTreeEntry[], options?: SessionContextBuildOptions): SessionTreeEntry[];
export declare function sessionEntryToContextMessages(entry: SessionTreeEntry, index: number, entries: readonly SessionTreeEntry[], options?: SessionContextBuildOptions): AgentMessage[];
export declare function buildSessionContext(pathEntries: readonly SessionTreeEntry[], options?: SessionContextBuildOptions): SessionContext;
export declare class Session<TMetadata extends SessionMetadata = SessionMetadata> {
    private storage;
    private contextBuildOptions;
    constructor(storage: SessionStorage<TMetadata>, contextBuildOptions?: SessionContextBuildOptions);
    getMetadata(): Promise<TMetadata>;
    getStorage(): SessionStorage<TMetadata>;
    getLeafId(): Promise<string | null>;
    getEntry(id: string): Promise<SessionTreeEntry | undefined>;
    getEntries(options?: SessionEntryCursorOptions): Promise<SessionTreeEntry[]>;
    getBranch(fromId?: string): Promise<SessionTreeEntry[]>;
    buildContextEntries(options?: SessionContextBuildOptions): Promise<SessionTreeEntry[]>;
    buildContext(options?: SessionContextBuildOptions): Promise<SessionContext>;
    private mergeContextBuildOptions;
    getLabel(id: string): Promise<string | undefined>;
    getSessionStats(): Promise<SessionStats>;
    getSessionName(): Promise<string | undefined>;
    private appendTypedEntry;
    appendMessage(message: AgentMessage): Promise<string>;
    appendThinkingLevelChange(thinkingLevel: string): Promise<string>;
    appendModelChange(provider: string, modelId: string): Promise<string>;
    appendActiveToolsChange(activeToolNames: string[]): Promise<string>;
    appendCompaction<T = unknown>(summary: string, firstKeptEntryId: string | undefined, tokensBefore: number, details?: T, fromHook?: boolean, usage?: Usage, retainedTail?: AgentMessage[]): Promise<string>;
    appendCustomEntry(customType: string, data?: unknown): Promise<string>;
    appendCustomMessageEntry<T = unknown>(customType: string, content: string | (TextContent | ImageContent)[], display: boolean, details?: T): Promise<string>;
    appendLabel(targetId: string, label: string | undefined): Promise<string>;
    appendSessionName(name: string): Promise<string>;
    moveTo(entryId: string | null, summary?: {
        summary: string;
        details?: unknown;
        usage?: Usage;
        fromHook?: boolean;
    }): Promise<string | undefined>;
}
//# sourceMappingURL=session.d.ts.map