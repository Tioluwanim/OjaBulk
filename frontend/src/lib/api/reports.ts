import { apiClient } from "@/lib/api-client";
import { getAdminToken } from "@/context/AdminAuthContext";
import type { StatsResponse, ReconciliationResponse } from "@/lib/types";

export function getStats() {
  return apiClient.get<StatsResponse>("/reports/stats", {
    tokenOverride: getAdminToken(),
  });
}

export function getReconciliation() {
  return apiClient.get<ReconciliationResponse>("/reports/reconciliation", {
    tokenOverride: getAdminToken(),
  });
}