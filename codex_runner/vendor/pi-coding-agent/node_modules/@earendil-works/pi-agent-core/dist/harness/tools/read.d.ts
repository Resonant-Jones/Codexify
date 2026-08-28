import { type Static, Type } from "typebox";
import type { AgentHarnessTool } from "../types.ts";
import { type TruncationResult } from "../utils/truncate.ts";
import type { ExecutionToolContext } from "./tool-context.ts";
declare const readSchema: Type.TObject<{
    path: Type.TString;
    offset: Type.TOptional<Type.TNumber>;
    limit: Type.TOptional<Type.TNumber>;
}>;
export type ReadToolInput = Static<typeof readSchema>;
export interface ReadToolDetails {
    truncation?: TruncationResult;
}
export type ReadImageProcessorResult = {
    ok: true;
    data: string;
    mimeType: string;
    hints: string[];
} | {
    ok: false;
    message: string;
};
export type ReadImageProcessor = (bytes: Uint8Array, mimeType: string, options: {
    autoResizeImages: boolean;
}) => Promise<ReadImageProcessorResult>;
export interface ReadToolOptions {
    /** Whether an injected image processor should resize images. Default: true. */
    autoResizeImages?: boolean;
    /** Optional image conversion/resizing implementation. */
    imageProcessor?: ReadImageProcessor;
}
export declare function createReadTool<TContext extends ExecutionToolContext = ExecutionToolContext>(options?: ReadToolOptions): AgentHarnessTool<TContext, typeof readSchema, ReadToolDetails | undefined>;
export {};
//# sourceMappingURL=read.d.ts.map