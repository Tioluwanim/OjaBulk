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

export interface PoolContributeFromSpendableResponse {
  pool_id: string;
  trader_id: string;
  amount_locked: number;
  new_spendable_balance: number;
  pool_current_locked_amount: number;
  pool_fulfilled: boolean;
  message: string;
}

export interface BankListItem {
  name: string;
  code: string;
}

export interface AccountLookupResponse {
  account_number: string;
  account_name: string;
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

export interface RecentPaymentItem {
  id: string;
  trader_id: string;
  trader_name: string;
  trader_phone: string;
  amount_received: number;
  spendable_portion: number;
  pool_portion: number;
  pool_id: string | null;
  pool_title: string | null;
  nomba_transaction_ref: string;
  received_at: string | null;
}

export interface RecentPaymentsResponse {
  items: RecentPaymentItem[];
}

export interface TraderPaymentResponse {
  id: string;
  amount_received: number;
  nomba_transaction_ref: string;
  pool_id: string | null;
  received_at: string;
  already_used_for_esusu: boolean;
}

export interface TraderPaymentsListResponse {
  items: TraderPaymentResponse[];
}

// ============================================================
// Esusu
// ============================================================
export type EsusuStatus = "open" | "active" | "completed" | "cancelled";
export type EsusuRoundStatus = "open" | "paid";

export interface EsusuCycleCreatePayload {
  title: string;
  market_name: string;
  contribution_amount: number;
  total_members: number;
  frequency_days: number;
  description?: string | null;
}

export interface EsusuMemberResponse {
  id: string;
  trader_id: string;
  trader_name: string;
  trader_phone: string;
  payout_position: number;
  joined_at: string | null;
  last_contributed_round: number | null;
  last_received_round: number | null;
}

export interface EsusuContributionResponse {
  id: string;
  round_id: string;
  trader_id: string;
  trader_name: string;
  amount: number;
  contributed_at: string | null;
}

export interface EsusuRoundResponse {
  id: string;
  round_number: number;
  beneficiary_member_id: string;
  beneficiary_trader_name: string;
  target_amount: number;
  collected_amount: number;
  status: EsusuRoundStatus;
  created_at: string | null;
  paid_at: string | null;
  contribution_count: number;
  progress_pct: number;
}

export interface EsusuCycleResponse {
  id: string;
  title: string;
  description: string | null;
  market_name: string | null;
  contribution_amount: number;
  total_members: number;
  frequency_days: number;
  current_round_number: number;
  status: EsusuStatus;
  total_collected: number;
  created_at: string | null;
  activated_at: string | null;
  completed_at: string | null;
  members: EsusuMemberResponse[];
  rounds: EsusuRoundResponse[];
  contributions: EsusuContributionResponse[];
  progress_pct: number;
  next_beneficiary_trader_name: string | null;
}

export interface EsusuListItem {
  id: string;
  title: string;
  market_name: string | null;
  contribution_amount: number;
  total_members: number;
  current_round_number: number;
  status: EsusuStatus;
  progress_pct: number;
  created_at: string | null;
}

export interface EsusuJoinResponse {
  id: string;
  cycle_id: string;
  trader_id: string;
  trader_name: string;
  payout_position: number;
  status: EsusuStatus;
  message: string;
}

export interface EsusuContributionResult {
  cycle_id: string;
  round_number: number;
  amount: number;
  round_paid: boolean;
  cycle_completed: boolean;
  next_round_number: number | null;
  beneficiary_trader_name: string;
}

export interface EsusuContributePayload {
  nomba_transaction_ref: string;
}

// ============================================================
// API error shape (FastAPI default)
// ============================================================
export interface ApiErrorBody {
  detail: string | { msg: string }[];
}
