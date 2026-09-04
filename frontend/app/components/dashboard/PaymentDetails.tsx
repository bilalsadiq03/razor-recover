import type {
  ExecutionResult,
  Payment,
} from "@/types/recovery";

type PaymentDetailsProps = {
  payment: Payment;
  executionResult: ExecutionResult | null;
  executing: boolean;
  onExecute: (paymentId: number) => void;
};

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

function StatusBadge({
  value,
}: {
  value: string;
}) {
  const normalized = value.toUpperCase();

  let classes =
    "inline-flex rounded-full px-2.5 py-1 text-xs font-medium";

  if (
    normalized === "HIGH" ||
    normalized === "SUCCESS"
  ) {
    classes +=
      " bg-emerald-500/10 text-emerald-400";
  } else if (
    normalized === "MEDIUM" ||
    normalized === "PENDING"
  ) {
    classes +=
      " bg-amber-500/10 text-amber-400";
  } else {
    classes +=
      " bg-slate-700 text-slate-300";
  }

  return (
    <span className={classes}>
      {value}
    </span>
  );
}

export default function PaymentDetails({
  payment,
  executionResult,
  executing,
  onExecute,
}: PaymentDetailsProps) {
  const recoveryCase =
    payment.recovery_case;

  return (
    <div>
      {/* Payment information */}
      <div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Payment Details
        </h3>

        <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Info
            label="Payment ID"
            value={payment.payment_id}
          />

          <Info
            label="Transaction ID"
            value={payment.transaction_id}
          />

          <Info
            label="Amount"
            value={`₹${Number(
              payment.amount
            ).toLocaleString("en-IN", {
              minimumFractionDigits: 2,
            })}`}
          />

          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
            <p className="text-xs uppercase tracking-wider text-slate-500">
              Payment Status
            </p>

            <div className="mt-2">
              <StatusBadge
                value={payment.payment_status}
              />
            </div>
          </div>

          <Info
            label="Failure Reason"
            value={payment.failure_reason}
          />
        </div>
      </div>

      {/* Recovery information */}
      {recoveryCase && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Recovery Decision
          </h3>

          <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500">
                Status
              </p>

              <div className="mt-2">
                <StatusBadge
                  value={recoveryCase.status}
                />
              </div>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-xs uppercase tracking-wider text-slate-500">
                Recoverability
              </p>

              <div className="mt-2">
                <StatusBadge
                  value={
                    recoveryCase.recoverability
                  }
                />
              </div>
            </div>

            <Info
              label="Recommended Action"
              value={
                recoveryCase.recommended_action ??
                "—"
              }
            />

            <Info
              label="Approved Action"
              value={
                recoveryCase.approved_action ??
                "—"
              }
            />

            <Info
              label="Amount at Risk"
              value={`₹${Number(
                recoveryCase.amount_at_risk
              ).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
              })}`}
            />

            <Info
              label="Amount Recovered"
              value={`₹${Number(
                recoveryCase.amount_recovered
              ).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
              })}`}
            />
          </div>
        </div>
      )}

      {/* Execute recovery */}
      {recoveryCase?.status === "PENDING" && (
        <button
          onClick={() =>
            onExecute(payment.payment_id)
          }
          disabled={executing}
          className="mt-8 rounded-xl bg-emerald-600 px-6 py-3 text-sm font-medium transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {executing
            ? "Executing Recovery..."
            : "Execute Recovery"}
        </button>
      )}

      {/* Execution result */}
      {executionResult && (
        <div className="mt-8 rounded-xl border border-slate-700 bg-slate-950 p-5">
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
                executionResult.confidence * 100
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
    </div>
  );
}