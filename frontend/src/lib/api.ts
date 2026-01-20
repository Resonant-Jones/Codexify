import axios from "axios";

/**
 * Central Axios instance for the frontend.
 * Reads `VITE_API_BASE_URL` at build time; defaults to "/api".
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  withCredentials: true,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const baseURL = String(
    config.baseURL ?? api.defaults.baseURL ?? ""
  ).replace(/\/+$/, "");
  if (
    baseURL.endsWith("/api")
    && typeof config.url === "string"
    && config.url.startsWith("/api/")
  ) {
    config.url = config.url.replace(/^\/api/, "");
  }
  return config;
});

export default api;
