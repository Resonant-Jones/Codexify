import { lazyStream } from "./api/lazy.js";
import { defaultProviderAuthContext as defaultAuthContext } from "./auth/context.js";
import { InMemoryCredentialStore } from "./auth/credential-store.js";
import { ModelsError, resolveProviderAuth } from "./auth/resolve.js";
import { InMemoryModelsStore } from "./models-store.js";
export { ModelsError } from "./auth/resolve.js";
function mergeHeaders(base, override) {
    if (!base && !override)
        return undefined;
    const merged = { ...base };
    for (const [name, value] of Object.entries(override ?? {})) {
        const lowerName = name.toLowerCase();
        for (const existingName of Object.keys(merged)) {
            if (existingName.toLowerCase() === lowerName)
                delete merged[existingName];
        }
        merged[name] = value;
    }
    return merged;
}
class ModelsImpl {
    providers = new Map();
    credentials;
    modelsStore;
    authContext;
    constructor(options) {
        this.credentials = options?.credentials ?? new InMemoryCredentialStore();
        this.modelsStore = options?.modelsStore ?? new InMemoryModelsStore();
        this.authContext = options?.authContext ?? defaultAuthContext();
    }
    setProvider(provider) {
        this.providers.set(provider.id, provider);
    }
    deleteProvider(id) {
        this.providers.delete(id);
    }
    clearProviders() {
        this.providers.clear();
    }
    getProviders() {
        return Array.from(this.providers.values());
    }
    getProvider(id) {
        return this.providers.get(id);
    }
    getModels(provider) {
        if (provider !== undefined) {
            const entry = this.providers.get(provider);
            if (!entry)
                return [];
            try {
                return entry.getModels();
            }
            catch {
                return [];
            }
        }
        const models = [];
        for (const entry of this.providers.values()) {
            try {
                models.push(...entry.getModels());
            }
            catch {
                // Best-effort: ill-behaved providers yield no models.
            }
        }
        return models;
    }
    getModel(provider, id) {
        return this.getModels(provider).find((model) => model.id === id);
    }
    async refresh(options = {}) {
        const allowNetwork = options.allowNetwork ?? true;
        const errors = new Map();
        const refreshable = Array.from(this.providers.values()).filter((provider) => provider.refreshModels !== undefined);
        await Promise.all(refreshable.map(async (provider) => {
            if (options.signal?.aborted)
                return;
            const store = {
                read: () => this.modelsStore.read(provider.id),
                write: (entry) => this.modelsStore.write(provider.id, entry),
                delete: () => this.modelsStore.delete(provider.id),
            };
            let stored;
            try {
                stored = await this.readCredential(provider.id);
                const credential = await this.resolveRefreshCredential(provider, stored, allowNetwork, options.signal);
                if (!credential)
                    return;
                await provider.refreshModels({
                    credential,
                    store,
                    allowNetwork,
                    force: options.force,
                    signal: options.signal,
                });
            }
            catch (error) {
                if (!options.signal?.aborted) {
                    errors.set(provider.id, error instanceof Error
                        ? error
                        : new ModelsError("model_source", `Model refresh failed for ${provider.id}`, { cause: error }));
                }
                try {
                    await provider.refreshModels({
                        credential: stored,
                        store,
                        allowNetwork: false,
                        signal: options.signal,
                    });
                }
                catch {
                    // Preserve the original auth/network error; cache restoration is best-effort here.
                }
            }
        }));
        return { aborted: options.signal?.aborted ?? false, errors };
    }
    async resolveRefreshCredential(provider, stored, allowNetwork, signal) {
        if (stored?.type === "oauth") {
            const oauth = provider.auth.oauth;
            if (!oauth)
                return undefined;
            if (!allowNetwork || Date.now() < stored.expires)
                return stored;
            if (signal?.aborted)
                return undefined;
            const post = await this.credentials.modify(provider.id, async (current) => {
                if (current?.type !== "oauth" || Date.now() < current.expires)
                    return undefined;
                return oauth.refresh(current, signal);
            });
            return post?.type === "oauth" ? post : undefined;
        }
        const apiKey = provider.auth.apiKey;
        if (!apiKey)
            return undefined;
        const credential = stored?.type === "api_key" ? stored : undefined;
        const result = await apiKey.resolve({ ctx: this.authContext, credential });
        if (!result)
            return undefined;
        return { type: "api_key", key: result.auth.apiKey, env: result.env };
    }
    async readCredential(providerId) {
        try {
            return await this.credentials.read(providerId);
        }
        catch (error) {
            throw new ModelsError("auth", `Credential store read failed for ${providerId}`, { cause: error });
        }
    }
    async checkProviderAuth(provider, credential) {
        if (credential?.type === "oauth") {
            return provider.auth.oauth ? { source: "OAuth", type: "oauth" } : undefined;
        }
        const apiKey = provider.auth.apiKey;
        if (!apiKey)
            return undefined;
        if (apiKey.check) {
            try {
                return await apiKey.check({
                    ctx: this.authContext,
                    credential: credential?.type === "api_key" ? credential : undefined,
                });
            }
            catch (error) {
                throw new ModelsError("auth", `API key auth check failed for provider ${provider.id}`, { cause: error });
            }
        }
        const resolution = await resolveProviderAuth(provider, this.credentials, this.authContext);
        return resolution ? { source: resolution.source, type: "api_key" } : undefined;
    }
    async checkAuth(providerId) {
        const provider = this.providers.get(providerId);
        if (!provider)
            return undefined;
        return this.checkProviderAuth(provider, await this.readCredential(providerId));
    }
    async getAvailable(providerId) {
        const providers = providerId
            ? [this.providers.get(providerId)].filter((entry) => entry !== undefined)
            : this.getProviders();
        const checks = await Promise.all(providers.map(async (provider) => {
            const credential = await this.readCredential(provider.id);
            return { provider, credential, auth: await this.checkProviderAuth(provider, credential) };
        }));
        return checks.flatMap(({ provider, credential, auth }) => {
            if (!auth)
                return [];
            const models = provider.getModels();
            return provider.filterModels?.(models, credential) ?? models;
        });
    }
    async getAuth(providerOrModel, overrides) {
        const providerId = typeof providerOrModel === "string" ? providerOrModel : providerOrModel.provider;
        const provider = this.providers.get(providerId);
        if (!provider)
            return undefined;
        const result = await resolveProviderAuth(provider, this.credentials, this.authContext, overrides);
        if (!result || typeof providerOrModel === "string" || !providerOrModel.headers)
            return result;
        return {
            ...result,
            auth: {
                ...result.auth,
                headers: mergeHeaders(result.auth.headers, providerOrModel.headers),
            },
        };
    }
    async login(providerId, type, interaction) {
        const provider = this.providers.get(providerId);
        if (!provider)
            throw new ModelsError("provider", `Unknown provider: ${providerId}`);
        const method = type === "oauth" ? provider.auth.oauth : provider.auth.apiKey;
        if (!method?.login) {
            throw new ModelsError("auth", `${provider.name} does not support ${type} login`);
        }
        const credential = await method.login(interaction);
        try {
            await this.credentials.modify(providerId, async () => credential);
        }
        catch (error) {
            throw new ModelsError("auth", `Credential store modify failed for ${providerId}`, { cause: error });
        }
        return credential;
    }
    async logout(providerId) {
        try {
            await this.credentials.delete(providerId);
        }
        catch (error) {
            throw new ModelsError("auth", `Credential store delete failed for ${providerId}`, { cause: error });
        }
    }
    requireProvider(model) {
        const provider = this.providers.get(model.provider);
        if (!provider) {
            throw new ModelsError("provider", `Unknown provider: ${model.provider}`);
        }
        return provider;
    }
    async applyAuth(model, options) {
        this.requireProvider(model);
        const resolution = await this.getAuth(model, {
            apiKey: options?.apiKey,
            env: options?.env,
        });
        if (!resolution) {
            throw new ModelsError("auth", `Provider is not configured: ${model.provider}`);
        }
        const auth = resolution.auth;
        // Explicit request options win per-field; the Models-only transform runs last.
        const apiKey = options?.apiKey ?? auth.apiKey;
        let headers = mergeHeaders(auth.headers, options?.headers);
        if (options?.transformHeaders)
            headers = await options.transformHeaders(headers ?? {});
        const env = resolution.env || options?.env ? { ...(resolution.env ?? {}), ...(options?.env ?? {}) } : undefined;
        const requestModel = auth.baseUrl ? { ...model, baseUrl: auth.baseUrl } : model;
        const { transformHeaders: _transformHeaders, ...providerOptions } = options ?? {};
        const requestOptions = { ...providerOptions, apiKey, headers, env };
        return { requestModel, requestOptions };
    }
    stream(model, context, options) {
        return lazyStream(model, async () => {
            const provider = this.requireProvider(model);
            const { requestModel, requestOptions } = await this.applyAuth(model, options);
            return provider.stream(requestModel, context, requestOptions);
        });
    }
    async complete(model, context, options) {
        return this.stream(model, context, options).result();
    }
    streamSimple(model, context, options) {
        return lazyStream(model, async () => {
            const provider = this.requireProvider(model);
            const { requestModel, requestOptions } = await this.applyAuth(model, options);
            return provider.streamSimple(requestModel, context, requestOptions);
        });
    }
    async completeSimple(model, context, options) {
        return this.streamSimple(model, context, options).result();
    }
}
export function createModels(options) {
    return new ModelsImpl(options);
}
/**
 * Builds a provider from parts. Built-in provider factories and models.json
 * custom providers both go through this. A single `api` streams all models;
 * an `api` map dispatches on `model.api`, and a model whose api has no entry
 * produces a stream error.
 */
