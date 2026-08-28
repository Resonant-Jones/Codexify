import { dirname, join } from "node:path";
import { createModels, lazyStream, ModelsError, } from "@earendil-works/pi-ai";
import * as builtinProviderCatalog from "@earendil-works/pi-ai/providers/all";
import { getAgentDir } from "../config.js";
import { AuthStorage as DefaultAuthStorage } from "./auth-storage.js";
import { ModelConfig } from "./model-config.js";
import { FileModelsStore, InMemoryCodingAgentModelsStore } from "./models-store.js";
import { composeModelProvider, configuredRequestAuthStatus, resolveCompatibilityRequestConfig, resolveConfiguredModelHeaders, validateExtensionProvider, } from "./provider-composer.js";
import { withRemoteCatalog } from "./remote-catalog-provider.js";
import { RuntimeCredentials } from "./runtime-credentials.js";
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
/** Configured pi-ai Models collection used by coding-agent and SDK consumers. */
export class ModelRuntime {
    models;
    credentials;
    defaultBuiltins;
    builtins = new Map();
    nativeExtensionProviders = new Map();
    extensionProviders = new Map();
    compositionErrors = new Map();
    modelsPath;
    modelNetworkEnabled;
    config;
    snapshot = {
        all: [],
        available: [],
        configuredProviders: new Set(),
        storedProviders: new Set(),
        auth: new Map(),
    };
    availabilityRefresh;
    availabilityError;
    constructor(credentials, config, modelsPath, modelsStore, providers, modelNetworkEnabled) {
        this.credentials = credentials;
        this.config = config;
        this.modelsPath = modelsPath;
        this.modelNetworkEnabled = modelNetworkEnabled;
        this.defaultBuiltins = new Map(providers.map((provider) => [provider.id, provider]));
        for (const [providerId, provider] of this.defaultBuiltins)
            this.builtins.set(providerId, provider);
        this.models = createModels({ credentials, modelsStore });
        this.rebuildProviders();
    }
    static async create(options = {}) {
        const credentials = new RuntimeCredentials(options.credentials ?? DefaultAuthStorage.create(options.authPath));
        const modelsPath = options.modelsPath === null ? undefined : (options.modelsPath ?? join(getAgentDir(), "models.json"));
        const config = await ModelConfig.load(modelsPath);
        const modelsStore = options.modelsStore ??
            (modelsPath
                ? new FileModelsStore(options.modelsStorePath ?? join(dirname(modelsPath), "models-store.json"))
                : new InMemoryCodingAgentModelsStore());
        const builtinModelDataGeneratedAt = builtinProviderCatalog.getBuiltinModelDataGeneratedAt();
        const providers = builtinProviderCatalog
            .builtinProviders()
            .map((provider) => provider.id === "radius"
            ? provider
            : withRemoteCatalog(provider, options.catalogBaseUrl, builtinModelDataGeneratedAt));
        const runtime = new ModelRuntime(credentials, config, modelsPath, modelsStore, providers, process.env.PI_OFFLINE === undefined);
        runtime.configureRadiusProviders();
        runtime.rebuildProviders();
        const refreshFromNetwork = runtime.modelNetworkEnabled && options.allowModelNetwork === true;
        const controller = refreshFromNetwork ? new AbortController() : undefined;
        const timeout = controller
            ? setTimeout(() => controller.abort(), options.modelRefreshTimeoutMs ?? 15_000)
            : undefined;
        try {
            await runtime.refresh({ allowNetwork: refreshFromNetwork, signal: controller?.signal });
        }
        finally {
            if (timeout)
                clearTimeout(timeout);
        }
        return runtime;
    }
    configureRadiusProviders() {
        this.builtins.clear();
        for (const [providerId, provider] of this.defaultBuiltins)
            this.builtins.set(providerId, provider);
        for (const providerId of this.config.getProviderIds()) {
            const config = this.config.getProvider(providerId);
            if (config?.oauth !== "radius" || !config.baseUrl)
                continue;
            this.builtins.set(providerId, builtinProviderCatalog.radiusProvider({
                id: providerId,
                name: config.name ?? providerId,
                gateway: config.baseUrl.replace(/\/v1\/?$/u, ""),
            }));
        }
    }
    providerIds() {
        return new Set([
            ...this.builtins.keys(),
            ...this.nativeExtensionProviders.keys(),
            ...this.config.getProviderIds(),
            ...this.extensionProviders.keys(),
        ]);
    }
    recomposeProvider(providerId) {
        const base = this.nativeExtensionProviders.get(providerId) ?? this.builtins.get(providerId);
        const extension = this.extensionProviders.get(providerId);
        if (!base && !this.config.getProvider(providerId) && !extension) {
            this.models.deleteProvider(providerId);
            this.compositionErrors.delete(providerId);
            return;
        }
        if (base && !this.config.getProvider(providerId) && !extension) {
            // No overlays: use the builtin untouched so its auth/login/stream behavior is exact.
            this.models.setProvider(base);
            this.compositionErrors.delete(providerId);
            return;
        }
        try {
            this.models.setProvider(composeModelProvider(providerId, base, this.config, extension));
            this.compositionErrors.delete(providerId);
        }
        catch (error) {
            this.compositionErrors.set(providerId, error instanceof Error ? error.message : String(error));
            if (base)
                this.models.setProvider(base);
            else
                this.models.deleteProvider(providerId);
        }
    }
    rebuildProviders() {
        this.models.clearProviders();
        this.compositionErrors.clear();
        for (const providerId of this.providerIds())
            this.recomposeProvider(providerId);
        this.updateModelSnapshot();
    }
    updateModelSnapshot() {
        const all = [...this.models.getModels()];
        this.snapshot = {
            ...this.snapshot,
            all,
            available: all.filter((model) => this.snapshot.configuredProviders.has(model.provider)),
        };
    }
    async runAvailabilityRefresh() {
        const providers = this.models.getProviders();
        const [available, checks, credentials] = await Promise.all([
            this.models.getAvailable(),
            Promise.all(providers.map(async (provider) => [
                provider.id,
                await this.models.checkAuth(provider.id),
            ])),
            this.credentials.list(),
        ]);
        const auth = new Map(checks);
        const configuredProviders = new Set(checks
            .filter((entry) => entry[1] !== undefined)
            .map(([providerId]) => providerId));
        this.snapshot = {
            all: [...this.models.getModels()],
            available: [...available],
            configuredProviders,
            storedProviders: new Set(credentials.map((entry) => entry.providerId)),
            auth,
        };
        this.availabilityError = undefined;
    }
    queueAvailabilityRefresh(after) {
        const refresh = (after ?? Promise.resolve()).catch(() => { }).then(() => this.runAvailabilityRefresh());
        const recorded = refresh.catch((error) => {
            this.availabilityError = error instanceof Error ? error.message : String(error);
            throw error;
        });
        const tracked = recorded.finally(() => {
            if (this.availabilityRefresh === tracked)
                this.availabilityRefresh = undefined;
        });
        this.availabilityRefresh = tracked;
        return tracked;
    }
    /** Coalesce concurrent readers onto the pending refresh. */
    refreshAvailability() {
        return this.availabilityRefresh ?? this.queueAvailabilityRefresh(undefined);
    }
    /** Mutations must not observe an in-flight refresh started before them. */
    forceRefreshAvailability() {
        return this.queueAvailabilityRefresh(this.availabilityRefresh);
    }
    getProviders() {
        return this.models.getProviders();
    }
    getProvider(providerId) {
        return this.models.getProvider(providerId);
    }
    getModels(providerId) {
        return this.models.getModels(providerId);
    }
    getModel(providerId, modelId) {
        return this.models.getModel(providerId, modelId);
    }
    async checkAuth(providerId) {
        return this.models.checkAuth(providerId);
    }
    async getAvailable(providerId) {
        if (providerId) {
            if (this.availabilityRefresh) {
                await this.availabilityRefresh;
                return this.snapshot.available.filter((model) => model.provider === providerId);
            }
            try {
                return await this.models.getAvailable(providerId);
            }
            catch (error) {
                this.availabilityError = error instanceof Error ? error.message : String(error);
                throw error;
            }
        }
        await this.refreshAvailability();
        return this.snapshot.available;
    }
    getAvailableSnapshot() {
        return this.snapshot.available;
    }
    getError() {
        const errors = [];
        const configError = this.config.getError();
        if (configError)
            errors.push(configError);
        for (const [providerId, error] of this.compositionErrors) {
            errors.push(`Provider "${providerId}": ${error}`);
        }
        if (this.availabilityError)
            errors.push(`Availability refresh: ${this.availabilityError}`);
        return errors.length > 0 ? errors.join("\n\n") : undefined;
    }
    getRegisteredProviderConfig(providerId) {
        return this.extensionProviders.get(providerId);
    }
    getRegisteredProviderIds() {
        return [...new Set([...this.extensionProviders.keys(), ...this.nativeExtensionProviders.keys()])];
    }
    getRegisteredNativeProvider(providerId) {
        return this.nativeExtensionProviders.get(providerId);
    }
    /** @internal Compatibility fallback for ModelRegistry when provider auth is unconfigured. */
    getCompatibilityRequestConfig(model) {
        return resolveCompatibilityRequestConfig(model, this.config.getProvider(model.provider), this.extensionProviders.get(model.provider));
    }
    isUsingOAuth(providerId) {
        return this.snapshot.auth.get(providerId)?.type === "oauth";
    }
    hasConfiguredAuth(providerId) {
        return this.snapshot.configuredProviders.has(providerId);
    }
    async getAuth(providerOrModel, overrides = {}) {
        if (typeof providerOrModel === "string")
            return this.models.getAuth(providerOrModel, overrides);
        const resolution = await this.models.getAuth(providerOrModel, overrides);
        if (!resolution)
            return undefined;
        const configuredHeaders = resolveConfiguredModelHeaders(providerOrModel, this.config.getProvider(providerOrModel.provider), this.extensionProviders.get(providerOrModel.provider), { ...(resolution.env ?? {}), ...(overrides.env ?? {}) });
        return {
            ...resolution,
            auth: {
                ...resolution.auth,
                headers: mergeHeaders(resolution.auth.headers, configuredHeaders),
            },
        };
    }
    async setRuntimeApiKey(providerId, apiKey, refreshOptions = {}) {
        this.credentials.setRuntimeApiKey(providerId, apiKey);
        const auth = new Map(this.snapshot.auth).set(providerId, { type: "api_key", source: "runtime API key" });
        const configuredProviders = new Set(this.snapshot.configuredProviders).add(providerId);
        const storedProviders = new Set(this.snapshot.storedProviders).add(providerId);
        this.snapshot = {
            ...this.snapshot,
            auth,
            configuredProviders,
            storedProviders,
            available: this.snapshot.all.filter((model) => configuredProviders.has(model.provider)),
        };
        await this.refresh(refreshOptions);
    }
    async removeRuntimeApiKey(providerId) {
        this.credentials.removeRuntimeApiKey(providerId);
        await this.refresh({ allowNetwork: this.modelNetworkEnabled });
    }
    listCredentials() {
        return this.credentials.list();
    }
    getProviderAuthStatus(providerId) {
        if (this.credentials.hasRuntimeApiKey(providerId))
            return { configured: true, source: "runtime" };
        if (this.snapshot.storedProviders.has(providerId))
            return { configured: true, source: "stored" };
        const configured = configuredRequestAuthStatus(this.config.getProvider(providerId), this.extensionProviders.get(providerId));
        if (configured)
            return configured;
        const check = this.snapshot.auth.get(providerId);
        return check ? { configured: true, source: "environment", label: check.source } : { configured: false };
    }
    async prepareRequest(model, options) {
        const provider = this.models.getProvider(model.provider);
        if (!provider)
            throw new ModelsError("provider", `Unknown provider: ${model.provider}`);
        const resolution = await this.getAuth(model, { apiKey: options?.apiKey, env: options?.env });
        if (!resolution)
            throw new ModelsError("auth", `Provider is not configured: ${model.provider}`);
        const { transformHeaders, ...providerOptions } = options ?? {};
        let headers = mergeHeaders(resolution.auth.headers, providerOptions.headers);
        if (transformHeaders)
            headers = await transformHeaders(headers ?? {});
        const env = resolution.env || providerOptions.env
            ? { ...(resolution.env ?? {}), ...(providerOptions.env ?? {}) }
            : undefined;
        return {
            provider,
            model: resolution.auth.baseUrl ? { ...model, baseUrl: resolution.auth.baseUrl } : model,
            options: {
                ...providerOptions,
                apiKey: providerOptions.apiKey ?? resolution.auth.apiKey,
                headers,
                env,
            },
        };
    }
    stream(model, context, options) {
        return lazyStream(model, async () => {
            const prepared = await this.prepareRequest(model, options);
            return prepared.provider.stream(prepared.model, context, prepared.options);
        });
    }
    complete(model, context, options) {
        return this.stream(model, context, options).result();
    }
    streamSimple(model, context, options) {
        return lazyStream(model, async () => {
            const prepared = await this.prepareRequest(model, options);
            return prepared.provider.streamSimple(prepared.model, context, prepared.options);
        });
    }
    completeSimple(model, context, options) {
        return this.streamSimple(model, context, options).result();
    }
    async login(providerId, type, interaction) {
        const credential = await this.models.login(providerId, type, interaction);
        await this.refresh({ allowNetwork: this.modelNetworkEnabled });
        return credential;
    }
    async logout(providerId) {
        await this.models.logout(providerId);
        // Reset credential-dependent compatibility projections before the unconfigured provider is skipped by refresh.
        this.recomposeProvider(providerId);
        await this.refresh({ allowNetwork: this.modelNetworkEnabled });
    }
    async refresh(options = {}) {
        this.config = await ModelConfig.load(this.modelsPath);
        this.configureRadiusProviders();
        this.rebuildProviders();
        const refreshOptions = {
            ...options,
            allowNetwork: options.allowNetwork ?? this.modelNetworkEnabled,
        };
        // Published pi-ai builds before ModelsStore returned void and accepted a provider ID.
        // The fallback keeps source-mode CLI tests working without rebuilding workspace dependencies.
        const result = (await this.models.refresh(refreshOptions)) ?? {
            aborted: refreshOptions.signal?.aborted ?? false,
            errors: new Map(),
        };
        this.updateModelSnapshot();
        try {
            await this.forceRefreshAvailability();
        }
        catch {
            // Availability errors are recorded by forceRefreshAvailability; refreshed models remain usable.
        }
        return result;
    }
    registerNativeProvider(provider) {
        if (!provider.id.trim())
            throw new Error("Provider id must not be empty.");
        this.extensionProviders.delete(provider.id);
        this.nativeExtensionProviders.set(provider.id, provider);
        this.recomposeProvider(provider.id);
        this.updateModelSnapshot();
        void this.refresh({ allowNetwork: false });
    }
    registerProvider(providerId, config) {
        // Validate the incoming registration on its own, like the legacy registry:
        // a broken re-registration must throw without touching the stored config.
        validateExtensionProvider(providerId, this.builtins.get(providerId), this.config.getProvider(providerId), config);
        this.nativeExtensionProviders.delete(providerId);
        // Re-registration merges defined values over the previous registration and
        // preserves undefined ones, matching the legacy ModelRegistry contract.
        const previous = this.extensionProviders.get(providerId);
        const effective = { ...previous };
        for (const [key, value] of Object.entries(config)) {
            if (value !== undefined)
                effective[key] = value;
        }
        this.extensionProviders.set(providerId, effective);
        this.recomposeProvider(providerId);
        this.updateModelSnapshot();
        if (this.snapshot.storedProviders.has(providerId) ||
            configuredRequestAuthStatus(this.config.getProvider(providerId), effective)?.configured) {
            const configuredProviders = new Set(this.snapshot.configuredProviders).add(providerId);
            const auth = new Map(this.snapshot.auth);
            // Provisional entry until the async refresh lands; never clobber a real check result.
            if (!auth.get(providerId)) {
                auth.set(providerId, {
                    type: effective.oauth && !effective.apiKey ? "oauth" : "api_key",
                    source: "configured provider",
                });
            }
            this.snapshot = {
                ...this.snapshot,
                auth,
                configuredProviders,
                available: this.snapshot.all.filter((model) => configuredProviders.has(model.provider)),
            };
        }
        void this.refresh({ allowNetwork: false });
    }
    unregisterProvider(providerId) {
        this.extensionProviders.delete(providerId);
        this.nativeExtensionProviders.delete(providerId);
        this.recomposeProvider(providerId);
        this.updateModelSnapshot();
        void this.refresh({ allowNetwork: false });
    }
}
//# sourceMappingURL=model-runtime.js.map