import { apiClient } from "@/lib/api-client";
import type { VerifyOTPResponse } from "@/lib/types";

export function requestOtp(phone: string) {
  return apiClient.post<{ message: string }>(
    "/auth/request-otp",
    { phone },
    { auth: false }
  );
}

export function verifyOtp(phone: string, code: string) {
  return apiClient.post<VerifyOTPResponse>(
    "/auth/verify-otp",
    { phone, code },
    { auth: false }
  );
}