"use client";

import { useState } from "react";

import {
  executeBatchRecovery,
  type BatchRecoveryResponse,
} from "@/lib/api";

type BatchRecoveryProps = {
  onCompleted: () => Promise<void> | void;
};

function formatCurrency(value: number) {
  return `₹${Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
  })}`;
}

function ResultCard({
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

      <p className="mt-2 text-lg font-semibold text-slate-100">
        {value}
      </p>
    </div>
  );
}

export default function BatchRecovery({
  onCompleted,
}: BatchRecoveryProps) {
  const [batchSize, setBatchSize] = useState(3);
  const [maxRevenueAtRisk, setMaxRevenueAtRisk] =
    useState(100000);
  const [maxConsecutiveErrors, setMaxConsecutiveErrors] =
    useState(3);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] =
    useState<BatchRecoveryResponse | null>(null);

  async function handleRunBatch() {
    setRunning(true);
    setError("");
    setResult(null);

    try {
      const response = await executeBatchRecovery({
        batch_size: batchSize,
        delay_seconds: 0,
        max_revenue_at_risk: maxRevenueAtRisk,
        max_consecutive_errors:
          maxConsecutiveErrors,
      });

      setResult(response);

      await onCompleted();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Batch recovery failed."
      );
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="flex flex-col gap-6">

        {/* Header */}
        <div>
          <h2 className="text-xl font-semibold">
            Autonomous Recovery
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Run a controlled recovery batch using the
            configured AI and policy engine.
          </p>
        </div>

        {/* Controls */}
        <div className="grid gap-4 md:grid-cols-3">

          <label className="block">
            <span className="text-xs uppercase tracking-wider text-slate-500">
              Batch Size
            </span>

            <input
              type="number"
              min={1}
              max={100}
              value={batchSize}
              onChange={(event) =>
                setBatchSize(
                  Number(event.target.value)
                )
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none transition focus:border-indigo-500"
            />
          </label>

          <label className="block">
            <span className="text-xs uppercase tracking-wider text-slate-500">
              Max Revenue at Risk
            </span>

            <input
              type="number"
              min={1}
              value={maxRevenueAtRisk}
              onChange={(event) =>
                setMaxRevenueAtRisk(
                  Number(event.target.value)
                )
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none transition focus:border-indigo-500"
            />
          </label>

          <label className="block">
            <span className="text-xs uppercase tracking-wider text-slate-500">
              Max Consecutive Errors
            </span>

            <input
              type="number"
              min={1}
              max={10}
              value={maxConsecutiveErrors}
              onChange={(event) =>
                setMaxConsecutiveErrors(
                  Number(event.target.value)
                )
              }
              className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm outline-none transition focus:border-indigo-500"
            />
          </label>
        </div>

        {/* Run button */}
        <div>
          <button
            type="button"
            onClick={handleRunBatch}
            disabled={running}
            className="rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {running
              ? "Running Recovery..."
              : "Run Recovery Batch"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="border-t border-slate-800 pt-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">
                Batch Result
              </h3>

              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                {result.stop_reason}
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <ResultCard
                label="Cases Found"
                value={result.cases_found}
              />

              <ResultCard
                label="Cases Processed"
                value={result.cases_processed}
              />

              <ResultCard
                label="Successful"
                value={result.successful_recoveries}
              />

              <ResultCard
                label="Failed"
                value={result.failed_recoveries}
              />

              <ResultCard
                label="Policy Blocked"
                value={result.policy_blocked}
              />

              <ResultCard
                label="Deferred"
                value={result.deferred}
              />

              <ResultCard
                label="Revenue at Risk"
                value={formatCurrency(
                  result.revenue_at_risk
                )}
              />

              <ResultCard
                label="Revenue Recovered"
                value={formatCurrency(
                  result.revenue_recovered
                )}
              />
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <ResultCard
                label="Case Recovery Rate"
                value={`${result.recovery_rate.toFixed(
                  2
                )}%`}
              />

              <ResultCard
                label="Revenue Recovery Rate"
                value={`${result.revenue_recovery_rate.toFixed(
                  2
                )}%`}
              />
            </div>
          </div>
        )}
      </div>
    </section>
  );
}