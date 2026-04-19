import { useState, useEffect } from "react";
import { fetchProviderState } from "@/lib/api";

export function useProviderState() {
  const [data, setData] = useState<unknown>(undefined);
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetchProviderState();
        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  console.log("[provider-state:query]", { status: isLoading ? "loading" : data ? "success" : error ? "error" : "idle", data, error });

  return { data, error, isLoading };
}
