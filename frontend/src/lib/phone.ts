/**
 * Mirrors the normalization logic in schemas/trader.py's clean_phone
 * validator, so the UI can show a friendly inline error before ever
 * hitting the API — not a replacement for backend validation.
 */
export function normalizeNigerianPhone(raw: string): string | null {
  let v = raw.trim().replace(/\s|-/g, "");

  if (v.startsWith("+234")) {
    v = "0" + v.slice(4);
  } else if (v.startsWith("234") && v.length === 13) {
    v = "0" + v.slice(3);
  }

  if (!/^\d+$/.test(v)) return null;
  if (!v.startsWith("0") || v.length !== 11) return null;

  return v;
}

export function formatPhoneForDisplay(phone: string): string {
  if (phone.length !== 11) return phone;
  return `${phone.slice(0, 4)} ${phone.slice(4, 7)} ${phone.slice(7)}`;
}