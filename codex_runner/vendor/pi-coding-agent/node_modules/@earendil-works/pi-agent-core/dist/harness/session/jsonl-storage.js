import { uuidv7 } from "@earendil-works/pi-ai";
import { SessionError, toError } from "../types.js";
import { getFileSystemResultOrThrow } from "./repo-utils.js";
function updateLabelCache(labelsById, entry) {
    if (entry.type !== "label")
        return;
    const label = entry.label?.trim();
    if (label) {
        labelsById.set(entry.targetId, label);
    }
    else {
        labelsById.delete(entry.targetId);
    }
}
function buildLabelsById(entries) {
    const labelsById = new Map();
    for (const entry of entries) {
        updateLabelCache(labelsById, entry);
    }
    return labelsById;
}
function generateEntryId(byId) {
    for (let i = 0; i < 100; i++) {
        // The uuidv7 prefix is timestamp-derived and nearly constant between calls,
        // so short ids must come from the random tail.
        const id = uuidv7().slice(-8);
        if (!byId.has(id))
            return id;
    }
    return uuidv7();
}
function invalidSession(filePath, message, cause) {
    return new SessionError("invalid_session", `Invalid JSONL session file ${filePath}: ${message}`, cause);
}
function invalidEntry(filePath, lineNumber, message, cause) {
    return new SessionError("invalid_entry", `Invalid JSONL session file ${filePath}: line ${lineNumber} ${message}`, cause);
}
function parseHeaderLine(line, filePath) {
    let parsed;
    try {
        parsed = JSON.parse(line);
    }
    catch (error) {
        throw invalidSession(filePath, "first line is not a valid session header", toError(error));
    }
    if (typeof parsed !== "object" || parsed === null) {
        throw invalidSession(filePath, "first line is not a valid session header");
    }
    const header = parsed;
    if (header.type !== "session")
        throw invalidSession(filePath, "first line is not a valid session header");
    if (header.version !== 3)
        throw invalidSession(filePath, "unsupported session version");
    if (typeof header.id !== "string" || !header.id)
        throw invalidSession(filePath, "session header is missing id");
    if (typeof header.timestamp !== "string" || !header.timestamp) {
        throw invalidSession(filePath, "session header is missing timestamp");
    }
    if (typeof header.cwd !== "string" || !header.cwd)
        throw invalidSession(filePath, "session header is missing cwd");
    if (header.parentSession !== undefined && typeof header.parentSession !== "string") {
        throw invalidSession(filePath, "session header parentSession must be a string");
    }
    if (header.metadata !== undefined &&
        (typeof header.metadata !== "object" || header.metadata === null || Array.isArray(header.metadata))) {
        throw invalidSession(filePath, "session header metadata must be an object");
    }
    return {
        type: "session",
        version: 3,
        id: header.id,
        timestamp: header.timestamp,
        cwd: header.cwd,
        parentSession: header.parentSession,
        metadata: header.metadata,
    };
}
function parseEntryLine(line, filePath, lineNumber) {
    let parsed;
    try {
        parsed = JSON.parse(line);
    }
    catch (error) {
        throw invalidEntry(filePath, lineNumber, "is not valid JSON", toError(error));
    }
    if (typeof parsed !== "object" || parsed === null) {
        throw invalidEntry(filePath, lineNumber, "is not a valid session entry");
    }
    const entry = parsed;
    if (typeof entry.type !== "string")
        throw invalidEntry(filePath, lineNumber, "is missing entry type");
    if (typeof entry.id !== "string" || !entry.id)
        throw invalidEntry(filePath, lineNumber, "is missing entry id");
    if (entry.parentId !== null && typeof entry.parentId !== "string") {
        throw invalidEntry(filePath, lineNumber, "has invalid parentId");
    }
    if (typeof entry.timestamp !== "string" || !entry.timestamp) {
        throw invalidEntry(filePath, lineNumber, "is missing timestamp");
    }
    if (entry.type === "leaf" && entry.targetId !== null && typeof entry.targetId !== "string") {
        throw invalidEntry(filePath, lineNumber, "has invalid targetId");
    }
    return entry;
}
function leafIdAfterEntry(entry) {
    return entry.type === "leaf" ? entry.targetId : entry.id;
}
function headerToSessionMetadata(header, path) {
    return {
        id: header.id,
        createdAt: header.timestamp,
        cwd: header.cwd,
        path,
        parentSessionPath: header.parentSession,
        metadata: header.metadata,
    };
}
export async function loadJsonlSessionMetadata(fs, filePath) {
    const lines = getFileSystemResultOrThrow(await fs.readTextLines(filePath, { maxLines: 1 }), `Failed to read session header ${filePath}`);
    const line = lines[0];
    if (line?.trim())
        return headerToSessionMetadata(parseHeaderLine(line, filePath), filePath);
    throw invalidSession(filePath, "missing session header");
}
async function loadJsonlStorage(fs, filePath) {
    const content = getFileSystemResultOrThrow(await fs.readTextFile(filePath), `Failed to read session ${filePath}`);
    const lines = content.split("\n").filter((line) => line.trim());
    if (lines.length === 0) {
        throw invalidSession(filePath, "missing session header");
    }
    const header = parseHeaderLine(lines[0], filePath);
    const entries = [];
    let leafId = null;
    for (let i = 1; i < lines.length; i++) {
        const entry = parseEntryLine(lines[i], filePath, i + 1);
        entries.push(entry);
        leafId = leafIdAfterEntry(entry);
    }
    return { header, entries, leafId };
}
export class JsonlSessionStorage {
    fs;
    filePath;
    metadata;
    entries;
    byId;
    labelsById;
    currentLeafId;
    constructor(fs, filePath, header, entries, leafId) {
        this.fs = fs;
        this.filePath = filePath;
        this.metadata = headerToSessionMetadata(header, this.filePath);
        this.entries = entries;
        this.byId = new Map(entries.map((entry) => [entry.id, entry]));
        this.labelsById = buildLabelsById(entries);
        this.currentLeafId = leafId;
    }
    static async open(fs, filePath) {
        const loaded = await loadJsonlStorage(fs, filePath);
        return new JsonlSessionStorage(fs, filePath, loaded.header, loaded.entries, loaded.leafId);
    }
    static async create(fs, filePath, options) {
        const header = {
            type: "session",
            version: 3,
            id: options.sessionId,
            timestamp: new Date().toISOString(),
            cwd: options.cwd,
            parentSession: options.parentSessionPath,
            metadata: options.metadata,
        };
        getFileSystemResultOrThrow(await fs.writeFile(filePath, `${JSON.stringify(header)}\n`), `Failed to create session ${filePath}`);
        return new JsonlSessionStorage(fs, filePath, header, [], null);
    }
    async getMetadata() {
        return this.metadata;
    }
    async getLeafId() {
        if (this.currentLeafId !== null && !this.byId.has(this.currentLeafId)) {
            throw new SessionError("invalid_session", `Entry ${this.currentLeafId} not found`);
        }
        return this.currentLeafId;
    }
    async setLeafId(leafId) {
        if (leafId !== null && !this.byId.has(leafId)) {
            throw new SessionError("not_found", `Entry ${leafId} not found`);
        }
        const entry = {
            type: "leaf",
            id: generateEntryId(this.byId),
            parentId: this.currentLeafId,
            timestamp: new Date().toISOString(),
            targetId: leafId,
        };
        getFileSystemResultOrThrow(await this.fs.appendFile(this.filePath, `${JSON.stringify(entry)}\n`), `Failed to append session leaf ${entry.id}`);
        this.entries.push(entry);
        this.byId.set(entry.id, entry);
        this.currentLeafId = leafId;
    }
    async createEntryId() {
        return generateEntryId(this.byId);
    }
    async appendEntry(entry) {
        getFileSystemResultOrThrow(await this.fs.appendFile(this.filePath, `${JSON.stringify(entry)}\n`), `Failed to append session entry ${entry.id}`);
        this.entries.push(entry);
        this.byId.set(entry.id, entry);
        updateLabelCache(this.labelsById, entry);
        this.currentLeafId = leafIdAfterEntry(entry);
    }
    async getEntry(id) {
        return this.byId.get(id);
    }
    async findEntries(type) {
        return this.entries.filter((entry) => entry.type === type);
    }
    async getLabel(id) {
        return this.labelsById.get(id);
    }
    async getSessionName() {
        const entries = await this.findEntries("session_info");
        return entries[entries.length - 1]?.name?.trim() || undefined;
    }
    async getSessionStats() {
        let messageCount = 0;
        let cachedTokens = 0;
        let uncachedTokens = 0;
        let totalTokens = 0;
        let costTotal = 0;
        for (const entry of this.entries) {
            if (entry.type === "message") {
                messageCount += 1;
            }
            const usage = entry.type === "message"
                ? entry.message.role === "assistant"
                    ? entry.message.usage
                    : undefined
                : entry.type === "compaction" || entry.type === "branch_summary"
                    ? entry.usage
                    : undefined;
            if (!usage ||
                typeof usage.input !== "number" ||
                typeof usage.output !== "number" ||
                typeof usage.cacheRead !== "number" ||
                typeof usage.cacheWrite !== "number" ||
                typeof usage.cost?.total !== "number") {
                continue;
            }
            cachedTokens += usage.cacheRead;
            uncachedTokens += usage.input + usage.cacheWrite;
            totalTokens += usage.input + usage.output + usage.cacheRead + usage.cacheWrite;
            costTotal += usage.cost.total;
        }
        return {
            messageCount,
            cachedTokens,
            uncachedTokens,
            totalTokens,
            costTotal,
        };
    }
    async getPathToRootOrCompaction(leafId) {
        if (leafId === null)
            return [];
        const path = [];
        let stopAtEntryId = null;
        let current = this.byId.get(leafId);
        if (!current)
            throw new SessionError("not_found", `Entry ${leafId} not found`);
        while (current) {
            path.unshift(current);
            if (stopAtEntryId !== null && current.id === stopAtEntryId)
                break;
            if (current.type === "compaction") {
                if (current.retainedTail)
                    break;
                stopAtEntryId = current.firstKeptEntryId ?? null;
            }
            if (!current.parentId)
                break;
            const parent = this.byId.get(current.parentId);
            if (!parent)
                throw new SessionError("invalid_session", `Entry ${current.parentId} not found`);
            current = parent;
        }
        return path;
    }
    async getEntries(options) {
        const start = options?.afterEntrySeq ?? 0;
        const end = options?.limit === undefined ? undefined : start + options.limit;
        return this.entries.slice(start, end);
    }
}
//# sourceMappingURL=jsonl-storage.js.map