/**
 * CredentialStore implementation backed by auth.json.
 * Provider auth orchestration belongs to ModelRuntime and pi-ai Models.
 */
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { dirname, join } from "path";
import lockfile from "proper-lockfile";
import { getAgentDir } from "../config.js";
import { normalizePath } from "../utils/paths.js";
import { resolveConfigValue } from "./resolve-config-value.js";
const AUTH_FILE_WRITE_OPTIONS = { encoding: "utf-8", mode: 0o600 };
export class FileAuthStorageBackend {
    authPath;
    constructor(authPath = join(getAgentDir(), "auth.json")) {
        this.authPath = normalizePath(authPath);
    }
    ensureParentDir() {
        const dir = dirname(this.authPath);
        if (!existsSync(dir)) {
            mkdirSync(dir, { recursive: true, mode: 0o700 });
        }
    }
    ensureFileExists() {
        if (!existsSync(this.authPath)) {
            writeFileSync(this.authPath, "{}", AUTH_FILE_WRITE_OPTIONS);
            chmodSync(this.authPath, 0o600);
        }
    }
    acquireLockSyncWithRetry(path) {
        const maxAttempts = 10;
        const delayMs = 20;
        let lastError;
        for (let attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                return lockfile.lockSync(path, { realpath: false });
            }
            catch (error) {
                const code = typeof error === "object" && error !== null && "code" in error
                    ? String(error.code)
                    : undefined;
                if (code !== "ELOCKED" || attempt === maxAttempts) {
                    throw error;
                }
                lastError = error;
                const start = Date.now();
                while (Date.now() - start < delayMs) {
                    // Sleep synchronously to avoid changing callers to async.
                }
            }
        }
        throw lastError ?? new Error("Failed to acquire auth storage lock");
    }
    withLock(fn) {
        this.ensureParentDir();
        this.ensureFileExists();
        let release;
        try {
            release = this.acquireLockSyncWithRetry(this.authPath);
            const current = existsSync(this.authPath) ? readFileSync(this.authPath, "utf-8") : undefined;
            const { result, next } = fn(current);
            if (next !== undefined) {
                writeFileSync(this.authPath, next, AUTH_FILE_WRITE_OPTIONS);
                chmodSync(this.authPath, 0o600);
            }
            return result;
        }
        finally {
            if (release) {
                release();
            }
        }
    }
    async withLockAsync(fn) {
        this.ensureParentDir();
        this.ensureFileExists();
        let release;
        let lockCompromised = false;
        let lockCompromisedError;
        const throwIfCompromised = () => {
            if (lockCompromised) {
                throw lockCompromisedError ?? new Error("Auth storage lock was compromised");
            }
        };
        try {
            release = await lockfile.lock(this.authPath, {
                retries: {
                    retries: 10,
                    factor: 2,
                    minTimeout: 100,
                    maxTimeout: 10000,
                    randomize: true,
                },
                stale: 30000,
                onCompromised: (err) => {
                    lockCompromised = true;
                    lockCompromisedError = err;
                },
            });
            throwIfCompromised();
            const current = existsSync(this.authPath) ? readFileSync(this.authPath, "utf-8") : undefined;
            const { result, next } = await fn(current);
            throwIfCompromised();
            if (next !== undefined) {
                writeFileSync(this.authPath, next, AUTH_FILE_WRITE_OPTIONS);
                chmodSync(this.authPath, 0o600);
            }
            throwIfCompromised();
            return result;
        }
        finally {
            if (release) {
                try {
                    await release();
                }
                catch {
                    // Ignore unlock errors when lock is compromised.
                }
            }
        }
    }
}
export class InMemoryAuthStorageBackend {
    value;
    withLock(fn) {
        const { result, next } = fn(this.value);
        if (next !== undefined) {
            this.value = next;
        }
        return result;
    }
    async withLockAsync(fn) {
        const { result, next } = await fn(this.value);
        if (next !== undefined) {
            this.value = next;
        }
        return result;
    }
}
/**
 * Credential storage backed by a JSON file.
 */
export class AuthStorage {
    data = {};
    storage;
    constructor(storage) {
        this.storage = storage;
        this.reload();
    }
    static create(authPath) {
        return new AuthStorage(new FileAuthStorageBackend(authPath ?? join(getAgentDir(), "auth.json")));
    }
    static fromStorage(storage) {
        return new AuthStorage(storage);
    }
    static inMemory(data = {}) {
        const storage = new InMemoryAuthStorageBackend();
        storage.withLock(() => ({ result: undefined, next: JSON.stringify(data, null, 2) }));
        return AuthStorage.fromStorage(storage);
    }
    parseStorageData(content) {
        if (!content) {
            return {};
        }
        return JSON.parse(content);
    }
    /**
     * Reload credentials from storage.
     */
    reload() {
        let content;
        try {
            this.storage.withLock((current) => {
                content = current;
                return { result: undefined };
            });
            this.data = this.parseStorageData(content);
        }
        catch {
            // Preserve the last valid in-memory snapshot.
        }
    }
    async read(provider) {
        const credential = this.data[provider];
        if (credential?.type !== "api_key")
            return credential;
        if (credential.key === undefined)
            return credential;
        return { ...credential, key: resolveConfigValue(credential.key, credential.env) };
    }
    async modify(provider, fn) {
        return this.storage.withLockAsync(async (content) => {
            const currentData = this.parseStorageData(content);
            const next = await fn(currentData[provider]);
            if (next === undefined) {
                this.data = currentData;
                return { result: currentData[provider] };
            }
            const merged = { ...currentData, [provider]: next };
            this.data = merged;
            return { result: next, next: JSON.stringify(merged, null, 2) };
        });
    }
    async delete(provider) {
        await this.storage.withLockAsync(async (content) => {
            const currentData = this.parseStorageData(content);
            delete currentData[provider];
            this.data = currentData;
            return { result: undefined, next: JSON.stringify(currentData, null, 2) };
        });
    }
    /** List credential metadata without resolving configured key values. */
    async list() {
        return Object.entries(this.data).map(([providerId, credential]) => ({ providerId, type: credential.type }));
    }
}
/**
 * One-off synchronous read of a stored credential from an auth.json file,
 * without instantiating a store or resolving configured key values.
 */
export function readStoredCredential(providerId, authPath = join(getAgentDir(), "auth.json")) {
    try {
        const data = JSON.parse(readFileSync(normalizePath(authPath), "utf-8"));
        return data[providerId];
    }
    catch {
        return undefined;
    }
}
//# sourceMappingURL=auth-storage.js.map