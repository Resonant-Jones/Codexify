import { Tools } from "@/dcw-services/gc";

export function useTriggerAction() {
  const trigger = async (type: string, args: Record<string, any>) => {
    const { jobId } = await Tools.execute({ type, args });
    return new Promise<{ state: string; result?: any }>((resolve, reject) => {
      const poll = setInterval(async () => {
        try {
          const { state, result } = await Tools.job(jobId);
          if (state === 'completed' || state === 'failed') {
            clearInterval(poll);
            if (state === 'failed') reject(result);
            else resolve({ state, result });
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
