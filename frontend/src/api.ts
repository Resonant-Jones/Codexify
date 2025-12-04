/**
 * @deprecated Shim—use '@/lib/api' going forward.
 *
 * This module re-exports the canonical API client for backwards compatibility.
 * New code should import directly from '@/lib/api'.
 */
export { api as default, ApiError } from "@/lib/api";
export type { ApiResponse } from "@/lib/api";
