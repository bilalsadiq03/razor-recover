"use client";

import { useEffect, useState } from "react";
// import MetricCard from "@/app/components/dashboard/MerticCard";
import RecoveryTable from "@/app/components/dashboard/RecoveryTable";

import type {
  ExecutionResult,
  Payment,
  RecoveryCase,
} from "@/types/recovery";

import {
  executeRecovery as executeRecoveryApi,
  getPayment,
  getRecoveryCases,
} from "@/lib/api";

export default function Home() {
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [selectedPayment, setSelectedPayment] =
    useState<Payment | null>(null);

  const [statusFilter, setStatusFilter] =
    useState("PENDING");

  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState("");

  const [executionResult, setExecutionResult] =
    useState<ExecutionResult | null>(null);

  async function loadCases() {
    setLoading(true);
    setError("");

    try {
      const data = await getRecoveryCases(50);
      setCases(data);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load recovery cases."
      );
    } finally {
      setLoading(false);
    }
  }

  async function inspectPayment(
    paymentId: number
  ) {
    setError("");

    try {
      const data = await getPayment(paymentId);

      setSelectedPayment(data);
      setExecutionResult(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load payment."
      );
    }
  }
  async function executeRecovery(
    paymentId: number
  ) {
    setExecuting(true);
    setError("");
    setExecutionResult(null);

    try {
      const result =
        await executeRecoveryApi(paymentId);

      setExecutionResult(result);

      await loadCases();
      await inspectPayment(paymentId);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Recovery execution failed."
      );
    } finally {
      setExecuting(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function fetchInitialCases() {
      try {
        const data = await getRecoveryCases(50);

        if (!cancelled) {
          setCases(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load recovery cases."
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchInitialCases();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredCases = cases.filter((item) => {
    const matchesStatus =
      statusFilter === "ALL" ||
      item.status === statusFilter;

    const query = search.toLowerCase();

    const matchesSearch =
      !query ||
      item.transaction_id
        .toLowerCase()
        .includes(query) ||
      String(item.payment_id).includes(query);

    return matchesStatus && matchesSearch;
  });

  const revenueAtRisk = cases.reduce(
    (total, item) =>
      total + Number(item.amount_at_risk),
    0
  );

  const revenueRecovered = cases.reduce(
    (total, item) =>
      total + Number(item.amount_recovered),
    0
  );

  const recoveredCases = cases.filter(
    (item) => item.status === "RECOVERED"
  ).length;

  const recoveryRate =
    cases.length > 0
      ? (recoveredCases / cases.length) * 100
      : 0;

  const pendingCases = cases.filter(
    (item) => item.status === "PENDING"
  ).length;

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <div className="mx-auto max-w-7xl px-6 py-8">

        {/* Header */}
        <header className="mb-10 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              RazorRecover
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              Autonomous AI-powered revenue recovery
            </p>
          </div>

          <div className="flex items-center gap-2 self-start rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            System Online
          </div>
        </header>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Metrics */}
        <section className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Revenue at Risk"
            value={`₹${revenueAtRisk.toLocaleString(
              "en-IN",
              {
                minimumFractionDigits: 2,
              }
            )}`}
          />

          <MetricCard
            label="Revenue Recovered"
            value={`₹${revenueRecovered.toLocaleString(
              "en-IN",
              {
                minimumFractionDigits: 2,
              }
            )}`}
          />

          <MetricCard
            label="Recovery Rate"
            value={`${recoveryRate.toFixed(1)}%`}
          />

          <MetricCard
            label="Pending Cases"
            value={pendingCases}
          />
        </section>

        {/* Cases */}
        <section className="rounded-2xl border border-slate-800 bg-slate-900">

          {/* Toolbar */}
          <div className="flex flex-col gap-4 border-b border-slate-800 p-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-xl font-semibold">
                Recovery Cases
              </h2>

              <p className="mt-1 text-sm text-slate-400">
                AI-ranked payment failures requiring recovery.
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">

              <input
                value={search}
                onChange={(e) =>
                  setSearch(e.target.value)
                }
                placeholder="Search payment or transaction"
                className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
              />

              <select
                value={statusFilter}
                onChange={(e) =>
                  setStatusFilter(e.target.value)
                }
                className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm outline-none focus:border-indigo-500"
              >
                <option value="ALL">
                  All
                </option>
                <option value="PENDING">
                  Pending
                </option>
                <option value="RECOVERED">
                  Recovered
                </option>
                <option value="FAILED">
                  Failed
                </option>
                <option value="BLOCKED">
                  Blocked
                </option>
              </select>

              <button
                onClick={loadCases}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm transition hover:bg-slate-800"
              >
                Refresh
              </button>
            </div>
          </div>

          {/* Table */}
          <RecoveryTable
            cases={filteredCases}
            loading={loading}
            onInspect={inspectPayment}
          />

          <div className="border-t border-slate-800 px-6 py-4 text-xs text-slate-500">
            Showing {filteredCases.length} of{" "}
            {cases.length} loaded cases
          </div>
        </section>

        {/* Selected Case */}
        {selectedPayment && (
          <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">

            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold">
                  Recovery Case #
                  {
                    selectedPayment.recovery_case
                      ?.id
                  }
                </h2>

                <p className="mt-1 text-sm text-slate-400">
                  Payment #
                  {selectedPayment.payment_id}
                </p>
              </div>

              <button
                onClick={() =>
                  setSelectedPayment(null)
                }
                className="text-sm text-slate-500 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">

              <Info
                label="Transaction"
                value={
                  selectedPayment.transaction_id
                }
              />

              <Info
                label="Amount"
                value={`₹${Number(
                  selectedPayment.amount
                ).toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                })}`}
              />

              <Info
                label="Failure Reason"
                value={
                  selectedPayment.failure_reason
                }
              />

              <Info
                label="Recoverability"
                value={
                  selectedPayment.recovery_case
                    ?.recoverability ?? "—"
                }
              />

              <Info
                label="Recommended Action"
                value={
                  selectedPayment.recovery_case
                    ?.recommended_action ?? "—"
                }
              />

              <Info
                label="Status"
                value={
                  selectedPayment.recovery_case
                    ?.status ?? "—"
                }
              />
            </div>

            {/* Execute */}
            {selectedPayment.recovery_case
              ?.status === "PENDING" && (
                <button
                  onClick={() =>
                    executeRecovery(
                      selectedPayment.payment_id
                    )
                  }
                  disabled={executing}
                  className="mt-6 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-medium transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {executing
                    ? "Executing Recovery..."
                    : "Execute Recovery"}
                </button>
              )}

            {/* Execution result */}
            {executionResult && (
              <div className="mt-6 rounded-xl border border-slate-700 bg-slate-950 p-5">
                <h3 className="font-semibold">
                  Execution Result
                </h3>

                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  <Info
                    label="AI Action"
                    value={
                      executionResult.ai_action
                    }
                  />

                  <Info
                    label="Approved Action"
                    value={
                      executionResult.approved_action ??
                      "—"
                    }
                  />

                  <Info
                    label="Confidence"
                    value={`${(
                      executionResult.confidence *
                      100
                    ).toFixed(0)}%`}
                  />

                  <Info
                    label="Status"
                    value={
                      executionResult.status
                    }
                  />

                  <Info
                    label="Recovered"
                    value={`₹${Number(
                      executionResult.amount_recovered
                    ).toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                    })}`}
                  />

                  <Info
                    label="Reason"
                    value={
                      executionResult.reason
                    }
                  />
                </div>
              </div>
            )}
          </section>
        )}
      </div>
    </main>
  );
}


function MetricCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-sm text-slate-400">
        {label}
      </p>

      <p className="mt-2 text-2xl font-bold">
        {value}
      </p>
    </div>
  );
}


function Info({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
      <p className="text-xs uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className="mt-2 break-all text-sm font-medium text-slate-200">
        {value}
      </p>
    </div>
  );
}
