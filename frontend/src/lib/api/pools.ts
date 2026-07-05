import { apiClient } from "@/lib/api-client";
import { getAdminToken } from "@/context/AdminAuthContext";
import type { PoolResponse, PoolDetailResponse, PoolJoinResponse } from "@/lib/types";

export function listPools() {
  return apiClient.get<PoolResponse[]>("/pools", {
    tokenOverride: getAdminToken(),
  });
}

export function getPool(poolId: string) {
  return apiClient.get<PoolDetailResponse>(`/pools/${poolId}`, {
    tokenOverride: getAdminToken(),
  });
}

export interface CreatePoolPayload {
  title: string;
  market_name: string;
  target_amount: number;
  supplier_name: string;
  supplier_account_number: string;
  supplier_bank_code: string;
  deadline: string; // ISO string
}

export function createPool(payload: CreatePoolPayload) {
  return apiClient.post<PoolResponse>("/pools", payload, {
    tokenOverride: getAdminToken(),
  });
}

export function joinPool(poolId: string, traderId: string) {
  return apiClient.post<PoolJoinResponse>(`/pools/${poolId}/join`, {
    trader_id: traderId,
  });
}