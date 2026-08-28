export class InMemoryModelsStore {
    entries = new Map();
    async read(providerId) {
        const entry = this.entries.get(providerId);
        return entry ? structuredClone(entry) : undefined;
    }
    async write(providerId, entry) {
        this.entries.set(providerId, structuredClone(entry));
    }
    async delete(providerId) {
        this.entries.delete(providerId);
    }
}
//# sourceMappingURL=models-store.js.map