import api from "@/lib/api";
import { isConfigurationSnapshot, type ConfigurationSnapshot } from "./contracts";

export async function getConfigurationSnapshot(): Promise<ConfigurationSnapshot> {
  const response = await api.get<unknown>("/api/operator/configuration");
  if (!isConfigurationSnapshot(response.data)) {
    throw new Error("Invalid Configuration Inspector snapshot");
  }
  return response.data;
}
