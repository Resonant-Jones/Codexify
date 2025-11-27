import { useCallback, useMemo, useRef, useState } from "react";
import { GuardianAPI } from "../lib/guardianApi";
import {
  getPreferredProvider,
  setPreferredProvider,
  type ProviderName,
} from "../lib/providerPref";

export type ChatMessage = {
  role: "user" | "assistant" | "system";
  content: string;
};

type SendOpts = {
  stream?: boolean;
  providerOverride?: string | null;
  model?: string | null;
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
};

export function useGuardianChat(initialProvider?: ProviderName) {
  const [provider, _setProvider] = useState<ProviderName>(
    initialProvider ?? getPreferredProvider()
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<() => void>(() => {});

  const setProvider = useCallback((p: ProviderName) => {
    _setProvider(p);
    setPreferredProvider(p);
  }, []);

  const reset = useCallback(() => {
    setMessages([]);
    if (isStreaming && abortRef.current) abortRef.current();
    setIsStreaming(false);
  }, [isStreaming]);

  const send = useCallback(
    async (prompt: string, opts: SendOpts = {}) => {
      const chosenProvider =
        opts.providerOverride !== undefined ? opts.providerOverride : provider;

      // 1) add user message
      setMessages((m) => [...m, { role: "user", content: prompt }]);

      if (opts.stream !== false) {
        // 2) streaming path (default)
        setIsStreaming(true);
        // add placeholder assistant message
        setMessages((m) => [...m, { role: "assistant", content: "" }]);

        const stop = GuardianAPI.chatStream(
          {
            prompt,
            provider: chosenProvider ?? undefined,
            model: opts.model ?? undefined,
            temperature: opts.temperature,
            top_p: opts.top_p,
            max_tokens: opts.max_tokens,
          },
          (tok) => {
            setMessages((m) => {
              // append token to last assistant message
              const out = m.slice();
              for (let i = out.length - 1; i >= 0; i--) {
                if (out[i].role === "assistant") {
                  out[i] = { ...out[i], content: out[i].content + tok };
                  break;
                }
              }
              return out;
            });
          }
        );

        abortRef.current = () => {
          try {
            stop();
          } catch {}
        };

        // Safety: turn off after ~90s if server doesn't send [DONE]
        const turnOff = () => setIsStreaming(false);
        setTimeout(turnOff, 90_000);
      } else {
        // 3) sync path
        const res = await GuardianAPI.chat({
          prompt,
          provider: chosenProvider ?? undefined,
          model: opts.model ?? undefined,
          temperature: opts.temperature,
          top_p: opts.top_p,
          max_tokens: opts.max_tokens,
        });
        setMessages((m) => [...m, { role: "assistant", content: res.text }]);
      }
    },
    [provider]
  );

  const abort = useCallback(() => {
    if (abortRef.current) abortRef.current();
    setIsStreaming(false);
  }, []);

  return useMemo(
    () => ({ messages, isStreaming, send, abort, provider, setProvider, reset }),
    [messages, isStreaming, send, abort, provider, setProvider, reset]
  );
}
