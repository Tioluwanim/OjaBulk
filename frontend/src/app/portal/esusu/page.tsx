"use client";

import { useEffect, useMemo, useState } from "react";
import { RequireAuth } from "@/components/portal/RequireAuth";
import { PortalNav } from "@/components/portal/PortalNav";
import { Spinner } from "@/components/ui/Spinner";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/context/AuthContext";
import { formatNaira } from "@/lib/format";
import { ApiError } from "@/lib/api-client";
import {
  listEsusuCycles,
  getEsusuCycle,
  createEsusuCycle,
  joinEsusuCycle,
  contributeToEsusuCycle,
} from "@/lib/api/esusu";
import type {
  EsusuCycleCreatePayload,
  EsusuCycleResponse,
  EsusuListItem,
  EsusuContributePayload,
} from "@/lib/types";
import { ArrowRight, RefreshCcw, Plus, Users, CircleDollarSign } from "lucide-react";

interface FormState {
  title: string;
  contribution_amount: string;
  total_members: string;
  frequency_days: string;
  description: string;
}

interface ContributeState {
  nomba_transaction_ref: string;
}

const initialForm: FormState = {
  title: "",
  contribution_amount: "",
  total_members: "",
  frequency_days: "7",
  description: "",
};

const initialContributeState: ContributeState = {
  nomba_transaction_ref: "",
};

function statusLabel(status: EsusuCycleResponse["status"]) {
  switch (status) {
    case "open":
      return "Open";
    case "active":
      return "Active";
    case "completed":
      return "Completed";
    case "cancelled":
      return "Cancelled";
    default:
      return status;
  }
}

function statusClass(status: EsusuCycleResponse["status"]) {
  switch (status) {
    case "open":
      return "bg-gold-50 text-gold-700";
    case "active":
      return "bg-info-bg text-info";
    case "completed":
      return "bg-success-bg text-success";
    case "cancelled":
      return "bg-danger-bg text-danger";
    default:
      return "bg-cream-dark text-charcoal-soft";
  }
}

export default function PortalEsusuPage() {
  return (
    <RequireAuth>
      <PortalNav />
      <EsusuContent />
    </RequireAuth>
  );
}

