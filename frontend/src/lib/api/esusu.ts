import { apiClient } from "@/lib/api-client";
import type {
  EsusuCycleCreatePayload,
  EsusuCycleResponse,
  EsusuListItem,
  EsusuJoinResponse,
  EsusuContributionResult,
  EsusuContributePayload,
} from "@/lib/types";

export function listEsusuCycles() {
  return apiClient.get<EsusuListItem[]>('/esusu/cycles');
}

export function getEsusuCycle(cycleId: string) {
  return apiClient.get<EsusuCycleResponse>(`/esusu/cycles/${cycleId}`);
}

export function createEsusuCycle(payload: EsusuCycleCreatePayload) {
  return apiClient.post<EsusuCycleResponse>('/esusu/cycles', payload);
}

export function joinEsusuCycle(cycleId: string) {
  return apiClient.post<EsusuJoinResponse>(`/esusu/cycles/${cycleId}/join`);
}

export function contributeToEsusuCycle(cycleId: string, payload: EsusuContributePayload) {
  return apiClient.post<EsusuContributionResult>(`/esusu/cycles/${cycleId}/contribute`, payload);
}