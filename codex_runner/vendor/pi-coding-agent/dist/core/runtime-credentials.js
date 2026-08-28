/** Async credential store overlay for non-persistent runtime API keys. */
export class RuntimeCredentials {
    store;
    overrides = new Map();
    constructor(store) {
        this.store = store;
    }
    setRuntimeApiKey(providerId, apiKey) {
        this.overrides.set(providerId, apiKey);
    }
    removeRuntimeApiKey(providerId) {
        this.overrides.delete(providerId);
    }
    hasRuntimeApiKey(providerId) {
        return this.overrides.has(providerId);
    }
    async read(providerId) {
        const override = this.overrides.get(providerId);
        return override ? { type: "api_key", key: override } : this.store.read(providerId);
    }
    async list() {
        const entries = new Map((await this.store.list()).map((entry) => [entry.providerId, entry]));
        for (const providerId of this.overrides.keys()) {
            entries.set(providerId, { providerId, type: "api_key" });
        }
        return [...entries.values()];
    }
    modify(providerId, fn) {
        return this.store.modify(providerId, fn);
    }
    async delete(providerId) {
        this.overrides.delete(providerId);
        await this.store.delete(providerId);
    }
}
//# sourceMappingURL=runtime-credentials.js.map