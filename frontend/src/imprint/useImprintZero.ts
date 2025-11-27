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

export function useImprintZero() {
  const [status, setStatus] = useState<ImprintStatus | null>(null);
  const [proposal, setProposal] = useState<ProposalState>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemDocs, setSystemDocs] = useState<Array<{ id: number; title: string; scope: string; enabled: boolean; token_estimate: number }>>([]);

  const refreshStatus = useCallback(async () => {
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
  }, []);

  const propose = useCallback(async () => {
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
  }, []);

  const accept = useCallback(
    async (personaOverride?: string) => {
      if (!proposal) return null;
      setLoading(true);
      setError(null);
      try {
        await acceptImprint(proposal.imprint_draft.id, personaOverride);
        setProposal(null);
        await refreshStatus();
      } catch (e: any) {
        setError(e?.message || "Failed to accept imprint");
      } finally {
        setLoading(false);
      }
    },
    [proposal, refreshStatus]
  );

  const reject = useCallback(async () => {
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
  }, [proposal]);

  const refreshSystemPromptSummary = useCallback(async () => {
    try {
      const data = await fetchSystemPromptSummary();
      setStatus((prev) => ({ ...(prev || {}), system_prompt_meta: data }));
    } catch (e) {
      // ignore summary errors; not fatal
    }
  }, []);

  const refreshSystemDocs = useCallback(async () => {
    try {
      const data = await fetchSystemDocs();
      setSystemDocs(data?.docs || []);
    } catch (e) {
      // ignore errors
    }
  }, []);

  const updatePersona = useCallback(
    async (body: string) => {
      setLoading(true);
      setError(null);
      try {
        await updatePersonaApi(body);
        await refreshStatus();
      } catch (e: any) {
        setError(e?.message || "Failed to update persona");
      } finally {
        setLoading(false);
      }
    },
    [refreshStatus]
  );

  const toggleSystemDoc = useCallback(
    async (docId: number, enabled: boolean) => {
      try {
        await toggleSystemDocApi(docId, enabled);
        await refreshSystemDocs();
        await refreshSystemPromptSummary();
      } catch (e: any) {
        setError(e?.message || "Failed to toggle system doc");
      }
    },
    [refreshSystemDocs, refreshSystemPromptSummary]
  );

  useEffect(() => {
    void refreshStatus().then(() => {
      void refreshSystemPromptSummary();
      void refreshSystemDocs();
    });
  }, [refreshStatus, refreshSystemDocs, refreshSystemPromptSummary]);

  const hasLargePrompt = useMemo(() => {
    const est = status?.system_prompt_meta?.estimated_tokens ?? 0;
    return est > 1500;
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
