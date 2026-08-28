export { clearApiKeyCache } from "./provider-composer.js";
/**
 * Synchronous compatibility facade exposed to extensions.
 * Coding-agent internals use ModelRuntime directly.
 */
export class ModelRegistry {
    runtime;
    constructor(runtime) {
        this.runtime = runtime;
    }
    /** Reload models.json asynchronously. Await before making synchronous registry reads. */
    async refresh() {
        await this.runtime.refresh();
    }
    getError() {
        return this.runtime.getError();
    }
    getAll() {
        return [...this.runtime.getModels()];
    }
    getAvailable() {
        return [...this.runtime.getAvailableSnapshot()];
    }
    find(provider, modelId) {
        return this.runtime.getModel(provider, modelId);
    }
    hasConfiguredAuth(model) {
        return this.runtime.hasConfiguredAuth(model.provider);
    }
    async getApiKeyAndHeaders(model) {
        try {
            const resolution = await this.runtime.getAuth(model);
            if (!resolution) {
                const compatibility = this.runtime.getCompatibilityRequestConfig(model);
                if (compatibility.authHeader) {
                    return { ok: false, error: `No API key found for "${model.provider}"` };
                }
                const headers = compatibility.headers
                    ? Object.fromEntries(Object.entries(compatibility.headers).filter((entry) => entry[1] !== null))
                    : undefined;
                return { ok: true, headers };
            }
            const headers = resolution.auth.headers
                ? Object.fromEntries(Object.entries(resolution.auth.headers).filter((entry) => entry[1] !== null))
                : undefined;
            return { ok: true, apiKey: resolution.auth.apiKey, headers, env: resolution.env };
        }
        catch (error) {
            const cause = error instanceof Error ? error.cause : undefined;
            const message = cause instanceof Error ? cause.message : error instanceof Error ? error.message : String(error);
            return {
                ok: false,
                error: message === "authHeader requires a resolved API key"
                    ? `No API key found for "${model.provider}"`
                    : message,
            };
        }
    }
    getProviderAuthStatus(provider) {
        return this.runtime.getProviderAuthStatus(provider);
    }
    getProvider(provider) {
        return this.runtime.getProvider(provider);
    }
    getProviderDisplayName(provider) {
        return this.runtime.getProvider(provider)?.name ?? provider;
    }
    getProviderAuth(provider) {
        return this.runtime.getAuth(provider);
    }
    async getApiKeyForProvider(provider) {
        try {
            return (await this.runtime.getAuth(provider))?.auth.apiKey;
        }
        catch {
            return undefined;
        }
    }
    isUsingOAuth(model) {
        return this.runtime.isUsingOAuth(model.provider);
    }
    registerProvider(providerOrName, config) {
        if (typeof providerOrName === "string") {
            if (!config)
                throw new Error("Provider config is required when registering by name");
            this.runtime.registerProvider(providerOrName, config);
            return;
        }
        this.runtime.registerNativeProvider(providerOrName);
    }
    unregisterProvider(providerName) {
        this.runtime.unregisterProvider(providerName);
    }
    getRegisteredProviderConfig(providerName) {
        return this.runtime.getRegisteredProviderConfig(providerName);
    }
    getRegisteredNativeProvider(providerName) {
        return this.runtime.getRegisteredNativeProvider(providerName);
    }
    getRegisteredProviderIds() {
        return this.runtime.getRegisteredProviderIds();
    }
}
//# sourceMappingURL=model-registry.js.map