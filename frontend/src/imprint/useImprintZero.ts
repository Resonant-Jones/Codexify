import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchImprintStatus,
  requestImprintProposal,
  acceptImprint,
  rejectImprint,
  fetchSystemPromptSummary,
  ImprintStatus,
  ImprintProposal,
  updatePersonaApi,
  fetchSystemDocs,
  toggleSystemDocApi,
} from "./api";

type ProposalState = ImprintProposal | null;

type UseImprintZeroOptions = {
  enabled?: boolean;
};

export function useImprintZero(options: UseImprintZeroOptions = {}) {
  const enabled = options.enabled ?? true;
  const [status, setStatus] = useState<ImprintStatus | null>(null);
  const [proposal, setProposal] = useState<ProposalState>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemDocs, setSystemDocs] = useState<Array<{ id: number; title: string; scope: string; enabled: boolean; token_estimate: number }>>([]);

  const refreshStatus = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchImprintStatus();
      setStatus(data);
    } catch (e: any) {
      setError(e?.message || "Failed to load imprint status");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  const propose = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await requestImprintProposal();
      setProposal(data);
    } catch (e: any) {
      setError(e?.message || "Failed to create proposal");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  const refreshSystemPromptSummary = useCallback(async () => {
    if (!enabled) return;
    try {
      const data = await fetchSystemPromptSummary();
      setStatus((prev) => ({ ...(prev || {}), system_prompt_meta: data }));
    } catch (e) {
      // ignore summary errors; not fatal
    }
  }, [enabled]);

  const accept = useCallback(
    async (personaOverride?: string) => {
      if (!enabled) return null;
      if (!proposal) return null;
      setLoading(true);
      setError(null);
      try {
        await acceptImprint(proposal.imprint_draft.id, personaOverride);
        setProposal(null);
        await refreshStatus();
        await refreshSystemPromptSummary();
      } catch (e: any) {
        setError(e?.message || "Failed to accept imprint");
      } finally {
        setLoading(false);
      }
    },
    [enabled, proposal, refreshStatus, refreshSystemPromptSummary]
  );

  const reject = useCallback(async () => {
    if (!enabled) return;
    if (!proposal) return;
    setLoading(true);
    setError(null);
    try {
      await rejectImprint(proposal.imprint_draft.id);
      setProposal(null);
    } catch (e: any) {
      setError(e?.message || "Failed to reject imprint");
    } finally {
      setLoading(false);
    }
  }, [enabled, proposal]);

  const refreshSystemDocs = useCallback(async () => {
    if (!enabled) return;
    try {
      const data = await fetchSystemDocs();
      setSystemDocs(data?.docs || []);
    } catch (e) {
      // ignore errors
    }
  }, [enabled]);

  const updatePersona = useCallback(
    async (body: string) => {
      if (!enabled) return;
      setLoading(true);
      setError(null);
      try {
        await updatePersonaApi(body);
        await refreshStatus();
        await refreshSystemPromptSummary();
      } catch (e: any) {
        setError(e?.message || "Failed to update persona");
      } finally {
        setLoading(false);
      }
    },
    [enabled, refreshStatus, refreshSystemPromptSummary]
  );

  const toggleSystemDoc = useCallback(
    async (docId: number, nextEnabled: boolean) => {
      if (!enabled) return;
      try {
        await toggleSystemDocApi(docId, nextEnabled);
        await refreshSystemDocs();
        await refreshSystemPromptSummary();
      } catch (e: any) {
        setError(e?.message || "Failed to toggle system doc");
      }
    },
    [enabled, refreshSystemDocs, refreshSystemPromptSummary]
  );

  useEffect(() => {
    if (!enabled) {
      setStatus(null);
      setProposal(null);
      setLoading(false);
      setError(null);
      setSystemDocs([]);
      return;
    }
    void refreshStatus().then(() => {
      void refreshSystemPromptSummary();
      void refreshSystemDocs();
    });
  }, [enabled, refreshStatus, refreshSystemDocs, refreshSystemPromptSummary]);

  const hasLargePrompt = useMemo(() => {
    const meta = status?.system_prompt_meta;
    const est =
      meta?.estimated_tokens_total ?? meta?.estimated_tokens ?? 0;
    const warn = meta?.threshold?.warn_tokens ?? 6000;
    return est >= warn;
  }, [status?.system_prompt_meta]);

  return {
    status,
    proposal,
    loading,
    error,
    refreshStatus,
    propose,
    accept,
    reject,
    hasLargePrompt,
    systemDocs,
    updatePersona,
    toggleSystemDoc,
  };
}

export default useImprintZero;