export function createProvider(input) {
    const baselineModels = input.models;
    let dynamicModels = [];
    let inflightRefresh;
    const fetchModels = input.fetchModels;
    const currentModels = () => {
        const merged = [...baselineModels];
        for (const model of dynamicModels) {
            const index = merged.findIndex((entry) => entry.id === model.id);
            if (index >= 0)
                merged[index] = model;
            else
                merged.push(model);
        }
        return merged;
    };
    const single = typeof input.api.stream === "function" ? input.api : undefined;
    const byApi = single ? undefined : input.api;
    const apiFor = (model) => single ?? byApi?.[model.api];
    const dispatch = (model, run) => {
        const streams = apiFor(model);
        if (!streams) {
            return lazyStream(model, async () => {
                throw new ModelsError("stream", `Provider ${input.id} has no API implementation for "${model.api}"`);
            });
        }
        return run(streams);
    };
    return {
        id: input.id,
        name: input.name ?? input.id,
        baseUrl: input.baseUrl,
        headers: input.headers,
        auth: input.auth,
        getModels: currentModels,
        refreshModels: fetchModels
            ? (context) => {
                inflightRefresh ??= (async () => {
                    try {
                        const stored = await context.store.read();
                        if (stored) {
                            dynamicModels = stored.models
                                .filter((model) => model.provider === input.id)
                                .map((model) => model);
                        }
                        if (!context.allowNetwork || context.signal?.aborted)
                            return;
                        const refreshed = await fetchModels(context);
                        if (context.signal?.aborted)
                            return;
                        dynamicModels = refreshed;
                        await context.store.write({ models: refreshed, checkedAt: Date.now() });
                    }
                    finally {
                        inflightRefresh = undefined;
                    }
                })();
                return inflightRefresh;
            }
            : undefined,
        filterModels: input.filterModels,
        stream: (model, context, options) => dispatch(model, (streams) => streams.stream(model, context, options)),
        streamSimple: (model, context, options) => dispatch(model, (streams) => streams.streamSimple(model, context, options)),
    };
}
/**
 * Runtime-checked narrowing for dynamically looked-up models:
 *
 * ```ts
 * const model = models.getModel("anthropic", "claude-opus-4-7");
 * if (model && hasApi(model, "anthropic-messages")) {
 *   // model: Model<"anthropic-messages">, stream options fully typed
 * }
 * ```
 */
