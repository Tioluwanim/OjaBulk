import { useEffect, useState } from "react";
import { listBanks } from "@/lib/api/pools";
import type { BankListItem } from "@/lib/types";

// Module-level cache: the bank list is static reference data (not
// account-specific), so fetching it once per browser session instead
// of once per page mount avoids an unnecessary network round-trip
// every time a pool detail page loads.
let cachedBanks: BankListItem[] | null = null;
let inFlight: Promise<BankListItem[]> | null = null;

async function getBanks(): Promise<BankListItem[]> {
  if (cachedBanks) return cachedBanks;
  if (inFlight) return inFlight;

  inFlight = listBanks()
    .then((banks) => {
      cachedBanks = banks;
      return banks;
    })
    .finally(() => {
      inFlight = null;
    });

  return inFlight;
}

/**
 * Resolves supplier_bank_code (a raw numeric code, e.g. "090405")
 * into the human-readable bank name (e.g. "Moniepoint MFB") for
 * display. Falls back to the raw code if the list hasn't loaded yet
 * or the code isn't found (e.g. a bank removed from Nomba's list
 * since the pool was created) -- never shows a blank.
 */
export function useBankName(bankCode: string | null | undefined): {
  bankName: string;
  isLoading: boolean;
} {
  const [banks, setBanks] = useState<BankListItem[] | null>(cachedBanks);
  const [isLoading, setIsLoading] = useState(!cachedBanks);

  useEffect(() => {
    if (cachedBanks) return;
    let cancelled = false;
    getBanks()
      .then((result) => {
        if (!cancelled) setBanks(result);
      })
      .catch(() => {
        // Silent -- caller falls back to the raw code below.
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!bankCode) {
    return { bankName: "", isLoading };
  }

  const match = banks?.find((b) => b.code === bankCode);
  return {
    bankName: match?.name ?? bankCode,
    isLoading,
  };
}
