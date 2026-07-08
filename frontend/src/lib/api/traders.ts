import { apiClient } from "@/lib/api-client";
import type {
  TraderResponse,
  TraderLedgerResponse,
  PoolResponse,
} from "@/lib/types";
import type { TraderListItem, TraderPayoutDetailsUpdatePayload } from "@/lib/types";
import { getAdminToken } from "@/context/AdminAuthContext";
export interface RegisterTraderPayload {
  name: string;
  phone: string;
  stall_number: string;
  market_name: string;
}

export function registerTrader(payload: RegisterTraderPayload) {
  return apiClient.post<TraderResponse>("/traders", payload, {
    auth: false,
  });
}

export function getMyProfile() {
  return apiClient.get<TraderResponse>("/traders/me");
}

export function getMyLedger() {
  return apiClient.get<TraderLedgerResponse>("/traders/me/ledger");
}

export function getMyPools() {
  return apiClient.get<PoolResponse[]>("/traders/me/pools");
}

export function updateMyPayoutDetails(payload: TraderPayoutDetailsUpdatePayload) {
  return apiClient.put<TraderResponse>("/traders/me/payout-details", payload);
}


export function listTraders() {
  return apiClient.get<TraderListItem[]>("/traders", {
    tokenOverride: getAdminToken(),
  });
}
export function getTraderById(traderId: string) {
  return apiClient.get<TraderResponse>(`/traders/${traderId}`, {
    tokenOverride: getAdminToken(),
  });
}

export function getTraderLedgerById(traderId: string) {
  return apiClient.get<TraderLedgerResponse>(`/traders/${traderId}/ledger`, {
    tokenOverride: getAdminToken(),
  });
}