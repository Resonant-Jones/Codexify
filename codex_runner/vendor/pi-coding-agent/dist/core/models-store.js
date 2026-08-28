import { join } from "node:path";
import { getAgentDir } from "../config.js";
import { FileAuthStorageBackend } from "./auth-storage.js";
export class InMemoryCodingAgentModelsStore {
    entries = new Map();
    async read(providerId) {
        return this.entries.get(providerId);
    }
    async write(providerId, entry) {
        this.entries.set(providerId, entry);
    }
    async delete(providerId) {
        this.entries.delete(providerId);
    }
}
/** Locked JSON-backed storage for dynamically refreshed provider catalogs. */
export class FileModelsStore {
    storage;
    constructor(path = join(getAgentDir(), "models-store.json")) {
        this.storage = new FileAuthStorageBackend(path);
    }
    parse(content) {
        return content ? JSON.parse(content) : {};
    }
    async read(providerId) {
        return this.storage.withLock((content) => ({
            result: structuredClone(this.parse(content)[providerId]),
        }));
    }
    async write(providerId, entry) {
        await this.storage.withLockAsync(async (content) => {
            const current = this.parse(content);
            current[providerId] = structuredClone(entry);
            return { result: undefined, next: JSON.stringify(current, null, 2) };
        });
    }
    async delete(providerId) {
        await this.storage.withLockAsync(async (content) => {
            const current = this.parse(content);
            delete current[providerId];
            return { result: undefined, next: JSON.stringify(current, null, 2) };
        });
    }
}
//# sourceMappingURL=models-store.js.map