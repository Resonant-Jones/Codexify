import { type AssistantMessage, type ImageContent, type Model, type Models } from "@earendil-works/pi-ai";
import type { AgentMessage, QueueMode, ThinkingLevel } from "../types.ts";
import type { AbortResult, AgentHarnessEvent, AgentHarnessEventResultMap, AgentHarnessOptions, AgentHarnessOwnEvent, AgentHarnessResources, AgentHarnessStreamOptions, AgentHarnessTool, CompactResult, NavigateTreeResult, PromptTemplate, Skill } from "./types.ts";
export declare class AgentHarness<TContext extends object | undefined = undefined, TSkill extends Skill = Skill, TPromptTemplate extends PromptTemplate = PromptTemplate, TTool extends AgentHarnessTool<TContext> = AgentHarnessTool<TContext>> {
    private session;
    readonly models: Models;
    private phase;
    private runAbortController?;
    private runPromise?;
    private pendingSessionWrites;
    private model;
    private thinkingLevel;
    private systemPrompt;
    private toolContext;
    private streamOptions;
    private retry;
    private resources;
    private tools;
    private activeToolNames;
    private steerQueue;
    private steeringQueueMode;
    private followUpQueue;
    private followUpQueueMode;
    private nextTurnQueue;
    private handlers;
    constructor(options: AgentHarnessOptions<TContext, TSkill, TPromptTemplate, TTool>);
    private getHandlers;
    private emitOwn;
    private emitAny;
    private emitHook;
    private retryCallbacks;
    private emitBeforeProviderRequest;
    private emitBeforeProviderPayload;
    private emitQueueUpdate;
    private startRunPromise;
    private resolveToolContext;
    private bindToolContext;
    private createTurnState;
    private createContext;
    private createStreamFn;
    private drainQueuedMessages;
    private createLoopConfig;
    private validateUniqueNames;
    private validateToolNames;
    private flushPendingSessionWrites;
    private handleAgentEvent;
    private emitRunFailure;
    private executeTurn;
    prompt(text: string, options?: {
        images?: ImageContent[];
    }): Promise<AssistantMessage>;
    skill(name: string, additionalInstructions?: string): Promise<AssistantMessage>;
    promptFromTemplate(name: string, args?: string[]): Promise<AssistantMessage>;
    steer(text: string, options?: {
        images?: ImageContent[];
    }): Promise<void>;
    followUp(text: string, options?: {
        images?: ImageContent[];
    }): Promise<void>;
    nextTurn(text: string, options?: {
        images?: ImageContent[];
    }): Promise<void>;
    appendMessage(message: AgentMessage): Promise<void>;
    compact(customInstructions?: string): Promise<CompactResult>;
    navigateTree(targetId: string, options?: {
        summarize?: boolean;
        customInstructions?: string;
        replaceInstructions?: boolean;
        label?: string;
    }): Promise<NavigateTreeResult>;
    getModel(): Model<any>;
    setModel(model: Model<any>): Promise<void>;
    getThinkingLevel(): ThinkingLevel;
    setThinkingLevel(level: ThinkingLevel): Promise<void>;
    getTools(): TTool[];
    setTools(tools: TTool[], activeToolNames?: string[]): Promise<void>;
    getActiveTools(): TTool[];
    setActiveTools(toolNames: string[]): Promise<void>;
    getSteeringMode(): QueueMode;
    setSteeringMode(mode: QueueMode): Promise<void>;
    getFollowUpMode(): QueueMode;
    setFollowUpMode(mode: QueueMode): Promise<void>;
    getResources(): AgentHarnessResources<TSkill, TPromptTemplate>;
    setResources(resources: AgentHarnessResources<TSkill, TPromptTemplate>): Promise<void>;
    getStreamOptions(): AgentHarnessStreamOptions;
    setStreamOptions(streamOptions: AgentHarnessStreamOptions): Promise<void>;
    abort(): Promise<AbortResult>;
    waitForIdle(): Promise<void>;
    subscribe(listener: (event: AgentHarnessEvent<TSkill, TPromptTemplate>, signal?: AbortSignal) => Promise<void> | void): () => void;
    on<TType extends keyof AgentHarnessEventResultMap>(type: TType, handler: (event: Extract<AgentHarnessOwnEvent, {
        type: TType;
    }>) => Promise<AgentHarnessEventResultMap[TType]> | AgentHarnessEventResultMap[TType]): () => void;
}
//# sourceMappingURL=agent-harness.d.ts.map