import { createBranchSummaryMessage, createCompactionSummaryMessage, createCustomMessage } from "../messages.js";
import { SessionError } from "../types.js";
function deriveSessionContextState(pathEntries) {
    let thinkingLevel = "off";
    let model = null;
    let activeToolNames = null;
    for (const entry of pathEntries) {
        if (entry.type === "thinking_level_change") {
            thinkingLevel = entry.thinkingLevel;
        }
        else if (entry.type === "model_change") {
            model = { provider: entry.provider, modelId: entry.modelId };
        }
        else if (entry.type === "message" && entry.message.role === "assistant") {
            model = { provider: entry.message.provider, modelId: entry.message.model };
        }
        else if (entry.type === "active_tools_change") {
            activeToolNames = [...entry.activeToolNames];
        }
    }
    return { thinkingLevel, model, activeToolNames };
}
export function defaultContextEntryTransform(pathEntries) {
    let compaction = null;
    for (const entry of pathEntries) {
        if (entry.type === "compaction") {
            compaction = entry;
        }
    }
    if (!compaction) {
        return [...pathEntries];
    }
    const entries = [compaction];
    const compactionIdx = pathEntries.findIndex((entry) => entry.type === "compaction" && entry.id === compaction.id);
    if (compaction.retainedTail) {
        for (let i = compactionIdx + 1; i < pathEntries.length; i++) {
            entries.push(pathEntries[i]);
        }
        return entries;
    }
    if (compaction.firstKeptEntryId) {
        let foundFirstKept = false;
        for (let i = 0; i < compactionIdx; i++) {
            const entry = pathEntries[i];
            if (entry.id === compaction.firstKeptEntryId)
                foundFirstKept = true;
            if (foundFirstKept)
                entries.push(entry);
        }
    }
    for (let i = compactionIdx + 1; i < pathEntries.length; i++) {
        entries.push(pathEntries[i]);
    }
    return entries;
}
export function buildContextEntries(pathEntries, options = {}) {
    let entries = defaultContextEntryTransform(pathEntries);
    for (const transform of options.entryTransforms ?? []) {
        entries = [...transform(entries)];
    }
    return entries;
}
export function sessionEntryToContextMessages(entry, index, entries, options = {}) {
    if (entry.type === "message") {
        return [entry.message];
    }
    if (entry.type === "custom_message") {
        return [
            createCustomMessage(entry.customType, entry.content, entry.display, entry.details, entry.timestamp),
        ];
    }
    if (entry.type === "compaction") {
        return [
            createCompactionSummaryMessage(entry.summary, entry.tokensBefore, entry.timestamp),
            ...(entry.retainedTail ?? []),
        ];
    }
    if (entry.type === "branch_summary" && entry.summary) {
        return [createBranchSummaryMessage(entry.summary, entry.fromId, entry.timestamp)];
    }
    if (entry.type === "custom") {
        return [...(options.entryProjectors?.[entry.customType]?.(entry, index, entries) ?? [])];
    }
    return [];
}
export function buildSessionContext(pathEntries, options = {}) {
    const state = deriveSessionContextState(pathEntries);
    const contextEntries = buildContextEntries(pathEntries, options);
    const messages = contextEntries.flatMap((entry, index) => sessionEntryToContextMessages(entry, index, contextEntries, options));
    return { ...state, messages };
}
export class Session {
    storage;
    contextBuildOptions;
    constructor(storage, contextBuildOptions = {}) {
        this.storage = storage;
        this.contextBuildOptions = contextBuildOptions;
    }
    getMetadata() {
        return this.storage.getMetadata();
    }
    getStorage() {
        return this.storage;
    }
    getLeafId() {
        return this.storage.getLeafId();
    }
    getEntry(id) {
        return this.storage.getEntry(id);
    }
    getEntries(options) {
        return this.storage.getEntries(options);
    }
    async getBranch(fromId) {
        const leafId = fromId ?? (await this.storage.getLeafId());
        return this.storage.getPathToRootOrCompaction(leafId);
    }
    async buildContextEntries(options = {}) {
        return buildContextEntries(await this.getBranch(), this.mergeContextBuildOptions(options));
    }
    async buildContext(options = {}) {
        return buildSessionContext(await this.getBranch(), this.mergeContextBuildOptions(options));
    }
    mergeContextBuildOptions(options) {
        return {
            entryTransforms: [...(this.contextBuildOptions.entryTransforms ?? []), ...(options.entryTransforms ?? [])],
            entryProjectors: {
                ...(this.contextBuildOptions.entryProjectors ?? {}),
                ...(options.entryProjectors ?? {}),
            },
        };
    }
    getLabel(id) {
        return this.storage.getLabel(id);
    }
    getSessionStats() {
        return this.storage.getSessionStats();
    }
    async getSessionName() {
        return this.storage.getSessionName();
    }
    async appendTypedEntry(entry) {
        await this.storage.appendEntry(entry);
        return entry.id;
    }
    async appendMessage(message) {
        return this.appendTypedEntry({
            type: "message",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            message,
        });
    }
    async appendThinkingLevelChange(thinkingLevel) {
        return this.appendTypedEntry({
            type: "thinking_level_change",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            thinkingLevel,
        });
    }
    async appendModelChange(provider, modelId) {
        return this.appendTypedEntry({
            type: "model_change",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            provider,
            modelId,
        });
    }
    async appendActiveToolsChange(activeToolNames) {
        return this.appendTypedEntry({
            type: "active_tools_change",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            activeToolNames: [...activeToolNames],
        });
    }
    async appendCompaction(summary, firstKeptEntryId, tokensBefore, details, fromHook, usage, retainedTail) {
        return this.appendTypedEntry({
            type: "compaction",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            summary,
            firstKeptEntryId,
            tokensBefore,
            retainedTail,
            details,
            usage,
            fromHook,
        });
    }
    async appendCustomEntry(customType, data) {
        return this.appendTypedEntry({
            type: "custom",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            customType,
            data,
        });
    }
    async appendCustomMessageEntry(customType, content, display, details) {
        return this.appendTypedEntry({
            type: "custom_message",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            customType,
            content,
            display,
            details,
        });
    }
    async appendLabel(targetId, label) {
        if (!(await this.storage.getEntry(targetId))) {
            throw new SessionError("not_found", `Entry ${targetId} not found`);
        }
        return this.appendTypedEntry({
            type: "label",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            targetId,
            label,
        });
    }
    async appendSessionName(name) {
        const sanitizedName = name.replace(/[\r\n]+/g, " ").trim();
        return this.appendTypedEntry({
            type: "session_info",
            id: await this.storage.createEntryId(),
            parentId: await this.storage.getLeafId(),
            timestamp: new Date().toISOString(),
            name: sanitizedName,
        });
    }
    async moveTo(entryId, summary) {
        if (entryId !== null && !(await this.storage.getEntry(entryId))) {
            throw new SessionError("not_found", `Entry ${entryId} not found`);
        }
        await this.storage.setLeafId(entryId);
        if (!summary)
            return undefined;
        return this.appendTypedEntry({
            type: "branch_summary",
            id: await this.storage.createEntryId(),
            parentId: entryId,
            timestamp: new Date().toISOString(),
            fromId: entryId ?? "root",
            summary: summary.summary,
            details: summary.details,
            usage: summary.usage,
            fromHook: summary.fromHook,
        });
    }
}
//# sourceMappingURL=session.js.map