export function hasApi(model, api) {
    return model.api === api;
}
export function calculateCost(model, usage) {
    const inputTokens = usage.input + usage.cacheRead + usage.cacheWrite;
    let rates = model.cost;
    let matchedThreshold = -1;
    for (const tier of model.cost.tiers ?? []) {
        if (inputTokens > tier.inputTokensAbove && tier.inputTokensAbove > matchedThreshold) {
            rates = tier;
            matchedThreshold = tier.inputTokensAbove;
        }
    }
    // Anthropic charges 2x base input for 1h cache writes.
    const longWrite = usage.cacheWrite1h ?? 0;
    const shortWrite = usage.cacheWrite - longWrite;
    usage.cost.input = (rates.input / 1000000) * usage.input;
    usage.cost.output = (rates.output / 1000000) * usage.output;
    usage.cost.cacheRead = (rates.cacheRead / 1000000) * usage.cacheRead;
    usage.cost.cacheWrite = (rates.cacheWrite * shortWrite + rates.input * 2 * longWrite) / 1000000;
    usage.cost.total = usage.cost.input + usage.cost.output + usage.cost.cacheRead + usage.cost.cacheWrite;
    return usage.cost;
}
const EXTENDED_THINKING_LEVELS = ["off", "minimal", "low", "medium", "high", "xhigh", "max"];
export function getSupportedThinkingLevels(model) {
    if (!model.reasoning)
        return ["off"];
    return EXTENDED_THINKING_LEVELS.filter((level) => {
        const mapped = model.thinkingLevelMap?.[level];
        if (mapped === null)
            return false;
        if (level === "xhigh" || level === "max")
            return mapped !== undefined;
        return true;
    });
}
export function clampThinkingLevel(model, level) {
    const availableLevels = getSupportedThinkingLevels(model);
    if (availableLevels.includes(level))
        return level;
    const requestedIndex = EXTENDED_THINKING_LEVELS.indexOf(level);
    if (requestedIndex === -1)
        return availableLevels[0] ?? "off";
    for (let i = requestedIndex; i < EXTENDED_THINKING_LEVELS.length; i++) {
        const candidate = EXTENDED_THINKING_LEVELS[i];
        if (availableLevels.includes(candidate))
            return candidate;
    }
    for (let i = requestedIndex - 1; i >= 0; i--) {
        const candidate = EXTENDED_THINKING_LEVELS[i];
        if (availableLevels.includes(candidate))
            return candidate;
    }
    return availableLevels[0] ?? "off";
}
/**
 * Check if two models are equal by comparing both their id and provider.
 * Returns false if either model is null or undefined.
 */
export function modelsAreEqual(a, b) {
    if (!a || !b)
        return false;
    return a.id === b.id && a.provider === b.provider;
}
//# sourceMappingURL=models.js.map