// ============================================================
// Auth
// ============================================================
export interface VerifyOTPResponse {
  access_token: string;
  role: "trader" | "head_of_traders" | "wholesaler";
  display_name: string;
  market_name: string | null;
}

// ============================================================
// Trader
// ============================================================
export interface TraderResponse {
  id: string;
  name: string;
  phone: string;
  stall_number: string;
  market_name: string;
  virtual_account_number: string | null;
  bank_name: string | null;
  bank_account_name: string | null;
  spendable_balance: number;
  total_contributed: number;
  created_at: string | null;
}

export interface TraderListItem {
  id: string;
  name: string;
  phone: string;
  stall_number: string;
  market_name: string;
  virtual_account_number: string | null;
  bank_name: string | null;
  spendable_balance: number;
  total_contributed: number;
}

export type LedgerEntryType =
  | "spendable_credit"
  | "pool_lock"
  | "pool_release_payout"
  | "pool_refund";

export interface LedgerEntryResponse {
  id: string;
  entry_type: LedgerEntryType;
  amount: number;
  balance_after: number;
  note: string | null;
  pool_id: string | null;
  created_at: string;
}

export interface TraderLedgerResponse {
  trader_id: string;
  trader_name: string;
  current_spendable: number;
  entries: LedgerEntryResponse[];
}

// ============================================================
// Pool
// ============================================================
export type PoolStatus = "open" | "fulfilled" | "refunded";

export interface PoolResponse {
  id: string;
  title: string;
  market_name: string | null;
  target_amount: number;
  current_locked_amount: number;
  progress_pct: number;
  supplier_name: string;
  supplier_account_number: string;
  supplier_bank_code: string;
  status: PoolStatus;
  deadline: string;
  created_at: string | null;
  fulfilled_at: string | null;
  wholesaler_confirmed_at: string | null;
}

export interface ContributorResponse {
  trader_id: string;
  amount_locked: number;
  status: "locked" | "released" | "refunded";
  created_at: string;
}

export interface PoolDetailResponse extends PoolResponse {
  contributors: ContributorResponse[];
}

export interface PoolJoinResponse {
  message: string;
  trader_id: string;
  pool_id: string;
  pool_title: string;
  target: number;
  progress: number;
}

// ============================================================
// Reports
// ============================================================
export interface ReconciliationBreakdown {
  spendable_total: number;
  locked_total: number;
}

export interface ReconciliationResponse {
  nomba_balance: number | null;
  our_ledger_total: number;
  discrepancy: number | null;
  is_reconciled: boolean | null;
  currency: string | null;
  checked_at: string | null;
  breakdown: ReconciliationBreakdown;
  error: string | null;
}

export interface StatsResponse {
  total_traders: number;
  active_pools: number;
  fulfilled_pools: number;
  total_locked: number;
  total_fulfilled_amount: number;
}

// ============================================================
// API error shape (FastAPI default)
// ============================================================
export interface ApiErrorBody {
  detail: string | { msg: string }[];
}