import axios from "axios";

const baseURL = (import.meta as any)?.env?.VITE_GUARDIAN_API_BASE || "";
const apiKey = (import.meta as any)?.env?.VITE_GUARDIAN_API_KEY || "";

export const api = axios.create({
  baseURL,
  headers: apiKey ? { "X-API-Key": apiKey } : undefined,
  withCredentials: false,
});

// Dev-only logging for failed responses
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if ((import.meta as any)?.env?.DEV) {
      // eslint-disable-next-line no-console
      console.warn("[api] request failed", {
        url: err?.config?.url,
        status: err?.response?.status,
        data: err?.response?.data,
      });
    }
    return Promise.reject(err);
  }
);

export default api;

