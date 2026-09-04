import type { RecoveryCase } from "@/types/recovery";

type RecoveryTableProps = {
  cases: RecoveryCase[];
  loading: boolean;
  onInspect: (paymentId: number) => void;
};

function Badge({ value }: { value: string }) {
  const normalized = value.toUpperCase();

  let classes =
    "inline-flex rounded-full px-2.5 py-1 text-xs font-medium";

  if (normalized === "HIGH" || normalized === "SUCCESS") {
    classes += " bg-emerald-500/10 text-emerald-400";
  } else if (
    normalized === "MEDIUM" ||
    normalized === "PENDING"
  ) {
    classes += " bg-amber-500/10 text-amber-400";
  } else {
    classes += " bg-slate-700 text-slate-300";
  }

  return (
    <span className={classes}>
      {value}
    </span>
  );
}

export default function RecoveryTable({
  cases,
  loading,
  onInspect,
}: RecoveryTableProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-6 py-5">
        <h2 className="text-lg font-semibold">
          Recovery Cases
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="px-6 py-4">Payment</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4">Recoverability</th>
              <th className="px-6 py-4">AI Action</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Action</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-800">
            {loading ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-slate-500"
                >
                  Loading recovery cases...
                </td>
              </tr>
            ) : cases.length === 0 ? (
              <tr>
                <td
                  colSpan={6}
                  className="px-6 py-12 text-center text-slate-500"
                >
                  No recovery cases found.
                </td>
              </tr>
            ) : (
              cases.map((item) => (
                <tr
                  key={item.id}
                  className="transition hover:bg-slate-800/40"
                >
                  <td className="px-6 py-4">
                    <div className="font-medium">
                      #{item.payment_id}
                    </div>

                    <div className="mt-1 text-xs text-slate-500">
                      {item.transaction_id}
                    </div>
                  </td>

                  <td className="px-6 py-4 font-medium">
                    ₹
                    {Number(
                      item.amount_at_risk
                    ).toLocaleString("en-IN", {
                      minimumFractionDigits: 2,
                    })}
                  </td>

                  <td className="px-6 py-4">
                    <Badge value={item.recoverability} />
                  </td>

                  <td className="px-6 py-4">
                    <span className="text-slate-300">
                      {item.recommended_action ?? "—"}
                    </span>
                  </td>

                  <td className="px-6 py-4">
                    <Badge value={item.status} />
                  </td>

                  <td className="px-6 py-4">
                    <button
                      onClick={() =>
                        onInspect(item.payment_id)
                      }
                      className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium transition hover:bg-slate-800"
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="border-t border-slate-800 px-6 py-4 text-xs text-slate-500">
        Showing {cases.length} loaded cases
      </div>
    </section>
  );
}