import OpenAI from "openai";
import type { ChatCompletionMessageParam } from "openai/resources/chat/completions.js";
import type { Context, Model, OpenAICompletionsCompat, SimpleStreamOptions, StreamFunction, StreamOptions } from "../types.ts";
export interface OpenAICompletionsOptions extends StreamOptions {
    toolChoice?: OpenAI.Chat.Completions.ChatCompletionToolChoiceOption;
    reasoningEffort?: "minimal" | "low" | "medium" | "high" | "xhigh" | "max";
}
export interface ConvertCompletionsMessagesOptions {
    grammarToolInputProperties?: ReadonlyMap<string, string>;
}
type ResolvedOpenAICompletionsCompat = Omit<Required<OpenAICompletionsCompat>, "cacheControlFormat" | "deferredToolsMode"> & {
    cacheControlFormat?: OpenAICompletionsCompat["cacheControlFormat"];
    deferredToolsMode?: OpenAICompletionsCompat["deferredToolsMode"];
};
export declare const stream: StreamFunction<"openai-completions", OpenAICompletionsOptions>;
export declare const streamSimple: StreamFunction<"openai-completions", SimpleStreamOptions>;
export declare function convertMessages(model: Model<"openai-completions">, context: Context, compat: ResolvedOpenAICompletionsCompat, options?: ConvertCompletionsMessagesOptions): ChatCompletionMessageParam[];
export {};
//# sourceMappingURL=openai-completions.d.ts.map