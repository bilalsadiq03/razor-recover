"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

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

import RecoveryTable from "@/app/components/dashboard/RecoveryTable";
import PaymentDetails from "@/app/components/dashboard/PaymentDetails";

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

  const selectedPaymentRef =
    useRef<HTMLElement | null>(null);

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

  /*
   * Initial dashboard load.
   *
   * We intentionally avoid calling setState directly
   * from the effect body to satisfy React's
   * set-state-in-effect rule.
   */
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

  /*
   * When a payment is inspected, automatically scroll
   * to the selected payment section.
   *
   * This effect interacts with the browser DOM rather
   * than synchronously changing React state.
   */
  useEffect(() => {
    if (!selectedPayment) {
      return;
    }

    selectedPaymentRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }, [selectedPayment]);

  const filteredCases = cases.filter((item) => {
    const matchesStatus =
      statusFilter === "ALL" ||
      item.status === statusFilter;

    const query = search.toLowerCase().trim();

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

        {/* Recovery Cases */}
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

              {/* Search */}
              <input
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search payment or transaction"
                className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm outline-none transition focus:border-indigo-500"
              />

              {/* Status filter */}
              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(event.target.value)
                }
                className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm outline-none transition focus:border-indigo-500"
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

              {/* Refresh */}
              <button
                type="button"
                onClick={loadCases}
                disabled={loading}
                className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading
                  ? "Refreshing..."
                  : "Refresh"}
              </button>
            </div>
          </div>

          {/* Table */}
          <RecoveryTable
            cases={filteredCases}
            loading={loading}
            onInspect={inspectPayment}
          />

          {/* Table footer */}
          <div className="border-t border-slate-800 px-6 py-4 text-xs text-slate-500">
            Showing{" "}
            {filteredCases.length} of{" "}
            {cases.length} loaded cases
          </div>
        </section>

        {/* Selected Payment */}
        {selectedPayment && (
          <section
            ref={selectedPaymentRef}
            className="mt-8 scroll-mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6"
          >
            {/* Selected case header */}
            <div className="mb-6 flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold">
                  Recovery Case #
                  {selectedPayment.recovery_case?.id ??
                    "—"}
                </h2>

                <p className="mt-1 text-sm text-slate-400">
                  Payment #
                  {selectedPayment.payment_id}
                </p>
              </div>

              <button
                type="button"
                onClick={() => {
                  setSelectedPayment(null);
                  setExecutionResult(null);
                }}
                className="rounded-lg px-3 py-2 text-sm text-slate-500 transition hover:bg-slate-800 hover:text-white"
              >
                Close
              </button>
            </div>

            {/* Payment details + recovery execution */}
            <PaymentDetails
              payment={selectedPayment}
              executionResult={executionResult}
              executing={executing}
              onExecute={executeRecovery}
            />
          </section>
        )}
      </div>
    </main>
  );
}

/* ============================================================
   Metric Card
   ============================================================ */

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