import type { ExecutionEnv } from "../types.ts";
/** Serialize file mutations targeting the same environment and canonical path. */
export declare function withFileMutationQueue<T>(env: ExecutionEnv, path: string, fn: () => Promise<T>): Promise<T>;
//# sourceMappingURL=file-mutation-queue.d.ts.map