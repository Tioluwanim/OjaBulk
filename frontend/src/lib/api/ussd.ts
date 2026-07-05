import { postFormRaw } from "@/lib/api-client";

export interface UssdRawResponse {
  mode: "CON" | "END";
  message: string;
}

export async function sendUssdRequest(params: {
  sessionId: string;
  serviceCode: string;
  phoneNumber: string;
  text: string;
}): Promise<UssdRawResponse> {
  const raw = await postFormRaw("/ussd/session", {
    sessionId: params.sessionId,
    serviceCode: params.serviceCode,
    phoneNumber: params.phoneNumber,
    text: params.text,
  });

  const mode = raw.startsWith("END") ? "END" : "CON";
  const message = raw.replace(/^(CON|END)\s*/, "");

  return { mode, message };
}