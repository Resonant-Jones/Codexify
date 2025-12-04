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

export default api;
