import { Tools } from "@/dcw-services/gc";

export function useTriggerAction() {
  const trigger = async (type: string, args: Record<string, any>) => {
    const execution = await Tools.execute({ type, args });
    if (execution.state === "completed") {
      return { state: execution.state, result: execution.result };
    }
    if (
      execution.state === "failed" ||
      execution.state === "blocked" ||
      execution.state === "denied"
    ) {
      throw execution.result ?? new Error("Trigger action failed");
    }

    const { jobId } = execution;
    return new Promise<{ state: string; result?: any }>((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const { state, result } = await Tools.job(jobId);
          if (state === 'completed' || state === 'failed') {
            clearInterval(poll);
            if (state === 'failed') reject(result);
            else resolve({ state, result });
          }
          if (state === "blocked" || state === "denied") {
            clearInterval(poll);
            reject(result);
          }
        } catch (e) {
          clearInterval(poll);
          reject(e);
        }
      }, 750);
    });
  };
  return { trigger };
}