function EsusuContent() {
  const { trader } = useAuth();
  const [cycles, setCycles] = useState<EsusuListItem[]>([]);
  const [selectedCycle, setSelectedCycle] = useState<EsusuCycleResponse | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [contributeForm, setContributeForm] = useState<ContributeState>(initialContributeState);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canCreate = !!trader?.market_name;

  const isSelectedCycleMember = useMemo(() => {
    if (!selectedCycle || !trader) return false;
    return selectedCycle.members.some((member) => member.trader_id === trader.id);
  }, [selectedCycle, trader]);

  async function loadCycles(selectId?: string) {
    setLoadingList(true);
    setError(null);
    try {
      const data = await listEsusuCycles();
      setCycles(data);
      const targetId = selectId ?? selectedCycle?.id ?? data[0]?.id;
      if (targetId) {
        await loadCycleDetail(targetId);
      } else {
        setSelectedCycle(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load Ajo/Esusu cycles.");
    } finally {
      setLoadingList(false);
    }
  }

  async function loadCycleDetail(cycleId: string) {
    setLoadingDetail(true);
    try {
      const detail = await getEsusuCycle(cycleId);
      setSelectedCycle(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load cycle details.");
    } finally {
      setLoadingDetail(false);
    }
  }

  useEffect(() => {
    loadCycles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!trader?.market_name) {
      setError("Your trader profile needs a market before you can create a cycle.");
      return;
    }

    const contributionAmount = Number(form.contribution_amount);
    const totalMembers = Number(form.total_members);
    const frequencyDays = Number(form.frequency_days);

    if (!form.title.trim() || !contributionAmount || !totalMembers) {
      setError("Enter a title, contribution amount, and member count.");
      return;
    }

    setSubmitting(true);
    try {
      const payload: EsusuCycleCreatePayload = {
        title: form.title.trim(),
        market_name: trader.market_name,
        contribution_amount: contributionAmount,
        total_members: totalMembers,
        frequency_days: frequencyDays,
        description: form.description.trim() || null,
      };

      const created = await createEsusuCycle(payload);
      setForm(initialForm);
      await loadCycles(created.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create cycle.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleJoin(cycleId: string) {
    setActionBusy(`join:${cycleId}`);
    setError(null);
    try {
      await joinEsusuCycle(cycleId);
      await loadCycles(cycleId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not join cycle.");
    } finally {
      setActionBusy(null);
    }
  }

  async function handleContribute(cycleId: string) {
    setActionBusy(`contribute:${cycleId}`);
    setError(null);

    if (!contributeForm.nomba_transaction_ref.trim()) {
      setError("Enter the Nomba transaction reference from the payment you made to your virtual account.");
      setActionBusy(null);
      return;
    }

    try {
      const payload: EsusuContributePayload = {
        nomba_transaction_ref: contributeForm.nomba_transaction_ref.trim(),
      };

      await contributeToEsusuCycle(cycleId, payload);
      setContributeForm(initialContributeState);
      await loadCycles(cycleId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not contribute to cycle.");
    } finally {
      setActionBusy(null);
    }
  }

  return (
    <div className="container-oja max-w-6xl py-8 pb-24 md:pb-8">
      <div className="mb-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <span className="text-xs font-semibold uppercase tracking-widest text-gold-600">
            Ajo / Esusu
          </span>
          <h1 className="mt-2 font-display text-display-md font-bold text-charcoal">
            Rotating savings for your market
          </h1>
          <p className="mt-3 max-w-2xl text-charcoal-soft">
            Create a savings circle, join your market group, and contribute round by round until every member receives their turn.
          </p>
        </div>
        <div className="rounded-2xl border border-surface-border bg-surface px-5 py-4 shadow-card">
          <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">Your market</p>
          <p className="mt-1 font-display text-lg font-bold text-charcoal">{trader?.market_name ?? "Unknown"}</p>
        </div>
      </div>

      {error && (
        <div className="mb-6 rounded-2xl border border-danger/20 bg-danger-bg px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <form onSubmit={handleCreate} className="card-surface p-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gold-50 text-gold-600">
              <Plus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="font-display text-xl font-bold text-charcoal">Create a cycle</h2>
              <p className="text-sm text-charcoal-soft">Start a new saving group in your market.</p>
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-charcoal">Title</label>
              <Input
                value={form.title}
                onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
                placeholder="Market Savings Circle"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-charcoal">Contribution amount</label>
              <Input
                type="number"
                min="1"
                step="0.01"
                value={form.contribution_amount}
                onChange={(e) => setForm((prev) => ({ ...prev, contribution_amount: e.target.value }))}
                placeholder="5000"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-charcoal">Members</label>
              <Input
                type="number"
                min="2"
                max="100"
                value={form.total_members}
                onChange={(e) => setForm((prev) => ({ ...prev, total_members: e.target.value }))}
                placeholder="10"
              />
            </div>
            <div>
              <label className="mb-2 block text-sm font-medium text-charcoal">Frequency (days)</label>
              <Input
                type="number"
                min="1"
                value={form.frequency_days}
                onChange={(e) => setForm((prev) => ({ ...prev, frequency_days: e.target.value }))}
                placeholder="7"
              />
            </div>
            <div className="md:col-span-2">
              <label className="mb-2 block text-sm font-medium text-charcoal">Description</label>
              <Input
                value={form.description}
                onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Weekly savings for wholesale stock"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || !canCreate}
            className="btn-gold mt-5 w-full justify-center disabled:opacity-60"
          >
            {submitting ? <Spinner className="h-5 w-5" /> : <><Plus className="h-4 w-4" /> Create Cycle</>}
          </button>

          {!canCreate && (
            <p className="mt-3 text-xs text-charcoal-soft">
              Your trader profile needs a market name before you can create a cycle.
            </p>
          )}
        </form>

        <div className="card-surface p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display text-xl font-bold text-charcoal">Cycle list</h2>
              <p className="text-sm text-charcoal-soft">Tap one to inspect the members and rounds.</p>
            </div>
            <button
              type="button"
              onClick={() => loadCycles(selectedCycle?.id)}
              className="flex items-center gap-2 rounded-full border border-surface-border bg-surface px-4 py-2 text-sm font-medium text-charcoal-soft hover:text-charcoal"
            >
              <RefreshCcw className="h-4 w-4" /> Refresh
            </button>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {loadingList ? (
              <div className="flex h-52 items-center justify-center">
                <Spinner className="h-8 w-8 text-gold-500" />
              </div>
            ) : cycles.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-surface-border p-6 text-center text-sm text-charcoal-soft">
                No cycles yet. Create the first one.
              </div>
            ) : (
              cycles.map((cycle) => {
                const active = selectedCycle?.id === cycle.id;
                const joined = !!selectedCycle && isSelectedCycleMember;
                return (
                  <button
                    key={cycle.id}
                    type="button"
                    onClick={() => loadCycleDetail(cycle.id)}
                    className={`rounded-2xl border p-4 text-left transition-colors ${active ? "border-gold-300 bg-gold-50/40" : "border-surface-border bg-surface hover:bg-cream-dark/40"}`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-display text-lg font-bold text-charcoal">{cycle.title}</h3>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusClass(cycle.status)}`}>
                            {statusLabel(cycle.status)}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-charcoal-soft">
                          {cycle.market_name ?? "Market unspecified"} · {cycle.total_members} members · {formatNaira(cycle.contribution_amount)} each
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-display text-sm font-bold text-charcoal">Round {cycle.current_round_number}</p>
                        <p className="text-xs text-charcoal-soft">{cycle.progress_pct.toFixed(0)}% joined</p>
                      </div>
                    </div>
                    <div className="mt-3 h-2 rounded-full bg-cream-dark">
                      <div className="h-2 rounded-full bg-gold-500" style={{ width: `${Math.min(cycle.progress_pct, 100)}%` }} />
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-charcoal-soft">
                      <span>Current round beneficiary shown in details</span>
                      <span>{joined ? "You are in this cycle" : "Not joined yet"}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 card-surface p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display text-xl font-bold text-charcoal">Cycle details</h2>
            <p className="text-sm text-charcoal-soft">{loadingDetail ? "Loading details..." : selectedCycle?.description ?? "Select a cycle to inspect it."}</p>
          </div>
          {selectedCycle && (
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass(selectedCycle.status)}`}>
              {statusLabel(selectedCycle.status)}
            </span>
          )}
        </div>

        {!selectedCycle ? (
          <div className="mt-6 rounded-2xl border border-dashed border-surface-border p-8 text-center text-sm text-charcoal-soft">
            Pick a cycle from the list to view members and act on it.
          </div>
        ) : loadingDetail ? (
          <div className="mt-6 flex h-48 items-center justify-center">
            <Spinner className="h-8 w-8 text-gold-500" />
          </div>
        ) : (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
            <div className="rounded-2xl border border-surface-border bg-cream-dark/30 p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-gold-50 text-gold-600">
                  <CircleDollarSign className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-charcoal-soft">Savings snapshot</p>
                  <p className="font-display text-lg font-bold text-charcoal">{formatNaira(selectedCycle.contribution_amount)} per round</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-2xl bg-surface p-4">
                  <p className="text-xs uppercase tracking-wider text-charcoal-soft">Members</p>
                  <p className="mt-1 font-display text-xl font-bold text-charcoal">{selectedCycle.members.length}/{selectedCycle.total_members}</p>
                </div>
                <div className="rounded-2xl bg-surface p-4">
                  <p className="text-xs uppercase tracking-wider text-charcoal-soft">Collected</p>
                  <p className="mt-1 font-display text-xl font-bold text-charcoal">{formatNaira(selectedCycle.total_collected)}</p>
                </div>
                <div className="rounded-2xl bg-surface p-4">
                  <p className="text-xs uppercase tracking-wider text-charcoal-soft">Current round</p>
                  <p className="mt-1 font-display text-xl font-bold text-charcoal">#{selectedCycle.current_round_number}</p>
                </div>
                <div className="rounded-2xl bg-surface p-4">
                  <p className="text-xs uppercase tracking-wider text-charcoal-soft">Next beneficiary</p>
                  <p className="mt-1 font-display text-sm font-bold text-charcoal">{selectedCycle.next_beneficiary_trader_name ?? "TBD"}</p>
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {selectedCycle.status === "open" && (
                  <button
                    onClick={() => handleJoin(selectedCycle.id)}
                    disabled={actionBusy === `join:${selectedCycle.id}`}
                    className="btn-outline flex-1 justify-center disabled:opacity-60"
                  >
                    {actionBusy === `join:${selectedCycle.id}` ? <Spinner className="h-5 w-5" /> : <><Users className="h-4 w-4" /> Join Cycle</>}
                  </button>
                )}
                {(selectedCycle.status === "active" || selectedCycle.status === "open") && isSelectedCycleMember && (
                    <div className="flex w-full flex-col gap-3 rounded-2xl border border-surface-border bg-surface p-4">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-charcoal">
                          Nomba transaction reference
                        </label>
                        <Input
                          value={contributeForm.nomba_transaction_ref}
                          onChange={(e) => setContributeForm({ nomba_transaction_ref: e.target.value })}
                          placeholder="Paste the transaction reference from your payment"
                        />
                      </div>
                      <button
                        onClick={() => handleContribute(selectedCycle.id)}
                        disabled={actionBusy === `contribute:${selectedCycle.id}`}
                        className="btn-gold justify-center disabled:opacity-60"
                      >
                        {actionBusy === `contribute:${selectedCycle.id}` ? <Spinner className="h-5 w-5" /> : <><ArrowRight className="h-4 w-4" /> Contribute</>}
                      </button>
                    </div>
                )}
              </div>

              <p className="mt-3 text-xs text-charcoal-soft">
                Contributions go round by round until every member has received their payout.
              </p>
            </div>

            <div className="grid gap-4">
              <div className="rounded-2xl border border-surface-border p-5">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-lg font-bold text-charcoal">Members</h3>
                  <span className="text-xs text-charcoal-soft">{selectedCycle.members.length} total</span>
                </div>
                <div className="mt-4 flex flex-col gap-3">
                  {selectedCycle.members.length === 0 ? (
                    <p className="text-sm text-charcoal-soft">No members yet.</p>
                  ) : (
                    selectedCycle.members.map((member) => (
                      <div key={member.id} className="flex items-center justify-between rounded-2xl bg-cream-dark/40 px-4 py-3">
                        <div>
                          <p className="font-medium text-charcoal">{member.trader_name}</p>
                          <p className="text-xs text-charcoal-soft">{member.trader_phone}</p>
                        </div>
                        <div className="text-right text-xs text-charcoal-soft">
                          <p>Position #{member.payout_position}</p>
                          <p>
                            {member.last_received_round ? `Received round ${member.last_received_round}` : "Waiting"}
                          </p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-surface-border p-5">
                <h3 className="font-display text-lg font-bold text-charcoal">Rounds</h3>
                <div className="mt-4 flex flex-col gap-3">
                  {selectedCycle.rounds.length === 0 ? (
                    <p className="text-sm text-charcoal-soft">No rounds have started yet.</p>
                  ) : (
                    selectedCycle.rounds.map((round) => (
                      <div key={round.id} className="rounded-2xl border border-surface-border bg-surface p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-charcoal">Round {round.round_number}</p>
                            <p className="text-xs text-charcoal-soft">Beneficiary: {round.beneficiary_trader_name}</p>
                          </div>
                          <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${round.status === "paid" ? "bg-success-bg text-success" : "bg-gold-50 text-gold-700"}`}>
                            {round.status}
                          </span>
                        </div>
                        <div className="mt-3 h-2 rounded-full bg-cream-dark">
                          <div className="h-2 rounded-full bg-gold-500" style={{ width: `${Math.min(round.progress_pct, 100)}%` }} />
                        </div>
                        <p className="mt-2 text-xs text-charcoal-soft">
                          {formatNaira(round.collected_amount)} of {formatNaira(round.target_amount)} collected · {round.contribution_count} contribution{round.contribution_count !== 1 ? "s" : ""}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}